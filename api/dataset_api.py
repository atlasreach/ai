"""
Dataset Creator API Endpoints
Handles dataset management, character constraints, and caption generation
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dataset_service import DatasetService
from services.grok_service import GrokService
import base64
from supabase import create_client
from dotenv import load_dotenv
import time

load_dotenv()

# Initialize services
dataset_service = DatasetService()
grok_service = GrokService()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create router
router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateDatasetRequest(BaseModel):
    character_id: str
    name: str
    dataset_type: str  # "SFW" or "NSFW"
    description: Optional[str] = None
    dataset_constraints: Optional[Dict] = None

class UpdateConstraintsRequest(BaseModel):
    constraints: Dict

class AddConstraintRequest(BaseModel):
    key: str
    value: str
    constraint_type: str = "physical"

class GenerateCaptionsRequest(BaseModel):
    dataset_id: str
    image_urls: List[str]  # URLs of images to caption

class UpdateCaptionRequest(BaseModel):
    caption: str

# ============================================================================
# CHARACTER CONSTRAINTS ENDPOINTS
# ============================================================================

@router.get("/characters/{character_id}")
async def get_character(character_id: str):
    """Get character with constraints"""
    character = dataset_service.get_character_with_constraints(character_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    return {
        "success": True,
        "character": character
    }

@router.put("/characters/{character_id}/constraints")
async def update_character_constraints(
    character_id: str,
    request: UpdateConstraintsRequest
):
    """Update character constraints"""
    success = dataset_service.update_character_constraints(
        character_id,
        request.constraints
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to update constraints")

    return {
        "success": True,
        "message": "Constraints updated"
    }

@router.post("/characters/{character_id}/constraints/add")
async def add_character_constraint(
    character_id: str,
    request: AddConstraintRequest
):
    """Add a single constraint to character"""
    success = dataset_service.add_character_constraint(
        character_id,
        request.key,
        request.value,
        request.constraint_type
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to add constraint")

    # Return updated character
    character = dataset_service.get_character_with_constraints(character_id)

    return {
        "success": True,
        "character": character
    }

@router.delete("/characters/{character_id}/constraints/{key}")
async def remove_character_constraint(character_id: str, key: str):
    """Remove a constraint from character"""
    success = dataset_service.remove_character_constraint(character_id, key)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove constraint")

    # Return updated character
    character = dataset_service.get_character_with_constraints(character_id)

    return {
        "success": True,
        "character": character
    }

# ============================================================================
# TRAINING DATASET ENDPOINTS
# ============================================================================

@router.post("/create")
async def create_dataset(request: CreateDatasetRequest):
    """Create a new training dataset"""
    dataset_id = dataset_service.create_training_dataset(
        request.character_id,
        request.name,
        request.dataset_type,
        request.description,
        request.dataset_constraints
    )

    if not dataset_id:
        raise HTTPException(status_code=400, detail="Failed to create dataset")

    dataset = dataset_service.get_dataset(dataset_id)

    return {
        "success": True,
        "dataset": dataset
    }

@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get dataset details"""
    dataset = dataset_service.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "success": True,
        "dataset": dataset
    }

@router.get("/character/{character_id}")
async def get_character_datasets(character_id: str):
    """Get all datasets for a character"""
    datasets = dataset_service.get_character_datasets(character_id)

    return {
        "success": True,
        "datasets": datasets
    }

@router.put("/{dataset_id}/constraints")
async def update_dataset_constraints(
    dataset_id: str,
    request: UpdateConstraintsRequest
):
    """Update dataset constraints"""
    success = dataset_service.update_dataset_constraints(
        dataset_id,
        request.constraints
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to update constraints")

    return {
        "success": True,
        "message": "Dataset constraints updated"
    }

# ============================================================================
# TRAINING IMAGES ENDPOINTS
# ============================================================================

@router.get("/{dataset_id}/images")
async def get_dataset_images(dataset_id: str):
    """Get all images in a dataset"""
    images = dataset_service.get_dataset_images(dataset_id)

    return {
        "success": True,
        "images": images
    }

@router.put("/images/{image_id}/caption")
async def update_image_caption(image_id: str, request: UpdateCaptionRequest):
    """Update caption for a training image"""
    success = dataset_service.update_training_image_caption(
        image_id,
        request.caption
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to update caption")

    return {
        "success": True,
        "message": "Caption updated"
    }

@router.delete("/images/{image_id}")
async def delete_training_image(image_id: str):
    """Delete a training image"""
    success = dataset_service.delete_training_image(image_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete image")

    return {
        "success": True,
        "message": "Image deleted"
    }

@router.post("/{dataset_id}/upload-images")
async def upload_training_images(
    dataset_id: str,
    files: List[UploadFile] = File(...)
):
    """
    Upload multiple images and auto-generate captions

    This endpoint:
    1. Uploads images to Supabase Storage
    2. Automatically generates captions with Grok AI
    3. Adds images + captions to training_images table

    Returns list of uploaded images with their captions
    """
    # Validate dataset exists
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get character for caption generation
    character = dataset_service.get_character_with_constraints(dataset['character_id'])
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Build Grok prompt once for all images
    grok_prompt = dataset_service.build_grok_prompt(character, dataset)

    results = []
    current_image_count = dataset.get('image_count', 0)

    for i, file in enumerate(files):
        try:
            # Read file content
            file_content = await file.read()

            # Generate unique filename
            timestamp = int(time.time() * 1000)
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            storage_filename = f"{dataset_id}/{timestamp}_{i}.{file_extension}"

            # Upload to Supabase Storage
            storage_response = supabase.storage.from_('training-images').upload(
                storage_filename,
                file_content,
                {'content-type': file.content_type or 'image/jpeg'}
            )

            # Get public URL
            public_url = supabase.storage.from_('training-images').get_public_url(storage_filename)

            # Auto-generate caption with Grok
            try:
                caption = await grok_service.generate_caption_from_url(public_url, grok_prompt)
            except Exception as caption_error:
                # If caption generation fails, use trigger word as fallback
                caption = character['trigger_word']
                print(f"⚠️ Caption generation failed for {file.filename}: {caption_error}")

            # Add to training_images table
            image_id = dataset_service.add_training_image(
                dataset_id,
                public_url,
                caption,
                metadata={'original_filename': file.filename, 'storage_path': storage_filename},
                display_order=current_image_count + i
            )

            results.append({
                "success": True,
                "image_id": image_id,
                "image_url": public_url,
                "caption": caption,
                "filename": file.filename
            })

        except Exception as e:
            results.append({
                "success": False,
                "filename": file.filename,
                "error": str(e)
            })

    # Count successes
    succeeded = sum(1 for r in results if r.get("success"))
    failed = len(results) - succeeded

    # Generate 5 validation prompts based on captions
    if succeeded > 0:
        try:
            # Get all captions from successful uploads
            captions = [r['caption'] for r in results if r.get("success")]

            # Create prompt for Grok to generate validation prompts
            validation_prompt = f"""Based on these image captions from a training dataset, generate 5 diverse validation prompts to test the trained LoRA model. Each prompt should use the trigger word '{character['trigger_word']}' and test different scenarios/styles.

Training captions:
{chr(10).join(f'- {c}' for c in captions[:10])}

Generate 5 validation prompts as a JSON array. Each prompt should be creative and test different aspects (poses, lighting, settings, styles, etc.).

Format: ["prompt 1", "prompt 2", "prompt 3", "prompt 4", "prompt 5"]"""

            validation_prompts_json = await grok_service.generate_text_completion(
                validation_prompt
            )

            # Try to parse JSON, fallback to default prompts if fails
            import json
            try:
                validation_prompts = json.loads(validation_prompts_json)
            except:
                # Fallback to simple prompts if JSON parsing fails
                trigger = character['trigger_word']
                validation_prompts = [
                    f"{trigger}, professional portrait, studio lighting",
                    f"{trigger}, casual photo, outdoor setting, natural light",
                    f"{trigger}, creative composition, artistic style",
                    f"{trigger}, close-up shot, detailed",
                    f"{trigger}, full body photo, dynamic pose"
                ]

            # Store validation prompts in dataset
            dataset_service.update_dataset(dataset_id, {
                'validation_prompts': validation_prompts
            })

            print(f"✅ Generated {len(validation_prompts)} validation prompts for dataset {dataset_id}")
        except Exception as e:
            print(f"⚠️ Failed to generate validation prompts: {e}")

    return {
        "success": True,
        "results": results,
        "total": len(files),
        "succeeded": succeeded,
        "failed": failed,
        "message": f"Uploaded {succeeded}/{len(files)} images with auto-generated captions"
    }

# ============================================================================
# CAPTION GENERATION ENDPOINTS
# ============================================================================

@router.get("/{dataset_id}/preview-template")
async def preview_caption_template(dataset_id: str):
    """Preview caption template for a dataset"""
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    character = dataset_service.get_character_with_constraints(dataset['character_id'])
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    caption_format = dataset_service.build_caption_format(character, dataset)
    grok_prompt = dataset_service.build_grok_prompt(character, dataset)

    return {
        "success": True,
        "caption_format": caption_format,
        "grok_prompt": grok_prompt,
        "character": character,
        "dataset": dataset
    }

@router.post("/{dataset_id}/generate-caption")
async def generate_single_caption(
    dataset_id: str,
    image_url: str
):
    """Generate caption for a single image using Grok"""
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    character = dataset_service.get_character_with_constraints(dataset['character_id'])
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Build Grok prompt
    grok_prompt = dataset_service.build_grok_prompt(character, dataset)

    # Generate caption with Grok
    try:
        caption = await grok_service.generate_caption_from_url(image_url, grok_prompt)

        return {
            "success": True,
            "caption": caption,
            "image_url": image_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate caption: {str(e)}")

@router.post("/{dataset_id}/generate-captions-batch")
async def generate_captions_batch(
    dataset_id: str,
    request: GenerateCaptionsRequest
):
    """Generate captions for multiple images"""
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    character = dataset_service.get_character_with_constraints(dataset['character_id'])
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Build Grok prompt
    grok_prompt = dataset_service.build_grok_prompt(character, dataset)

    # Generate captions for all images
    results = []
    for i, image_url in enumerate(request.image_urls):
        try:
            caption = await grok_service.generate_caption_from_url(image_url, grok_prompt)

            # Add to dataset
            image_id = dataset_service.add_training_image(
                dataset_id,
                image_url,
                caption,
                display_order=i
            )

            results.append({
                "image_id": image_id,
                "image_url": image_url,
                "caption": caption,
                "success": True
            })
        except Exception as e:
            results.append({
                "image_url": image_url,
                "error": str(e),
                "success": False
            })

    return {
        "success": True,
        "results": results,
        "total": len(request.image_urls),
        "succeeded": sum(1 for r in results if r["success"])
    }

# Export router
__all__ = ["router"]
