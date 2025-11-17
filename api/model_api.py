"""
Model & Dataset API for New Schema
Handles model management, feature analysis, and caption generation
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import sys
import os
import io
import zipfile
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.grok_service import GrokService
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize services
grok_service = GrokService()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create router
router = APIRouter(prefix="/api", tags=["models"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalyzeFeaturesRequest(BaseModel):
    image_urls: List[str]

class GenerateCaptionRequest(BaseModel):
    image_url: str
    model_id: str

class BatchCaptionsRequest(BaseModel):
    dataset_id: str

class ScrapeInstagramRequest(BaseModel):
    instagram_username: str
    model_id: str
    dataset_name: str
    num_posts: int = 20

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/scrape-instagram")
async def scrape_instagram(request: ScrapeInstagramRequest):
    """
    Scrape Instagram account and create a dataset
    """
    try:
        # Get Apify token from env
        apify_token = os.getenv('APIFY_API_TOKEN')
        if not apify_token:
            raise HTTPException(status_code=500, detail="APIFY_API_TOKEN not configured")

        # Verify model exists
        model_result = supabase.table('models').select('*').eq('id', request.model_id).single().execute()
        if not model_result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        # Call Apify Instagram scraper
        import requests as req
        import json as json_lib

        apify_url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={apify_token}"

        payload = {
            "directUrls": [f"https://www.instagram.com/{request.instagram_username}/"],
            "resultsType": "posts",
            "resultsLimit": request.num_posts
        }

        print(f"Scraping Instagram @{request.instagram_username}...")
        response = req.post(apify_url, json=payload, timeout=180)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Apify API failed: {response.text}")

        posts = response.json()

        if not posts or len(posts) == 0:
            raise HTTPException(status_code=404, detail="No posts found or account is private")

        # Create dataset in database
        dataset_data = {
            'model_id': request.model_id,
            'name': request.dataset_name,
            'source': f'instagram:{request.instagram_username}',
            'training_status': 'preparing'
        }

        dataset_result = supabase.table('datasets').insert(dataset_data).execute()
        dataset = dataset_result.data[0]
        dataset_id = dataset['id']

        # Process posts and save images
        saved_images = []

        for idx, post in enumerate(posts):
            post_type = post.get('type')

            # Handle different post types
            image_urls = []

            if post_type == 'Image' or post_type == 'Video':
                if post.get('displayUrl'):
                    image_urls.append(post['displayUrl'])
            elif post_type == 'Sidecar':
                # Carousel post - get all images
                image_urls = post.get('images', [])

            # Save each image to dataset
            for img_idx, img_url in enumerate(image_urls):
                caption = post.get('caption', '')

                image_data = {
                    'dataset_id': dataset_id,
                    'image_url': img_url,
                    'caption': caption,
                    'display_order': len(saved_images),
                    'metadata': {
                        'instagram_post_url': post.get('url'),
                        'likes': post.get('likesCount'),
                        'comments': post.get('commentsCount'),
                        'post_type': post_type,
                        'timestamp': post.get('timestamp')
                    }
                }

                result = supabase.table('dataset_images').insert(image_data).execute()
                saved_images.append(result.data[0])

        return {
            "success": True,
            "dataset_id": dataset_id,
            "dataset_name": request.dataset_name,
            "images_saved": len(saved_images),
            "posts_scraped": len(posts),
            "message": f"Successfully scraped {len(posts)} posts with {len(saved_images)} images from @{request.instagram_username}"
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Instagram scraping failed: {str(e)}")

@router.post("/analyze-features")
async def analyze_features(request: AnalyzeFeaturesRequest):
    """
    Analyze sample images with Grok to extract defining features
    """
    if not request.image_urls or len(request.image_urls) < 3:
        raise HTTPException(status_code=400, detail="Please provide at least 3 images")

    try:
        # Build Grok prompt for feature analysis
        prompt = """Analyze these photos of the same person. Identify consistent defining features:

- Hair: color, length, style
- Eyes: color, shape
- Skin: tone, complexion
- Face: shape, distinctive features
- Body: build, physique
- Other: any unique characteristics

Return ONLY a JSON object like this:
{
  "hair": "long blonde wavy hair",
  "eyes": "blue eyes",
  "skin": "fair skin with natural glow",
  "face": "heart-shaped face, high cheekbones",
  "body": "athletic build, toned",
  "other": "minimal makeup, natural look"
}"""

        # Call Grok with multiple images
        # For now, using first image - in production would send all to Grok
        response = await grok_service.generate_caption_from_url(
            image_url=request.image_urls[0],
            custom_prompt=prompt
        )

        # Try to parse JSON from response
        import json
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                features_json = response[start:end]
                features = json.loads(features_json)
            else:
                # Fallback: create structured response
                features = {
                    "hair": "Please analyze manually",
                    "eyes": "Please analyze manually",
                    "skin": "Please analyze manually"
                }
        except:
            features = {
                "raw_analysis": response
            }

        return {
            "success": True,
            "features": features
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature analysis failed: {str(e)}")


@router.post("/datasets/{dataset_id}/generate-all-captions")
async def generate_all_captions(dataset_id: str):
    """
    Generate captions for all images in a dataset using new schema
    """
    try:
        # Get dataset and model info
        dataset_result = supabase.table('datasets').select('*').eq('id', dataset_id).single().execute()

        if not dataset_result.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        dataset_data = dataset_result.data

        # Get model info
        model_result = supabase.table('models').select('*').eq('id', dataset_data['model_id']).single().execute()

        if not model_result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        model_data = model_result.data

        # Get all images for this dataset
        images = supabase.table('dataset_images')\
            .select('*')\
            .eq('dataset_id', dataset_id)\
            .order('display_order')\
            .execute()

        if not images.data:
            raise HTTPException(status_code=404, detail="No images found")

        # Build caption template
        trigger_word = model_data.get('trigger_word', '')
        defining_features = model_data.get('defining_features', {})

        # Create feature string
        feature_parts = []
        for key, value in defining_features.items():
            if key != 'other' and value:
                feature_parts.append(value)

        if feature_parts:
            feature_string = ', '.join(feature_parts)
            base_template = f"{trigger_word}, {feature_string}"
        else:
            base_template = trigger_word

        # Generate caption for each image that doesn't have one
        updated_count = 0
        skipped_count = 0
        errors = []

        for img in images.data:
            # Skip if already has caption
            if img.get('caption') and img['caption'].strip():
                skipped_count += 1
                continue
            try:
                # Build prompt for this image
                prompt = f"""You are captioning training images for AI model training.

Create a detailed, natural caption in 25-75 words that describes this image. Include:
- The character identifier: {trigger_word},
- Specific clothing details (colors, styles, fit)
- Exact pose and body position, hand positining on her body
- Facial expression and where they're looking
- Background and setting details
- Lighting type and mood
- Any objects or props visible

Start with "{trigger_word}" then describe naturally and specifically what you see.

Example style: "testmodel wearing fitted black leather jacket over white tshirt, standing with arms crossed, confident smirk, looking directly at camera, urban brick wall background, golden hour lighting"

Be specific and detailed. Also if nfsw content be desriptive as possible about what you see. Avoid generic words like "nice" or "beautiful"."""

                caption = await grok_service.generate_caption_from_url(
                    image_url=img['image_url'],
                    custom_prompt=prompt
                )

                # Clean up caption
                caption = caption.strip()
                if not caption.startswith(trigger_word):
                    caption = f"{base_template}, {caption}"

                # Update database
                supabase.table('dataset_images')\
                    .update({'caption': caption})\
                    .eq('id', img['id'])\
                    .execute()

                updated_count += 1

            except Exception as e:
                error_msg = f"Error for image {img['id']}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                continue

        # Generate 10 test captions for manual AI Toolkit training
        test_captions = []
        try:
            # Re-fetch images to get updated captions
            fresh_images = supabase.table('dataset_images')\
                .select('*')\
                .eq('dataset_id', dataset_id)\
                .order('display_order')\
                .execute()

            # Get sample captions to match the style
            captioned_images = [img for img in fresh_images.data if img.get('caption')]

            if captioned_images:
                # Use first 3-5 captions as examples
                example_captions = [img['caption'] for img in captioned_images[:min(5, len(captioned_images))]]
                examples_text = '\n'.join([f"- {cap}" for cap in example_captions])

                test_prompt = f"""You are generating additional training captions that match the EXACT style and format of existing captions.

Here are example captions from this dataset:
{examples_text}

Generate EXACTLY 10 new captions in the EXACT same style, format, length, and detail level. They should:
- Start the same way (with "{trigger_word}")
- Have the same level of detail and specificity
- Use similar descriptive language
- Match the same word count and structure
- Vary the scenarios (different poses, clothing, settings, lighting, expressions)

IMPORTANT: Return EXACTLY 10 captions, one per line. No numbering, no extra text, no commentary. Just 10 captions."""

                test_caption_response = await grok_service.generate_caption_from_url(
                    image_url=images.data[0]['image_url'],  # Use first image as reference
                    custom_prompt=test_prompt
                )
            else:
                # Fallback if no captions yet
                test_caption_response = ""

            # Parse captions
            test_captions = [line.strip() for line in test_caption_response.split('\n') if line.strip()]

        except Exception as e:
            print(f"Failed to generate test captions: {str(e)}")

        return {
            "success": True,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "total_images": len(images.data),
            "errors": errors,
            "test_captions": test_captions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch caption generation failed: {str(e)}")


@router.post("/datasets/{dataset_id}/generate-caption/{image_id}")
async def generate_single_caption(dataset_id: str, image_id: str, request: dict):
    """
    Generate caption for a single image
    """
    try:
        # Get dataset and model info
        dataset_result = supabase.table('datasets').select('*').eq('id', dataset_id).single().execute()
        if not dataset_result.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        dataset_data = dataset_result.data

        # Get model info
        model_result = supabase.table('models').select('*').eq('id', dataset_data['model_id']).single().execute()
        if not model_result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        model_data = model_result.data

        # Get the specific image
        image_result = supabase.table('dataset_images').select('*').eq('id', image_id).single().execute()
        if not image_result.data:
            raise HTTPException(status_code=404, detail="Image not found")

        image_data = image_result.data

        # Build caption template
        trigger_word = model_data.get('trigger_word', '')
        defining_features = model_data.get('defining_features', {})

        # Create feature string
        feature_parts = []
        for key, value in defining_features.items():
            if key != 'other' and value:
                feature_parts.append(value)

        if feature_parts:
            feature_string = ', '.join(feature_parts)
            base_template = f"{trigger_word}, {feature_string}"
        else:
            base_template = trigger_word

        # Build prompt
        prompt = request.get('prompt') or f"""You are captioning training images for AI model training.

Create a detailed, natural caption in 25-40 words that describes this image. Include:
- The character identifier: {trigger_word}
- Specific clothing details (colors, styles, fit)
- Exact pose and body position
- Facial expression and where they're looking
- Background and setting details
- Lighting type and mood
- Any objects or props visible if not visable just ignore this part

Start with "{trigger_word}" then describe naturally and specifically what you see.

Example style: "testmodel wearing fitted black leather jacket over white tshirt, standing with arms crossed, confident smirk, looking directly at camera, urban brick wall background, golden hour lighting"

Be specific and detailed. Avoid generic words like "nice" or "beautiful"."""

        # Generate caption with Grok
        caption = await grok_service.generate_caption_from_url(
            image_url=image_data['image_url'],
            custom_prompt=prompt
        )

        # Clean up caption
        caption = caption.strip()
        if not caption.startswith(trigger_word):
            caption = f"{base_template}, {caption}"

        # Update database
        supabase.table('dataset_images')\
            .update({'caption': caption})\
            .eq('id', image_id)\
            .execute()

        return {
            "success": True,
            "caption": caption,
            "image_id": image_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Caption generation failed: {str(e)}")


@router.post("/datasets/{dataset_id}/update-training-status")
async def update_training_status(
    dataset_id: str,
    lora_filename: str,
    huggingface_url: Optional[str] = None,
    training_notes: Optional[str] = None
):
    """
    Update dataset after training is complete
    """
    try:
        update_data = {
            'lora_filename': lora_filename,
            'training_status': 'trained'
        }

        if huggingface_url:
            update_data['huggingface_url'] = huggingface_url
        if training_notes:
            update_data['training_notes'] = training_notes

        result = supabase.table('datasets')\
            .update(update_data)\
            .eq('id', dataset_id)\
            .execute()

        return {
            "success": True,
            "dataset": result.data[0] if result.data else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update training status: {str(e)}")


@router.get("/models/{model_id}/datasets")
async def get_model_datasets(model_id: str):
    """
    Get all datasets for a model
    """
    try:
        result = supabase.table('datasets')\
            .select('*')\
            .eq('model_id', model_id)\
            .order('created_at', desc=True)\
            .execute()

        return {
            "success": True,
            "datasets": result.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch datasets: {str(e)}")


# Temp file upload for content generation
@router.post("/upload-temp")
async def upload_temp_file(file: UploadFile = File(...)):
    """
    Upload temporary file for content generation
    """
    try:
        # Read file content
        contents = await file.read()

        # Upload to Supabase storage (temp folder)
        file_name = f"temp/{file.filename}"

        result = supabase.storage\
            .from_('training-images')\
            .upload(file_name, contents, {'upsert': 'true'})

        # Get public URL
        url_data = supabase.storage\
            .from_('training-images')\
            .get_public_url(file_name)

        return {
            "success": True,
            "url": url_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """
    Delete a dataset and all its images
    """
    try:
        # Delete dataset (cascade will delete images due to foreign key)
        result = supabase.table('datasets')\
            .delete()\
            .eq('id', dataset_id)\
            .execute()

        return {
            "success": True,
            "message": "Dataset deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {str(e)}")


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    """
    Delete a model and all its datasets (cascade will delete images)
    """
    try:
        # Delete model (cascade will delete datasets and images due to foreign keys)
        result = supabase.table('models')\
            .delete()\
            .eq('id', model_id)\
            .execute()

        return {
            "success": True,
            "message": "Model deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@router.get("/datasets/{dataset_id}/download")
async def download_dataset(dataset_id: str):
    """
    Download dataset as ZIP with images and caption text files
    """
    try:
        # Get dataset info
        dataset_result = supabase.table('datasets').select('*').eq('id', dataset_id).single().execute()
        if not dataset_result.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        dataset = dataset_result.data
        dataset_name = dataset['name']

        # Get all images with captions
        images_result = supabase.table('dataset_images')\
            .select('*')\
            .eq('dataset_id', dataset_id)\
            .order('display_order')\
            .execute()

        if not images_result.data:
            raise HTTPException(status_code=404, detail="No images found")

        # Create ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add each image and its caption
            for idx, img in enumerate(images_result.data, start=1):
                # Download image from URL
                img_response = requests.get(img['image_url'])
                if img_response.status_code == 200:
                    # Get file extension from URL
                    ext = img['image_url'].split('.')[-1].split('?')[0]
                    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                        ext = 'jpg'

                    # Create filenames
                    base_name = f"{dataset_name}_{idx:04d}"
                    img_filename = f"{base_name}.{ext}"
                    txt_filename = f"{base_name}.txt"

                    # Add image to zip
                    zip_file.writestr(img_filename, img_response.content)

                    # Add caption text file
                    if img.get('caption'):
                        zip_file.writestr(txt_filename, img['caption'])

            # Add test captions if they exist (we'll need to fetch from somewhere)
            # For now, add a placeholder - you can enhance this later
            # zip_file.writestr("test_captions.txt", "Test captions here")

        # Prepare the response
        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={dataset_name}.zip"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
