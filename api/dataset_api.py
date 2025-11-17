"""
Dataset API
Handles training and content generation datasets for model training
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import zipfile
import io
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# ============================================================
# PYDANTIC MODELS
# ============================================================

class DatasetCreate(BaseModel):
    name: str
    type: str  # 'training' or 'content_generation'
    model_id: str
    description: Optional[str] = None

class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Dataset(BaseModel):
    id: str
    name: str
    type: str
    model_id: str
    description: Optional[str]
    image_count: int
    created_at: datetime
    updated_at: datetime

class DatasetImageAdd(BaseModel):
    source: str  # 'instagram' or 'upload'
    image_url: str
    instagram_post_id: Optional[str] = None
    caption: Optional[str] = None

# ============================================================
# DATASET CRUD
# ============================================================

@router.post("/", response_model=Dataset)
async def create_dataset(dataset: DatasetCreate):
    """Create a new dataset"""
    try:
        result = supabase.table('datasets').insert({
            'name': dataset.name,
            'type': dataset.type,
            'model_id': dataset.model_id,
            'description': dataset.description,
            'image_count': 0
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create dataset")

        return result.data[0]

    except Exception as e:
        print(f"Error creating dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Dataset])
async def list_datasets(model_id: Optional[str] = None, type: Optional[str] = None):
    """Get all datasets, optionally filtered by model or type"""
    try:
        query = supabase.table('datasets').select('*')

        if model_id:
            query = query.eq('model_id', model_id)
        if type:
            query = query.eq('type', type)

        result = query.order('created_at', desc=True).execute()

        return result.data or []

    except Exception as e:
        print(f"Error listing datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get a single dataset with its images"""
    try:
        # Get dataset
        dataset_result = supabase.table('datasets')\
            .select('*')\
            .eq('id', dataset_id)\
            .single()\
            .execute()

        if not dataset_result.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Get images
        images_result = supabase.table('dataset_images')\
            .select('*')\
            .eq('dataset_id', dataset_id)\
            .order('created_at', desc=False)\
            .execute()

        return {
            "success": True,
            "dataset": dataset_result.data,
            "images": images_result.data or []
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{dataset_id}", response_model=Dataset)
async def update_dataset(dataset_id: str, update: DatasetUpdate):
    """Update a dataset"""
    try:
        update_data = {k: v for k, v in update.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_data['updated_at'] = datetime.utcnow().isoformat()

        result = supabase.table('datasets')\
            .update(update_data)\
            .eq('id', dataset_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset and all its images"""
    try:
        result = supabase.table('datasets')\
            .delete()\
            .eq('id', dataset_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return {"success": True, "message": "Dataset deleted"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# DATASET IMAGES
# ============================================================

@router.post("/{dataset_id}/images")
async def add_image_to_dataset(dataset_id: str, image: DatasetImageAdd):
    """Add an image to a dataset"""
    try:
        result = supabase.table('dataset_images').insert({
            'dataset_id': dataset_id,
            'image_url': image.image_url,
            'source': image.source,
            'instagram_post_id': image.instagram_post_id,
            'caption': image.caption
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to add image")

        # Update dataset image count
        count_result = supabase.table('dataset_images')\
            .select('id', count='exact')\
            .eq('dataset_id', dataset_id)\
            .execute()

        supabase.table('datasets')\
            .update({'image_count': count_result.count})\
            .eq('id', dataset_id)\
            .execute()

        return {"success": True, "image": result.data[0]}

    except Exception as e:
        print(f"Error adding image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dataset_id}/images/bulk")
async def add_images_bulk(dataset_id: str, images: List[DatasetImageAdd]):
    """Add multiple images to a dataset at once"""
    try:
        image_data = []
        for img in images:
            image_data.append({
                'dataset_id': dataset_id,
                'image_url': img.image_url,
                'source': img.source,
                'instagram_post_id': img.instagram_post_id,
                'caption': img.caption
            })

        result = supabase.table('dataset_images').insert(image_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to add images")

        # Update dataset image count
        count_result = supabase.table('dataset_images')\
            .select('id', count='exact')\
            .eq('dataset_id', dataset_id)\
            .execute()

        supabase.table('datasets')\
            .update({'image_count': count_result.count})\
            .eq('id', dataset_id)\
            .execute()

        return {"success": True, "images_added": len(result.data)}

    except Exception as e:
        print(f"Error adding images bulk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{dataset_id}/images/{image_id}")
async def remove_image_from_dataset(dataset_id: str, image_id: str):
    """Remove an image from a dataset"""
    try:
        result = supabase.table('dataset_images')\
            .delete()\
            .eq('id', image_id)\
            .eq('dataset_id', dataset_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Image not found")

        # Update dataset image count
        count_result = supabase.table('dataset_images')\
            .select('id', count='exact')\
            .eq('dataset_id', dataset_id)\
            .execute()

        supabase.table('datasets')\
            .update({'image_count': count_result.count or 0})\
            .eq('id', dataset_id)\
            .execute()

        return {"success": True, "message": "Image removed"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error removing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dataset_id}/upload")
async def upload_images_to_dataset(
    dataset_id: str,
    files: List[UploadFile] = File(...)
):
    """Upload one or more images to a dataset"""
    try:
        # Verify dataset exists
        dataset = supabase.table('datasets').select('id').eq('id', dataset_id).execute()
        if not dataset.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        uploaded_images = []

        for file in files:
            # Read file
            file_content = await file.read()

            # Generate unique filename
            file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            filename = f"datasets/{dataset_id}/{uuid.uuid4()}.{file_ext}"

            # Upload to Supabase storage
            supabase.storage.from_('images').upload(
                filename,
                file_content,
                {'content-type': file.content_type, 'upsert': 'true'}
            )

            # Get public URL
            image_url = supabase.storage.from_('images').get_public_url(filename)

            # Add to dataset
            result = supabase.table('dataset_images').insert({
                'dataset_id': dataset_id,
                'image_url': image_url,
                'source': 'upload'
            }).execute()

            if result.data:
                uploaded_images.append(result.data[0])

        # Update dataset image count
        count_result = supabase.table('dataset_images')\
            .select('id', count='exact')\
            .eq('dataset_id', dataset_id)\
            .execute()

        supabase.table('datasets')\
            .update({'image_count': count_result.count})\
            .eq('id', dataset_id)\
            .execute()

        return {
            "success": True,
            "images_uploaded": len(uploaded_images),
            "images": uploaded_images
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading images: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dataset_id}/upload-zip")
async def upload_zip_to_dataset(
    dataset_id: str,
    file: UploadFile = File(...)
):
    """Upload a ZIP file containing images to a dataset"""
    try:
        # Verify dataset exists
        dataset = supabase.table('datasets').select('id').eq('id', dataset_id).execute()
        if not dataset.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Read ZIP file
        zip_content = await file.read()
        zip_file = zipfile.ZipFile(io.BytesIO(zip_content))

        uploaded_images = []

        # Extract and upload each image
        for filename in zip_file.namelist():
            # Skip directories and hidden files
            if filename.endswith('/') or filename.startswith('.') or '/__MACOSX' in filename:
                continue

            # Check if it's an image
            file_ext = filename.split('.')[-1].lower()
            if file_ext not in ['jpg', 'jpeg', 'png', 'webp']:
                continue

            # Read image from ZIP
            image_data = zip_file.read(filename)

            # Generate unique filename
            storage_filename = f"datasets/{dataset_id}/{uuid.uuid4()}.{file_ext}"

            # Upload to Supabase storage
            supabase.storage.from_('images').upload(
                storage_filename,
                image_data,
                {'content-type': f'image/{file_ext}', 'upsert': 'true'}
            )

            # Get public URL
            image_url = supabase.storage.from_('images').get_public_url(storage_filename)

            # Add to dataset
            result = supabase.table('dataset_images').insert({
                'dataset_id': dataset_id,
                'image_url': image_url,
                'source': 'upload'
            }).execute()

            if result.data:
                uploaded_images.append(result.data[0])

        # Update dataset image count
        count_result = supabase.table('dataset_images')\
            .select('id', count='exact')\
            .eq('dataset_id', dataset_id)\
            .execute()

        supabase.table('datasets')\
            .update({'image_count': count_result.count})\
            .eq('id', dataset_id)\
            .execute()

        return {
            "success": True,
            "images_extracted": len(uploaded_images),
            "images": uploaded_images
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading ZIP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# DOWNLOAD DATASET
# ============================================================

@router.get("/{dataset_id}/download")
async def download_dataset(dataset_id: str):
    """Download dataset as ZIP with images and captions"""
    try:
        import requests

        # Get dataset info
        dataset = supabase.table('datasets')\
            .select('name')\
            .eq('id', dataset_id)\
            .single()\
            .execute()

        if not dataset.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Get all images with captions
        images = supabase.table('dataset_images')\
            .select('image_url, caption')\
            .eq('dataset_id', dataset_id)\
            .execute()

        if not images.data:
            raise HTTPException(status_code=404, detail="No images in dataset")

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, img in enumerate(images.data):
                # Download image
                try:
                    img_response = requests.get(img['image_url'], timeout=30)
                    if img_response.status_code == 200:
                        # Add image to ZIP
                        img_filename = f"image_{idx:04d}.jpg"
                        zip_file.writestr(img_filename, img_response.content)

                        # Add caption if exists
                        if img.get('caption'):
                            caption_filename = f"image_{idx:04d}.txt"
                            zip_file.writestr(caption_filename, img['caption'])
                except:
                    continue

        zip_buffer.seek(0)

        dataset_name = dataset.data['name'].replace(' ', '_')
        filename = f"{dataset_name}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
