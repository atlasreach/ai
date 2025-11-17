"""
Persona System API
Handles models, personas, reference libraries for the multi-persona content factory
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import uuid
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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    description: Optional[str] = None
    instagram_username: Optional[str] = None
    tiktok_username: Optional[str] = None
    onlyfans_username: Optional[str] = None

class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instagram_username: Optional[str] = None
    tiktok_username: Optional[str] = None
    onlyfans_username: Optional[str] = None

class Model(BaseModel):
    id: str
    name: str
    first_name: Optional[str]
    last_name: Optional[str]
    description: Optional[str]
    thumbnail_url: Optional[str]
    instagram_username: Optional[str]
    tiktok_username: Optional[str]
    onlyfans_username: Optional[str]
    instagram_account_id: Optional[str]
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
async def create_model(model: ModelCreate, background_tasks: BackgroundTasks):
    """Create a new model"""
    try:
        result = supabase.table('models').insert({
            'name': model.name,
            'first_name': model.first_name,
            'last_name': model.last_name,
            'description': model.description,
            'instagram_username': model.instagram_username,
            'tiktok_username': model.tiktok_username,
            'onlyfans_username': model.onlyfans_username
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create model")

        model_data = result.data[0]
        model_id = model_data['id']

        # If Instagram username provided, automatically start scraping
        if model.instagram_username:
            print(f"🔄 Auto-scraping Instagram for @{model.instagram_username} (model: {model_id})")
            # Import scraper function
            from api.instagram_scraper_instaloader import scrape_instagram_account

            # Define background task to scrape and auto-link
            def scrape_and_link():
                try:
                    account_id, posts_scraped = scrape_instagram_account(model.instagram_username, num_posts=0)
                    print(f"✅ Auto-scrape complete: {posts_scraped} posts")

                    # Auto-link the Instagram account to the model
                    supabase.table('models').update({
                        'instagram_account_id': account_id
                    }).eq('id', model_id).execute()

                    # Also link back from Instagram account to model
                    supabase.table('instagram_accounts').update({
                        'model_id': model_id
                    }).eq('id', account_id).execute()

                    print(f"✅ Auto-linked @{model.instagram_username} to model {model_id}")
                except Exception as e:
                    print(f"❌ Auto-scrape failed for @{model.instagram_username}: {e}")

            background_tasks.add_task(scrape_and_link)

        return model_data

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


@router.post("/models/{model_id}/upload-thumbnail")
async def upload_model_thumbnail(model_id: str, file: UploadFile = File(...)):
    """Upload profile picture for a model"""
    try:
        # Read file content
        file_content = await file.read()

        # Create filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        storage_path = f"models/{model_id}/thumbnail.{file_ext}"

        # Upload to Supabase storage
        supabase.storage.from_('images').upload(
            storage_path,
            file_content,
            {'content-type': file.content_type, 'upsert': 'true'}
        )

        # Get public URL
        thumbnail_url = supabase.storage.from_('images').get_public_url(storage_path)

        # Update model with thumbnail URL
        result = supabase.table('models')\
            .update({'thumbnail_url': thumbnail_url})\
            .eq('id', model_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        return {"success": True, "thumbnail_url": thumbnail_url}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading thumbnail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LinkInstagramRequest(BaseModel):
    instagram_account_id: str

@router.post("/models/{model_id}/link-instagram")
async def link_instagram_account(model_id: str, request: LinkInstagramRequest):
    """Link an Instagram account to a model"""
    try:
        print(f"🔗 Linking Instagram account {request.instagram_account_id} to model {model_id}")

        # Get Instagram account details
        instagram_account = supabase.table('instagram_accounts')\
            .select('username')\
            .eq('id', request.instagram_account_id)\
            .execute()

        if not instagram_account.data:
            print(f"❌ Instagram account {request.instagram_account_id} not found")
            raise HTTPException(status_code=404, detail="Instagram account not found")

        username = instagram_account.data[0]['username']
        print(f"📋 Found Instagram account: @{username}")

        # Update the model with the Instagram account ID and username
        result = supabase.table('models')\
            .update({
                'instagram_account_id': request.instagram_account_id,
                'instagram_username': username
            })\
            .eq('id', model_id)\
            .execute()

        if not result.data:
            print(f"❌ Model {model_id} not found")
            raise HTTPException(status_code=404, detail="Model not found")

        print(f"✅ Updated model {model_id} with instagram_account_id: {request.instagram_account_id}")

        # Also link back from the Instagram account to the model
        supabase.table('instagram_accounts')\
            .update({'model_id': model_id})\
            .eq('id', request.instagram_account_id)\
            .execute()

        print(f"✅ Linked Instagram account @{username} to model {model_id}")
        return {"success": True, "message": "Instagram account linked to model"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error linking Instagram account: {e}")
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


@router.get("/models/{model_id}/instagram-posts")
async def get_model_instagram_posts(model_id: str):
    """Get Instagram posts for a model"""
    try:
        print(f"🔍 Getting Instagram posts for model {model_id}")

        # Get the model's Instagram account ID
        model_result = supabase.table('models')\
            .select('instagram_account_id, instagram_username')\
            .eq('id', model_id)\
            .single()\
            .execute()

        print(f"📋 Model result: {model_result.data}")

        if not model_result.data or not model_result.data.get('instagram_account_id'):
            print(f"⚠️  Model has no instagram_account_id linked")
            return {"success": False, "posts": [], "message": "No Instagram account linked to this model"}

        instagram_account_id = model_result.data['instagram_account_id']
        print(f"🔗 Looking for posts with account_id: {instagram_account_id}")

        # Get posts for that Instagram account (use account_id not instagram_account_id)
        posts_result = supabase.table('instagram_posts')\
            .select('*')\
            .eq('account_id', instagram_account_id)\
            .order('created_at', desc=True)\
            .execute()

        print(f"📸 Found {len(posts_result.data or [])} posts")

        return {"success": True, "posts": posts_result.data or []}

    except Exception as e:
        print(f"❌ Error getting Instagram posts: {e}")
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


# ============================================================
# PERSONA CRUD ENDPOINTS
# ============================================================

class PersonaCreate(BaseModel):
    name: str
    description: Optional[str] = None
    niche: Optional[str] = None
    reference_library_id: Optional[str] = None
    target_face_name: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_bio: Optional[str] = None
    tiktok_username: Optional[str] = None
    onlyfans_username: Optional[str] = None
    default_prompt_prefix: Optional[str] = None
    default_negative_prompt: Optional[str] = None
    default_strength: float = 0.75

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    niche: Optional[str] = None
    reference_library_id: Optional[str] = None
    target_face_name: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_bio: Optional[str] = None
    instagram_connected: Optional[bool] = None
    tiktok_username: Optional[str] = None
    onlyfans_username: Optional[str] = None
    default_prompt_prefix: Optional[str] = None
    default_negative_prompt: Optional[str] = None
    default_strength: Optional[float] = None

class Persona(BaseModel):
    id: str
    name: str
    description: Optional[str]
    niche: Optional[str]
    thumbnail_url: Optional[str]
    model_id: str
    reference_library_id: Optional[str]
    target_face_url: str
    target_face_thumbnail: Optional[str]
    target_face_name: Optional[str]
    instagram_username: Optional[str]
    instagram_bio: Optional[str]
    instagram_connected: bool
    tiktok_username: Optional[str]
    onlyfans_username: Optional[str]
    default_prompt_prefix: Optional[str]
    default_negative_prompt: Optional[str]
    default_strength: float
    total_generated: int
    total_posted: int
    created_at: datetime
    updated_at: datetime


@router.post("/personas", response_model=Persona)
async def create_persona(
    model_id: str,
    name: str,
    target_face: UploadFile = File(...),
    description: Optional[str] = None,
    niche: Optional[str] = None,
    reference_library_id: Optional[str] = None,
    target_face_name: Optional[str] = None,
    instagram_username: Optional[str] = None,
    instagram_bio: Optional[str] = None,
    tiktok_username: Optional[str] = None,
    onlyfans_username: Optional[str] = None,
    default_prompt_prefix: Optional[str] = None,
    default_negative_prompt: Optional[str] = None,
    default_strength: float = 0.75
):
    """Create a new persona with target face upload"""
    try:
        # Verify model exists
        model_result = supabase.table('models').select('id').eq('id', model_id).execute()
        if not model_result.data:
            raise HTTPException(status_code=404, detail="Model not found")

        # Upload target face to Supabase storage
        file_content = await target_face.read()
        persona_temp_id = str(uuid.uuid4())
        filename = f"personas/{persona_temp_id}/target_face.jpg"

        supabase.storage.from_('images').upload(
            filename,
            file_content,
            {'content-type': target_face.content_type, 'upsert': 'true'}
        )

        # Get public URL
        target_face_url = supabase.storage.from_('images').get_public_url(filename)

        # Create persona in database
        result = supabase.table('personas').insert({
            'model_id': model_id,
            'name': name,
            'description': description,
            'niche': niche,
            'reference_library_id': reference_library_id,
            'target_face_url': target_face_url,
            'target_face_thumbnail': target_face_url,
            'target_face_name': target_face_name,
            'instagram_username': instagram_username,
            'instagram_bio': instagram_bio,
            'instagram_connected': False,
            'tiktok_username': tiktok_username,
            'onlyfans_username': onlyfans_username,
            'default_prompt_prefix': default_prompt_prefix,
            'default_negative_prompt': default_negative_prompt,
            'default_strength': default_strength,
            'total_generated': 0,
            'total_posted': 0
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create persona")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/personas/{persona_id}", response_model=Persona)
async def get_persona(persona_id: str):
    """Get a single persona"""
    try:
        result = supabase.table('personas')\
            .select('*')\
            .eq('id', persona_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Persona not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/personas/{persona_id}", response_model=Persona)
async def update_persona(persona_id: str, update: PersonaUpdate):
    """Update a persona"""
    try:
        # Build update data
        update_data = {k: v for k, v in update.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_data['updated_at'] = datetime.utcnow().isoformat()

        result = supabase.table('personas')\
            .update(update_data)\
            .eq('id', persona_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Persona not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/personas/{persona_id}")
async def delete_persona(persona_id: str):
    """Delete a persona"""
    try:
        result = supabase.table('personas')\
            .delete()\
            .eq('id', persona_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Persona not found")

        return {"success": True, "message": "Persona deleted"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# REFERENCE LIBRARY ENDPOINTS
# ============================================================

class ReferenceLibraryCreate(BaseModel):
    name: str
    niche: str
    description: Optional[str] = None

class ReferenceLibrary(BaseModel):
    id: str
    name: str
    niche: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    image_count: int
    created_at: datetime
    updated_at: datetime


@router.get("/reference-libraries")
async def list_reference_libraries(niche: Optional[str] = None):
    """List all reference libraries, optionally filtered by niche"""
    try:
        query = supabase.table('reference_libraries').select('*')

        if niche:
            query = query.eq('niche', niche)

        result = query.order('created_at', desc=True).execute()

        return result.data or []

    except Exception as e:
        print(f"Error listing reference libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reference-libraries", response_model=ReferenceLibrary)
async def create_reference_library(library: ReferenceLibraryCreate):
    """Create a new reference library"""
    try:
        result = supabase.table('reference_libraries').insert({
            'name': library.name,
            'niche': library.niche,
            'description': library.description,
            'image_count': 0
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create reference library")

        return result.data[0]

    except Exception as e:
        print(f"Error creating reference library: {e}")
        raise HTTPException(status_code=500, detail=str(e))
