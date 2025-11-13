"""
FastAPI server for RunPod GPU generation
Run this ON RUNPOD to expose generation endpoint
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import torch
from diffusers import DiffusionPipeline, FlowMatchEulerDiscreteScheduler
from diffusers.utils import load_image
import math
import base64
from io import BytesIO
import os
from PIL import Image

app = FastAPI(
    title="RunPod Image Generation API",
    description="Diffusers-based image generation with character LoRAs",
    version="1.0.0"
)

# CORS for Codespaces access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline (loaded once on startup)
pipe = None
current_lora = None

class GenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = "blurry, low quality, distorted"
    character: str = "milan"  # Character name
    width: int = 1024
    height: int = 768
    num_inference_steps: int = 30
    guidance_scale: float = 4.0
    seed: Optional[int] = None
    lora_strength: float = 0.8

    # IMG2IMG support
    init_image_base64: Optional[str] = None  # Base64 encoded input image
    strength: float = 0.85  # Denoise strength (0.0-1.0) - 0.85 matches ComfyUI

    # Batch generation
    num_images: int = 1  # Generate multiple images at once

    # Upscaling
    upscale_factor: float = 1.0  # 1.0=no upscale, 1.5=1.5x, 2.0=2x

class GenerationResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None  # Single image (for backwards compatibility)
    images_base64: Optional[List[str]] = None  # Multiple images (for batch generation)
    error: Optional[str] = None
    generation_time: Optional[float] = None

# Character LoRA mapping
LORA_PATHS = {
    "milan": "/workspace/ComfyUI/models/loras/milan_000002000.safetensors",
    # Add more characters here as you train them
}

def load_pipeline():
    """Load base pipeline once on startup"""
    global pipe

    print("🚀 Loading Qwen-Image pipeline...")

    scheduler_config = {
        "base_image_seq_len": 256,
        "base_shift": math.log(3),
        "num_train_timesteps": 1000,
        "shift": 1.0,
        "use_dynamic_shifting": True,
    }

    scheduler = FlowMatchEulerDiscreteScheduler.from_config(scheduler_config)

    pipe = DiffusionPipeline.from_pretrained(
        "Qwen/Qwen-Image",
        scheduler=scheduler,
        torch_dtype=torch.bfloat16,
        device_map="balanced",
        low_cpu_mem_usage=True
    )

    print("✅ Pipeline loaded!")

def load_lora(character: str, strength: float = 0.8):
    """Load or switch LoRA for character"""
    global pipe, current_lora

    if not pipe:
        raise RuntimeError("Pipeline not initialized")

    # Check if LoRA already loaded
    if current_lora == character:
        print(f"✅ LoRA '{character}' already loaded")
        return

    # Get LoRA path
    lora_path = LORA_PATHS.get(character)
    if not lora_path:
        raise ValueError(f"Unknown character: {character}")

    if not os.path.exists(lora_path):
        raise FileNotFoundError(f"LoRA file not found: {lora_path}")

    print(f"📦 Loading LoRA for '{character}'...")

    # Unload previous LoRA if any
    if current_lora:
        pipe.unfuse_lora()
        pipe.unload_lora_weights()

    # Load new LoRA
    pipe.load_lora_weights(lora_path)
    pipe.fuse_lora(lora_scale=strength)

    current_lora = character
    print(f"✅ LoRA '{character}' loaded (strength: {strength})")

@app.on_event("startup")
async def startup():
    """Load pipeline on server start"""
    load_pipeline()

@app.get("/")
async def root():
    return {
        "status": "online",
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU",
        "pipeline_loaded": pipe is not None,
        "current_lora": current_lora,
        "available_characters": list(LORA_PATHS.keys())
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "cuda_available": torch.cuda.is_available(),
        "pipeline_ready": pipe is not None
    }

@app.post("/generate", response_model=GenerationResponse)
async def generate(request: GenerationRequest):
    """Generate image with character LoRA"""

    if not pipe:
        raise HTTPException(status_code=503, detail="Pipeline not loaded")

    try:
        import time
        start_time = time.time()

        # Load character LoRA
        load_lora(request.character, request.lora_strength)

        # Set seed if provided
        generator = None
        if request.seed:
            generator = torch.manual_seed(request.seed)

        # Check if img2img or text2img
        init_image = None
        if request.init_image_base64:
            # Decode base64 image for img2img
            print(f"🖼️  IMG2IMG mode (strength: {request.strength})")
            image_data = base64.b64decode(request.init_image_base64)
            init_image = Image.open(BytesIO(image_data)).convert("RGB")
            # Resize to target dimensions
            init_image = init_image.resize((request.width, request.height))

        print(f"🎨 Generating {request.num_images} image(s): '{request.prompt[:50]}...'")

        # Generate images (supports batch)
        if init_image:
            # IMG2IMG generation
            result = pipe(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                image=init_image,
                strength=request.strength,  # Denoise amount (0.85 = 85% new, 15% original)
                width=request.width,
                height=request.height,
                num_inference_steps=request.num_inference_steps,
                guidance_scale=request.guidance_scale,
                generator=generator,
                num_images_per_prompt=request.num_images,
            )
        else:
            # TEXT2IMG generation
            result = pipe(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                width=request.width,
                height=request.height,
                num_inference_steps=request.num_inference_steps,
                guidance_scale=request.guidance_scale,
                generator=generator,
                num_images_per_prompt=request.num_images,
            )

        images = result.images

        # Apply upscaling if requested
        if request.upscale_factor > 1.0:
            print(f"🔍 Upscaling {request.upscale_factor}x...")
            upscaled = []
            for img in images:
                new_width = int(img.width * request.upscale_factor)
                new_height = int(img.height * request.upscale_factor)
                upscaled.append(img.resize((new_width, new_height), Image.LANCZOS))
            images = upscaled

        # Convert to base64
        images_base64 = []
        for img in images:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            images_base64.append(base64.b64encode(buffered.getvalue()).decode())

        generation_time = time.time() - start_time

        print(f"✅ Generated {len(images)} image(s) in {generation_time:.1f}s")

        return GenerationResponse(
            success=True,
            image_base64=images_base64[0],  # First image for backwards compatibility
            images_base64=images_base64,  # All images for batch generation
            generation_time=generation_time
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

        return GenerationResponse(
            success=False,
            error=str(e)
        )

@app.get("/characters")
async def list_characters():
    """List available characters"""
    characters = []
    for name, path in LORA_PATHS.items():
        characters.append({
            "id": name,
            "name": name.title(),
            "lora_path": path,
            "exists": os.path.exists(path)
        })
    return characters

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting RunPod Generation API...")
    print("   GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU")
    print("   Server: http://0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
