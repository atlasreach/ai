"""
Generation API Router
Endpoints for AI image generation
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

from backend.models.characters import get_character
from backend.services.groq_service import GroqService
from backend.services.comfyui_service import ComfyUIService
from backend.services.s3_service import S3Service


router = APIRouter(prefix="/generate", tags=["generate"])

# Initialize services
groq_service = GroqService()
comfyui_service = ComfyUIService()
s3_service = S3Service()


class GenerationRequest(BaseModel):
    """Request model for image generation"""
    character_id: str = Field(..., description="Character ID to use")
    prompt: str = Field(..., description="User's generation prompt")
    negative_prompt: Optional[str] = Field("", description="Negative prompt (optional)")
    use_groq_enhancement: bool = Field(True, description="Auto-enhance prompt with Grok")
    lora_strength: Optional[float] = Field(None, description="Override LoRA strength (0.1-2.0)")
    cfg_scale: float = Field(4.0, description="CFG scale (1.0-20.0)", ge=1.0, le=20.0)
    steps: int = Field(30, description="Sampling steps (10-100)", ge=10, le=100)
    denoise: float = Field(0.85, description="Denoise strength (0.0-1.0)", ge=0.0, le=1.0)
    seed: int = Field(-1, description="Random seed (-1 for random)")
    batch_size: int = Field(1, description="Number of images (1-10)", ge=1, le=10)
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class GenerationResponse(BaseModel):
    """Response model for image generation"""
    job_id: str
    character_id: str
    prompt: str
    enhanced_prompt: str
    image_urls: List[str]
    generation_time_seconds: float
    parameters: dict


@router.post("/", response_model=GenerationResponse)
async def generate_image(
    character_id: str = Form(...),
    prompt: str = Form(...),
    reference_image: UploadFile = File(...),
    negative_prompt: str = Form(""),
    use_groq_enhancement: bool = Form(True),
    lora_strength: Optional[float] = Form(None),
    cfg_scale: float = Form(4.0),
    steps: int = Form(30),
    denoise: float = Form(0.85),
    seed: int = Form(-1),
    batch_size: int = Form(1),
    user_id: Optional[str] = Form(None)
):
    """
    Generate AI images using character LoRA

    Args:
        character_id: Character to use
        prompt: Generation prompt
        reference_image: Reference image file upload
        negative_prompt: Negative prompt (optional)
        use_groq_enhancement: Auto-enhance prompt
        lora_strength: Override LoRA strength
        cfg_scale: CFG scale
        steps: Sampling steps
        denoise: Denoise strength
        seed: Random seed
        batch_size: Number of images
        user_id: Optional user ID

    Returns:
        GenerationResponse with image URLs and metadata
    """
    import time
    start_time = time.time()

    job_id = str(uuid.uuid4())

    try:
        # 1. Get character configuration
        try:
            character = get_character(character_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Character '{character_id}' not found")

        # 2. Read reference image
        reference_image_bytes = await reference_image.read()

        # 3. Upload reference image to ComfyUI
        ref_filename = f"{job_id}_reference.png"
        upload_success = await comfyui_service.upload_reference_image(
            reference_image_bytes,
            ref_filename
        )

        if not upload_success:
            raise HTTPException(status_code=500, detail="Failed to upload reference image to ComfyUI")

        # 4. Enhance prompt with Grok (if enabled)
        if use_groq_enhancement:
            enhanced_prompt = await groq_service.enhance_prompt(
                prompt,
                character.trigger_word,
                style="instagram influencer"
            )
        else:
            # Add trigger word manually
            if not prompt.startswith(character.trigger_word):
                enhanced_prompt = f"{character.trigger_word}, {prompt}"
            else:
                enhanced_prompt = prompt

        # 5. Generate negative prompt if not provided
        if not negative_prompt and use_groq_enhancement:
            negative_prompt = await groq_service.suggest_negative_prompt(enhanced_prompt)

        # 6. Load and update workflow
        use_batch = batch_size > 1
        workflow = comfyui_service.load_workflow(batch=use_batch)

        # Use character's default LoRA strength or override
        final_lora_strength = lora_strength if lora_strength is not None else character.lora_strength

        workflow = comfyui_service.update_workflow(
            workflow=workflow,
            character_lora=character.lora_model,
            lora_strength=final_lora_strength,
            positive_prompt=enhanced_prompt,
            negative_prompt=negative_prompt,
            reference_image_name=ref_filename,
            cfg_scale=cfg_scale,
            steps=steps,
            denoise=denoise,
            seed=seed,
            batch_size=batch_size
        )

        # 7. Queue generation on ComfyUI
        prompt_id = await comfyui_service.queue_prompt(workflow, client_id=job_id)

        # 8. Wait for completion
        history = await comfyui_service.wait_for_completion(
            prompt_id,
            timeout=300  # 5 minutes
        )

        if not history:
            raise HTTPException(status_code=504, detail="Generation timeout - please try again")

        # 9. Extract generated image URLs from ComfyUI
        comfyui_image_urls = comfyui_service.extract_image_urls(history)

        if not comfyui_image_urls:
            raise HTTPException(status_code=500, detail="No images generated")

        # 10. Download images from ComfyUI and upload to S3
        s3_urls = []
        for comfyui_url in comfyui_image_urls:
            # Download from ComfyUI
            image_bytes = await comfyui_service.download_image(comfyui_url)

            # Upload to S3
            s3_url = await s3_service.upload_image(
                image_bytes,
                character_id=character_id,
                user_id=user_id,
                prefix="generated"
            )
            s3_urls.append(s3_url)

        # 11. Calculate generation time
        generation_time = time.time() - start_time

        # 12. Return response
        return GenerationResponse(
            job_id=job_id,
            character_id=character_id,
            prompt=prompt,
            enhanced_prompt=enhanced_prompt,
            image_urls=s3_urls,
            generation_time_seconds=round(generation_time, 2),
            parameters={
                "lora_model": character.lora_model,
                "lora_strength": final_lora_strength,
                "cfg_scale": cfg_scale,
                "steps": steps,
                "denoise": denoise,
                "seed": seed,
                "batch_size": batch_size,
                "negative_prompt": negative_prompt
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/status/{job_id}")
async def get_generation_status(job_id: str):
    """
    Get status of a generation job

    Args:
        job_id: Job ID from generate endpoint

    Returns:
        Status information
    """
    # TODO: Implement job status tracking with database/cache
    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Status tracking coming soon"
    }
