"""
FastAPI wrapper for ComfyUI - Enables IMG2IMG
Run this on port 8001 to replace the old Diffusers API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import requests
import json
import time
import base64
from io import BytesIO
from datetime import datetime
import os
from dotenv import load_dotenv
import boto3
from comfyui_simple import convert_workflow_to_api_format

# Load environment variables
load_dotenv()

# AWS S3 Setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-2')
)
S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'ai-character-generations')

# API Keys
GROK_API_KEY = os.getenv('GROK_API_KEY')

app = FastAPI(
    title="ComfyUI Wrapper API",
    description="IMG2IMG working via ComfyUI",
    version="1.0.0"
)

# CORS for Codespaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ComfyUI endpoint
COMFYUI_URL = "https://slai6mcmlxsqvh-3001.proxy.runpod.net"
WORKFLOW_PATH = "/workspaces/ai/qwen instagram influencer workflow (Aiorbust).json"

class GenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = "blurry, low quality, distorted"
    character: str = "milan"
    width: int = 1024
    height: int = 768
    num_inference_steps: int = 30
    guidance_scale: float = 4.0
    seed: Optional[int] = None
    lora_strength: float = 0.8

    # IMG2IMG support
    init_image_base64: Optional[str] = None
    strength: float = 0.85

    # Batch generation
    num_images: int = 1

    # Upscaling (enable if > 1.0)
    upscale_factor: float = 1.5
    enable_upscaling: bool = False

    # Advanced: Model sampling shift (affects style adherence)
    model_sampling_shift: float = 2.0

class GenerationResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    images_base64: Optional[List[str]] = None
    error: Optional[str] = None
    generation_time: Optional[float] = None
    s3_input_url: Optional[str] = None  # Uploaded input image
    s3_output_url: Optional[str] = None  # Generated output image
    s3_metadata_url: Optional[str] = None  # JSON metadata file

class InpaintRequest(BaseModel):
    image_base64: str  # Original image to inpaint
    mask_base64: str   # Mask image (white = inpaint, black = keep)
    prompt: str        # What to put in masked area
    negative_prompt: Optional[str] = "blurry, low quality, distorted"
    character: str = "milan"
    num_inference_steps: int = 30
    guidance_scale: float = 4.0
    seed: Optional[int] = None
    use_grok_enhancement: bool = False  # Enhance prompt with Grok

@app.get("/")
async def root():
    return {
        "status": "online",
        "backend": "ComfyUI",
        "img2img": "supported",
        "workflow": "qwen-instagram-influencer"
    }

@app.get("/health")
async def health():
    # Check if ComfyUI is reachable
    try:
        response = requests.get(f"{COMFYUI_URL}/", timeout=5)
        comfyui_status = "online" if response.status_code == 200 else "offline"
    except:
        comfyui_status = "offline"

    return {
        "status": "healthy",
        "comfyui": comfyui_status,
        "wrapper": "ready"
    }

# Grok Vision Models
class AnalyzeImageRequest(BaseModel):
    image_base64: str
    model_name: str = "milan"

class AnalyzeImageResponse(BaseModel):
    success: bool
    caption: Optional[str] = None
    error: Optional[str] = None

@app.post("/analyze-image", response_model=AnalyzeImageResponse)
async def analyze_image(request: AnalyzeImageRequest):
    """Analyze uploaded image with Grok Vision and generate training-style caption"""

    if not GROK_API_KEY:
        return AnalyzeImageResponse(success=False, error="Grok API key not configured")

    try:
        # Prepare Grok Vision API request
        grok_prompt = f"""Analyze this image and create a detailed caption in this exact format:

{request.model_name}, [physical features: hair style/color, skin tone, etc.], [clothing or nude description], [pose and body position], [hand positions if visible], [facial expression], [lighting description]

Examples of the format:
- milan, woman with dark hair slicked back in bun, tanned skin, wearing sheer see-through beige bra with white trim showing nipples, sheer see-through beige high-waisted panties with white trim, standing in white doorway facing forward, left hand on left doorframe, right hand on right doorframe, neutral expression, bright even lighting
- milan, woman with long dark brown hair loose, tanned skin, fully nude, sitting on wooden sauna bench facing camera with legs spread very wide, left hand on left knee, right hand on right knee, genitals visible, warm golden sauna lighting

Be extremely detailed and specific about pose, clothing, and body positioning. Start with "{request.model_name},"."""

        grok_response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-2-vision-1212",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": grok_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{request.image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.3
            },
            timeout=30
        )

        if grok_response.status_code != 200:
            return AnalyzeImageResponse(
                success=False,
                error=f"Grok API error: {grok_response.status_code}"
            )

        result = grok_response.json()
        caption = result['choices'][0]['message']['content'].strip()

        print(f"🤖 Grok Vision caption: {caption[:100]}...")

        return AnalyzeImageResponse(success=True, caption=caption)

    except Exception as e:
        print(f"❌ Grok Vision error: {e}")
        return AnalyzeImageResponse(success=False, error=str(e))

def upload_to_s3(file_content: bytes, s3_path: str, content_type: str = "image/png") -> str:
    """Upload file to S3 and return the URL"""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_path,
            Body=file_content,
            ContentType=content_type
        )
        url = f"https://{S3_BUCKET}.s3.{os.getenv('AWS_REGION', 'us-east-2')}.amazonaws.com/{s3_path}"
        print(f"   ✅ Uploaded to S3: {s3_path}")
        return url
    except Exception as e:
        print(f"   ⚠️  S3 upload failed: {e}")
        return None

@app.post("/generate", response_model=GenerationResponse)
async def generate(request: GenerationRequest):
    """Generate image with ComfyUI (supports IMG2IMG)"""

    try:
        start_time = time.time()

        # 1. Load workflow
        print(f"📂 Loading workflow from {WORKFLOW_PATH}")
        with open(WORKFLOW_PATH) as f:
            workflow_ui = json.load(f)

        # 2. Update positive prompt (node 6)
        print(f"✏️  Updating prompt: {request.prompt[:50]}...")
        for node in workflow_ui["nodes"]:
            if node.get("id") == 6:  # Positive prompt node
                node["widgets_values"][0] = request.prompt
                print(f"   ✅ Updated positive prompt in node 6")
                break

        # 3. Update negative prompt (node 7)
        for node in workflow_ui["nodes"]:
            if node.get("id") == 7:  # Negative prompt node
                node["widgets_values"][0] = request.negative_prompt
                print(f"   ✅ Updated negative prompt in node 7")
                break

        # 4. Handle IMG2IMG if image provided
        uploaded_filename = None
        if request.init_image_base64:
            print(f"🖼️  IMG2IMG mode (strength: {request.strength})")

            # Upload image to ComfyUI
            try:
                image_data = base64.b64decode(request.init_image_base64)
                files = {'image': ('uploaded.jpg', BytesIO(image_data), 'image/jpeg')}

                upload_response = requests.post(
                    f"{COMFYUI_URL}/upload/image",
                    files=files,
                    timeout=30
                )

                if upload_response.status_code == 200:
                    uploaded_filename = upload_response.json().get("name")
                    print(f"   ✅ Uploaded image: {uploaded_filename}")
                else:
                    raise Exception(f"Upload failed: {upload_response.status_code}")

            except Exception as e:
                print(f"   ❌ Image upload failed: {e}")
                return GenerationResponse(
                    success=False,
                    error=f"Failed to upload image: {str(e)}"
                )

            # Update LoadImage node (node 76)
            for node in workflow_ui["nodes"]:
                if node.get("id") == 76:  # LoadImage node
                    node["widgets_values"][0] = uploaded_filename
                    node["mode"] = 0  # Enable
                    print(f"   ✅ Updated LoadImage node with {uploaded_filename}")
                    break
        else:
            # No input image provided - create a blank/dummy image for the LoadImage node
            # This prevents validation errors even though the node will be bypassed
            print(f"   📝 No input image - workflow requires IMG2IMG. Please upload an image.")
            return GenerationResponse(
                success=False,
                error="This workflow requires an input image. Please upload an image to use IMG2IMG generation."
            )

        # 5. Update LoRA strength if different (node 74)
        if request.lora_strength != 0.8:
            for node in workflow_ui["nodes"]:
                if node.get("id") == 74 and node.get("type") == "LoraLoaderModelOnly":
                    node["widgets_values"][1] = request.lora_strength
                    print(f"   ✅ Updated LoRA strength to {request.lora_strength}")
                    break

        # 5b. Update KSampler parameters (node 3)
        # Widget mapping for KSampler: [seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise]
        for node in workflow_ui["nodes"]:
            if node.get("id") == 3 and node.get("type") == "KSampler":
                # Update seed (widget[0])
                if request.seed is not None:
                    node["widgets_values"][0] = request.seed
                    print(f"   ✅ Updated seed to {request.seed}")

                # Update steps (widget[2])
                node["widgets_values"][2] = request.num_inference_steps
                print(f"   ✅ Updated steps to {request.num_inference_steps}")

                # Update CFG (widget[3])
                node["widgets_values"][3] = request.guidance_scale
                print(f"   ✅ Updated CFG to {request.guidance_scale}")

                # Update denoise/strength (widget[6]) - only if not using IMG2IMG
                if not request.init_image_base64:
                    node["widgets_values"][6] = request.strength
                    print(f"   ✅ Updated denoise to {request.strength}")

                break

        # 5c. Update dimensions and batch size (EmptySD3LatentImage node 58)
        # Widget mapping: [width, height, batch_size]
        for node in workflow_ui["nodes"]:
            if node.get("id") == 58 and node.get("type") == "EmptySD3LatentImage":
                node["widgets_values"][0] = request.width
                node["widgets_values"][1] = request.height
                node["widgets_values"][2] = request.num_images
                print(f"   ✅ Updated dimensions to {request.width}x{request.height}, batch: {request.num_images}")
                break

        # 5d. Update model sampling shift (ModelSamplingAuraFlow node 66)
        # Widget mapping: [shift]
        for node in workflow_ui["nodes"]:
            if node.get("id") == 66 and node.get("type") == "ModelSamplingAuraFlow":
                node["widgets_values"][0] = request.model_sampling_shift
                print(f"   ✅ Updated model sampling shift to {request.model_sampling_shift}")
                break

        # 5e. Enable/disable upscaling (LatentUpscaleBy node 78 + KSampler node 79)
        # mode: 0 = enabled, 4 = disabled (bypassed)
        if request.enable_upscaling:
            # Enable upscaler node 78
            for node in workflow_ui["nodes"]:
                if node.get("id") == 78 and node.get("type") == "LatentUpscaleBy":
                    node["mode"] = 0  # Enable
                    node["widgets_values"][1] = request.upscale_factor
                    print(f"   ✅ Enabled upscaling with factor {request.upscale_factor}")
                    break

            # Enable second KSampler node 79 for upscaling refinement
            for node in workflow_ui["nodes"]:
                if node.get("id") == 79 and node.get("type") == "KSampler":
                    node["mode"] = 0  # Enable
                    # Update its parameters too
                    if request.seed is not None:
                        node["widgets_values"][0] = request.seed + 1  # Different seed for upscale
                    node["widgets_values"][2] = max(20, request.num_inference_steps // 2)  # Half steps
                    node["widgets_values"][3] = request.guidance_scale * 0.5  # Lower CFG
                    print(f"   ✅ Enabled upscale refinement pass")
                    break
        else:
            # Disable upscaling nodes
            for node in workflow_ui["nodes"]:
                if node.get("id") == 78 and node.get("type") == "LatentUpscaleBy":
                    node["mode"] = 4  # Bypass
                    print(f"   ⏭️  Upscaling disabled")
                    break
            for node in workflow_ui["nodes"]:
                if node.get("id") == 79 and node.get("type") == "KSampler":
                    node["mode"] = 4  # Bypass
                    break

        # 6. Convert workflow to API format
        print("🔄 Converting workflow to API format...")
        workflow_api = convert_workflow_to_api_format(workflow_ui)
        print(f"   ✅ Converted {len(workflow_api)} nodes")

        # 7. Submit to ComfyUI
        print("🚀 Submitting to ComfyUI...")
        submit_response = requests.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow_api},
            timeout=30
        )

        if submit_response.status_code != 200:
            return GenerationResponse(
                success=False,
                error=f"ComfyUI submission failed: {submit_response.text}"
            )

        result = submit_response.json()

        if "error" in result:
            return GenerationResponse(
                success=False,
                error=f"ComfyUI error: {result['error']}"
            )

        prompt_id = result.get("prompt_id")
        if not prompt_id:
            return GenerationResponse(
                success=False,
                error=f"No prompt_id returned: {result}"
            )

        print(f"   ✅ Queued: {prompt_id}")

        # 8. Poll for completion
        print("⏳ Waiting for generation...")
        max_wait = 300  # 5 minutes
        poll_start = time.time()

        while time.time() - poll_start < max_wait:
            try:
                history_response = requests.get(
                    f"{COMFYUI_URL}/history/{prompt_id}",
                    timeout=10
                )

                if history_response.status_code != 200:
                    print(f"   ⚠️  History check returned {history_response.status_code}")
                    time.sleep(2)
                    continue

                history = history_response.json()

                # Check if generation is complete
                if prompt_id in history:
                    elapsed = time.time() - poll_start
                    print(f"   ✅ Generation complete in {elapsed:.1f}s")

                    # Extract images from outputs
                    outputs = history[prompt_id].get("outputs", {})

                    if not outputs:
                        return GenerationResponse(
                            success=False,
                            error="Generation completed but no outputs found"
                        )

                    # Find SaveImage node output (node 60)
                    images_base64 = []

                    for node_id, output in outputs.items():
                        if "images" in output:
                            for image_info in output["images"]:
                                filename = image_info.get("filename")
                                subfolder = image_info.get("subfolder", "")

                                if not filename:
                                    continue

                                # Download image
                                print(f"   📥 Downloading {filename}...")
                                image_url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type=output"

                                image_response = requests.get(image_url, timeout=30)

                                if image_response.status_code == 200:
                                    image_b64 = base64.b64encode(image_response.content).decode()
                                    images_base64.append(image_b64)
                                    print(f"   ✅ Downloaded {filename}")

                    if not images_base64:
                        return GenerationResponse(
                            success=False,
                            error="No images could be downloaded"
                        )

                    total_time = time.time() - start_time

                    # Prepare paths
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    model_name = request.character.lower()
                    s3_base_path = f"generations/{model_name}/{timestamp}"

                    # Local Jupyter path
                    local_base_path = f"/workspaces/ai/outputs/{model_name}/{timestamp}"
                    os.makedirs(local_base_path, exist_ok=True)

                    s3_input_url = None
                    s3_output_url = None
                    s3_metadata_url = None
                    local_output_path = None

                    try:
                        # Save and upload input image if provided
                        if request.init_image_base64:
                            input_data = base64.b64decode(request.init_image_base64)

                            # Save locally
                            local_input_path = f"{local_base_path}/input.jpg"
                            with open(local_input_path, "wb") as f:
                                f.write(input_data)
                            print(f"   💾 Saved input to {local_input_path}")

                            # Upload to S3
                            s3_input_path = f"{s3_base_path}/input.jpg"
                            s3_input_url = upload_to_s3(input_data, s3_input_path, "image/jpeg")

                        # Save and upload output image
                        output_data = base64.b64decode(images_base64[0])

                        # Save locally
                        local_output_path = f"{local_base_path}/output.png"
                        with open(local_output_path, "wb") as f:
                            f.write(output_data)
                        print(f"   💾 Saved output to {local_output_path}")

                        # Upload to S3
                        s3_output_path = f"{s3_base_path}/output.png"
                        s3_output_url = upload_to_s3(output_data, s3_output_path, "image/png")

                        # Create and upload metadata
                        metadata = {
                            "model": model_name,
                            "timestamp": timestamp,
                            "prompt": request.prompt,
                            "negative_prompt": request.negative_prompt,
                            "parameters": {
                                "width": request.width,
                                "height": request.height,
                                "steps": request.num_inference_steps,
                                "cfg_scale": request.guidance_scale,
                                "lora_strength": request.lora_strength,
                                "seed": request.seed,
                                "strength": request.strength if request.init_image_base64 else None,
                                "num_images": request.num_images,
                                "upscale_enabled": request.enable_upscaling,
                                "upscale_factor": request.upscale_factor if request.enable_upscaling else None,
                                "model_sampling_shift": request.model_sampling_shift
                            },
                            "generation_time": total_time,
                            "has_input_image": request.init_image_base64 is not None
                        }
                        metadata_json = json.dumps(metadata, indent=2)

                        # Save metadata locally
                        local_metadata_path = f"{local_base_path}/metadata.json"
                        with open(local_metadata_path, "w") as f:
                            f.write(metadata_json)
                        print(f"   💾 Saved metadata to {local_metadata_path}")

                        # Upload metadata to S3
                        s3_metadata_path = f"{s3_base_path}/metadata.json"
                        s3_metadata_url = upload_to_s3(
                            metadata_json.encode(),
                            s3_metadata_path,
                            "application/json"
                        )

                        print(f"💾 Saved locally: {local_base_path}/")
                        print(f"☁️  Saved to S3: {s3_base_path}/")

                    except Exception as e:
                        print(f"⚠️  S3 upload error (non-fatal): {e}")

                    return GenerationResponse(
                        success=True,
                        image_base64=images_base64[0],
                        images_base64=images_base64,
                        generation_time=total_time,
                        s3_input_url=s3_input_url,
                        s3_output_url=s3_output_url,
                        s3_metadata_url=s3_metadata_url
                    )

                # Still generating
                elapsed = time.time() - poll_start
                if int(elapsed) % 10 == 0:  # Log every 10 seconds
                    print(f"   ⏳ Still generating... ({elapsed:.0f}s)")

                time.sleep(2)

            except Exception as e:
                print(f"   ⚠️  Poll error: {e}")
                time.sleep(2)
                continue

        # Timeout
        return GenerationResponse(
            success=False,
            error=f"Generation timeout after {max_wait}s"
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

        return GenerationResponse(
            success=False,
            error=str(e)
        )

@app.post("/inpaint", response_model=GenerationResponse)
async def inpaint(request: InpaintRequest):
    """Inpaint specific areas of an image (edit clothes, background, etc.)"""

    try:
        start_time = time.time()

        # 1. Load inpaint workflow
        workflow_path = "/workspaces/ai/Flux Fill Inpaint (Cloths swap).json"
        print(f"📂 Loading inpaint workflow from {workflow_path}")
        with open(workflow_path) as f:
            workflow_ui = json.load(f)

        # 2. Enhance prompt with Grok if requested
        final_prompt = request.prompt
        if request.use_grok_enhancement and GROK_API_KEY:
            print(f"🤖 Enhancing prompt with Grok...")
            try:
                grok_response = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-2-1212",
                        "messages": [{
                            "role": "user",
                            "content": f"Enhance this inpainting prompt for consistency and quality. Keep it concise but detailed. Start with '{request.character}': {request.prompt}"
                        }],
                        "temperature": 0.3
                    },
                    timeout=10
                )
                if grok_response.status_code == 200:
                    final_prompt = grok_response.json()['choices'][0]['message']['content'].strip()
                    print(f"   ✅ Enhanced prompt: {final_prompt[:100]}...")
            except Exception as e:
                print(f"   ⚠️  Grok enhancement failed: {e}, using original prompt")

        # 3. Upload original image to ComfyUI
        print(f"🖼️  Uploading original image...")
        try:
            image_data = base64.b64decode(request.image_base64)
            files = {'image': ('original.png', BytesIO(image_data), 'image/png')}

            upload_response = requests.post(
                f"{COMFYUI_URL}/upload/image",
                files=files,
                timeout=30
            )

            if upload_response.status_code == 200:
                original_filename = upload_response.json().get("name")
                print(f"   ✅ Uploaded original: {original_filename}")
            else:
                raise Exception(f"Upload failed: {upload_response.status_code}")
        except Exception as e:
            return GenerationResponse(
                success=False,
                error=f"Failed to upload original image: {str(e)}"
            )

        # 4. Upload mask image to ComfyUI
        print(f"🎭 Uploading mask...")
        try:
            mask_data = base64.b64decode(request.mask_base64)
            files = {'image': ('mask.png', BytesIO(mask_data), 'image/png')}

            upload_response = requests.post(
                f"{COMFYUI_URL}/upload/image",
                files=files,
                timeout=30
            )

            if upload_response.status_code == 200:
                mask_filename = upload_response.json().get("name")
                print(f"   ✅ Uploaded mask: {mask_filename}")
            else:
                raise Exception(f"Mask upload failed: {upload_response.status_code}")
        except Exception as e:
            return GenerationResponse(
                success=False,
                error=f"Failed to upload mask: {str(e)}"
            )

        # 5. Update workflow nodes
        # Node 415: LoadImage (original image with mask)
        for node in workflow_ui["nodes"]:
            if node.get("id") == 415 and node.get("type") == "LoadImage":
                node["widgets_values"][0] = original_filename
                print(f"   ✅ Updated LoadImage node with {original_filename}")
                break

        # Node 416: Disable clothing reference (not using cloth swap)
        for node in workflow_ui["nodes"]:
            if node.get("id") == 416 and node.get("type") == "LoadImage":
                node["mode"] = 4  # Bypass
                print(f"   ⏭️  Disabled clothing reference node")
                break

        # Node 23: Update prompt
        for node in workflow_ui["nodes"]:
            if node.get("id") == 23 and node.get("type") == "CLIPTextEncode":
                node["widgets_values"][0] = final_prompt
                print(f"   ✅ Updated prompt: {final_prompt[:50]}...")
                break

        # 6. Convert workflow to API format
        print("🔄 Converting workflow to API format...")
        workflow_api = convert_workflow_to_api_format(workflow_ui)
        print(f"   ✅ Converted {len(workflow_api)} nodes")

        # 7. Submit to ComfyUI
        print("🚀 Submitting to ComfyUI...")
        submit_response = requests.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow_api},
            timeout=30
        )

        if submit_response.status_code != 200:
            return GenerationResponse(
                success=False,
                error=f"ComfyUI submission failed: {submit_response.text}"
            )

        result = submit_response.json()
        if "error" in result:
            return GenerationResponse(
                success=False,
                error=f"ComfyUI error: {result['error']}"
            )

        prompt_id = result.get("prompt_id")
        if not prompt_id:
            return GenerationResponse(
                success=False,
                error=f"No prompt_id returned: {result}"
            )

        print(f"   ✅ Queued: {prompt_id}")

        # 8. Poll for completion (same logic as /generate)
        print("⏳ Waiting for inpainting...")
        max_wait = 300
        poll_start = time.time()

        while time.time() - poll_start < max_wait:
            try:
                history_response = requests.get(
                    f"{COMFYUI_URL}/history/{prompt_id}",
                    timeout=10
                )

                if history_response.status_code != 200:
                    time.sleep(2)
                    continue

                history = history_response.json()

                if prompt_id in history:
                    elapsed = time.time() - poll_start
                    print(f"   ✅ Inpainting complete in {elapsed:.1f}s")

                    outputs = history[prompt_id].get("outputs", {})
                    if not outputs:
                        return GenerationResponse(
                            success=False,
                            error="Inpainting completed but no outputs found"
                        )

                    # Download result images
                    images_base64 = []
                    for node_id, output in outputs.items():
                        if "images" in output:
                            for image_info in output["images"]:
                                filename = image_info.get("filename")
                                subfolder = image_info.get("subfolder", "")

                                if not filename:
                                    continue

                                print(f"   📥 Downloading {filename}...")
                                image_url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type=output"

                                image_response = requests.get(image_url, timeout=30)
                                if image_response.status_code == 200:
                                    image_b64 = base64.b64encode(image_response.content).decode()
                                    images_base64.append(image_b64)
                                    print(f"   ✅ Downloaded {filename}")

                    if not images_base64:
                        return GenerationResponse(
                            success=False,
                            error="No images could be downloaded"
                        )

                    total_time = time.time() - start_time

                    # Save to S3 and local
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    model_name = request.character.lower()
                    s3_base_path = f"inpaints/{model_name}/{timestamp}"
                    local_base_path = f"/workspaces/ai/outputs/{model_name}/{timestamp}"
                    os.makedirs(local_base_path, exist_ok=True)

                    s3_output_url = None
                    try:
                        output_data = base64.b64decode(images_base64[0])

                        # Save locally
                        local_output_path = f"{local_base_path}/inpaint_output.png"
                        with open(local_output_path, "wb") as f:
                            f.write(output_data)
                        print(f"   💾 Saved to {local_output_path}")

                        # Upload to S3
                        s3_output_path = f"{s3_base_path}/inpaint_output.png"
                        s3_output_url = upload_to_s3(output_data, s3_output_path, "image/png")

                        # Save metadata
                        metadata = {
                            "model": model_name,
                            "timestamp": timestamp,
                            "workflow": "inpaint",
                            "prompt": final_prompt,
                            "negative_prompt": request.negative_prompt,
                            "parameters": {
                                "steps": request.num_inference_steps,
                                "cfg_scale": request.guidance_scale,
                                "seed": request.seed,
                                "grok_enhanced": request.use_grok_enhancement
                            },
                            "generation_time": total_time
                        }
                        metadata_json = json.dumps(metadata, indent=2)

                        local_metadata_path = f"{local_base_path}/metadata.json"
                        with open(local_metadata_path, "w") as f:
                            f.write(metadata_json)

                        print(f"💾 Saved locally: {local_base_path}/")
                        print(f"☁️  Saved to S3: {s3_base_path}/")
                    except Exception as e:
                        print(f"⚠️  Save error (non-fatal): {e}")

                    return GenerationResponse(
                        success=True,
                        image_base64=images_base64[0],
                        images_base64=images_base64,
                        generation_time=total_time,
                        s3_output_url=s3_output_url
                    )

                # Still generating
                elapsed = time.time() - poll_start
                if int(elapsed) % 10 == 0:
                    print(f"   ⏳ Still inpainting... ({elapsed:.0f}s)")

                time.sleep(2)

            except Exception as e:
                print(f"   ⚠️  Poll error: {e}")
                time.sleep(2)
                continue

        return GenerationResponse(
            success=False,
            error=f"Inpainting timeout after {max_wait}s"
        )

    except Exception as e:
        print(f"❌ Inpaint error: {e}")
        import traceback
        traceback.print_exc()

        return GenerationResponse(
            success=False,
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting ComfyUI Wrapper API...")
    print(f"   ComfyUI: {COMFYUI_URL}")
    print(f"   Workflow: {WORKFLOW_PATH}")
    print(f"   Server: http://0.0.0.0:8001")
    print("   IMG2IMG: ✅ ENABLED")
    uvicorn.run(app, host="0.0.0.0", port=8001)
