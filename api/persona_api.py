"""
Persona System API
Handles models, personas, reference libraries for the multi-persona content factory
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

router = APIRouter(prefix="/api/persona", tags=["persona-system"])

# ============================================================
# PYDANTIC MODELS
# ============================================================

class ModelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instagram_username: Optional[str] = None
    tiktok_username: Optional[str] = None
    onlyfans_username: Optional[str] = None

class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    training_status: Optional[str] = None  # 'not_started', 'training', 'complete'
    lora_url: Optional[str] = None
    lora_trigger_word: Optional[str] = None
    training_notes: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instagram_username: Optional[str] = None
    tiktok_username: Optional[str] = None
    onlyfans_username: Optional[str] = None

class Model(BaseModel):
    id: str
    name: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    training_status: str
    lora_url: Optional[str]
    lora_trigger_word: Optional[str]
    training_notes: Optional[str]
    instagram_username: Optional[str]
    tiktok_username: Optional[str]
    onlyfans_username: Optional[str]
    created_at: datetime
    updated_at: datetime

class ModelWithStats(Model):
    """Model with aggregated stats from personas"""
    persona_count: int = 0
    total_generated: int = 0
    total_posted: int = 0

# ============================================================
# MODEL CRUD ENDPOINTS
# ============================================================

@router.post("/models", response_model=Model)
async def create_model(model: ModelCreate):
    """Create a new model"""
    try:
        result = supabase.table('models').insert({
            'name': model.name,
            'description': model.description,
            'instagram_username': model.instagram_username,
            'tiktok_username': model.tiktok_username,
            'onlyfans_username': model.onlyfans_username,
            'training_status': 'not_started'
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create model")

        return result.data[0]

    except Exception as e:
        print(f"Error creating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=List[ModelWithStats])
async def list_models():
    """Get all models with stats"""
    try:
        # Get all models
        models_result = supabase.table('models')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()

        if not models_result.data:
            return []

        # For each model, get persona stats
        models_with_stats = []
        for model in models_result.data:
            # Get persona count and aggregated stats
            personas_result = supabase.table('personas')\
                .select('total_generated, total_posted')\
                .eq('model_id', model['id'])\
                .execute()

            persona_count = len(personas_result.data) if personas_result.data else 0
            total_generated = sum(p['total_generated'] or 0 for p in personas_result.data) if personas_result.data else 0
            total_posted = sum(p['total_posted'] or 0 for p in personas_result.data) if personas_result.data else 0

            models_with_stats.append({
                **model,
                'persona_count': persona_count,
                'total_generated': total_generated,
                'total_posted': total_posted
            })

        return models_with_stats

    except Exception as e:
        print(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}", response_model=ModelWithStats)
async def get_model(model_id: str):
    """Get a single model with stats"""
    try:
        # Get model
        model_result = supabase.table('models')\
            .select('*')\
            .eq('id', model_id)\
            .execute()

        if not model_result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        model = model_result.data[0]

        # Get persona stats
        personas_result = supabase.table('personas')\
            .select('total_generated, total_posted')\
            .eq('model_id', model_id)\
            .execute()

        persona_count = len(personas_result.data) if personas_result.data else 0
        total_generated = sum(p['total_generated'] or 0 for p in personas_result.data) if personas_result.data else 0
        total_posted = sum(p['total_posted'] or 0 for p in personas_result.data) if personas_result.data else 0

        return {
            **model,
            'persona_count': persona_count,
            'total_generated': total_generated,
            'total_posted': total_posted
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/models/{model_id}", response_model=Model)
async def update_model(model_id: str, update: ModelUpdate):
    """Update a model"""
    try:
        # Build update data (only include fields that were provided)
        update_data = {k: v for k, v in update.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_data['updated_at'] = datetime.utcnow().isoformat()

        result = supabase.table('models')\
            .update(update_data)\
            .eq('id', model_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    """Delete a model (cascades to personas and generated content)"""
    try:
        result = supabase.table('models')\
            .delete()\
            .eq('id', model_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        return {"success": True, "message": "Model deleted"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# MODEL PERSONAS ENDPOINT
# ============================================================

@router.get("/models/{model_id}/personas")
async def get_model_personas(model_id: str):
    """Get all personas for a model"""
    try:
        result = supabase.table('personas')\
            .select('*')\
            .eq('model_id', model_id)\
            .order('created_at', desc=True)\
            .execute()

        return result.data or []

    except Exception as e:
        print(f"Error getting model personas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# IMAGE UPLOAD ENDPOINTS
# ============================================================

@router.post("/models/{model_id}/thumbnail")
async def upload_model_thumbnail(model_id: str, file: UploadFile = File(...)):
    """Upload thumbnail for a model"""
    try:
        # Check model exists
        model_result = supabase.table('models').select('id').eq('id', model_id).execute()
        if not model_result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        # Upload to Supabase storage
        file_content = await file.read()
        filename = f"models/{model_id}/thumbnail.jpg"

        supabase.storage.from_('images').upload(
            filename,
            file_content,
            {'content-type': file.content_type, 'upsert': 'true'}
        )

        # Get public URL
        thumbnail_url = supabase.storage.from_('images').get_public_url(filename)

        # Update model
        supabase.table('models')\
            .update({'thumbnail_url': thumbnail_url})\
            .eq('id', model_id)\
            .execute()

        return {"success": True, "thumbnail_url": thumbnail_url}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading thumbnail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
