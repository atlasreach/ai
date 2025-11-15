"""
Content Studio API - Brand New Backend
Handles: Face swap, video generation, background operations, scheduling
"""
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv
import boto3
from datetime import datetime
import uuid
import psycopg2
import psycopg2.extras
from services.replicate_service import ReplicateService

load_dotenv()

# AWS S3 Setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-2')
)
S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'ai-character-generations')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')

# Supabase Database
DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

# Initialize Replicate service
replicate_service = ReplicateService()

# FastAPI app
app = FastAPI(
    title="Content Studio API",
    description="Face swap, video generation, and content management",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class FaceSwapRequest(BaseModel):
    input_image_url: str
    character_id: str  # 'milan', 'skyler', etc.

class FaceSwapResponse(BaseModel):
    success: bool
    output_url: Optional[str] = None
    content_item_id: Optional[str] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None

class VideoGenerationRequest(BaseModel):
    image_url: str
    prompt: Optional[str] = ""
    duration: int = 5

class VideoGenerationResponse(BaseModel):
    success: bool
    prediction_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None

class CheckStatusRequest(BaseModel):
    prediction_id: str

class UploadResponse(BaseModel):
    success: bool
    url: Optional[str] = None
    s3_key: Optional[str] = None
    error: Optional[str] = None

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def get_character_featured_image(character_id: str) -> Optional[str]:
    """Get a featured training image for a character"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT image_url FROM model_gallery
            WHERE character_id = %s AND is_featured = true
            ORDER BY display_order
            LIMIT 1
        """, (character_id,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching character image: {e}")
        return None

def save_content_item(data: dict) -> str:
    """Save content item to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO content_items (
                character_id, content_type, status,
                original_file_url, face_swapped_url, video_url,
                caption, operations_performed, processing_time_seconds
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('character_id'),
            data.get('content_type', 'image'),
            data.get('status', 'ready'),
            data.get('original_file_url'),
            data.get('face_swapped_url'),
            data.get('video_url'),
            data.get('caption'),
            psycopg2.extras.Json(data.get('operations_performed', [])),
            data.get('processing_time_seconds')
        ))

        content_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        return str(content_id)
    except Exception as e:
        print(f"Error saving content item: {e}")
        raise

# ============================================================================
# S3 UPLOAD HELPER
# ============================================================================

def upload_to_s3(file_content: bytes, filename: str, content_type: str = "image/jpeg") -> dict:
    """Upload file to S3 and return URL"""
    try:
        # Generate unique S3 key
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"studio-uploads/{timestamp}_{filename}"

        # Upload
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            CacheControl='max-age=31536000'
        )

        # Generate URL
        url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

        print(f"✅ Uploaded to S3: {s3_key}")

        return {
            "success": True,
            "url": url,
            "s3_key": s3_key
        }
    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Content Studio API",
        "features": ["face_swap", "video_generation", "background_operations"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected",
        "replicate": "configured"
    }

@app.get("/characters")
async def list_characters():
    """Get all available character models"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.id,
                c.name,
                c.lora_file,
                c.description,
                c.thumbnail_url,
                COUNT(mg.id) as training_image_count
            FROM characters c
            LEFT JOIN model_gallery mg ON c.id = mg.character_id
            GROUP BY c.id, c.name, c.lora_file, c.description, c.thumbnail_url
            ORDER BY c.name
        """)

        characters = []
        for row in cursor.fetchall():
            characters.append({
                "id": row[0],
                "name": row[1],
                "lora_file": row[2],
                "description": row[3],
                "thumbnail_url": row[4],
                "training_image_count": row[5]
            })

        cursor.close()
        conn.close()

        return {
            "success": True,
            "characters": characters
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/characters/{character_id}/gallery")
async def get_character_gallery(character_id: str, featured_only: bool = False):
    """Get training images for a character"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, image_url, caption, is_featured, display_order
            FROM model_gallery
            WHERE character_id = %s
        """

        if featured_only:
            query += " AND is_featured = true"

        query += " ORDER BY display_order"

        cursor.execute(query, (character_id,))

        images = []
        for row in cursor.fetchall():
            images.append({
                "id": str(row[0]),
                "image_url": row[1],
                "caption": row[2],
                "is_featured": row[3],
                "display_order": row[4]
            })

        cursor.close()
        conn.close()

        return {
            "success": True,
            "character_id": character_id,
            "images": images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload image/video to S3"""
    try:
        # Read file
        content = await file.read()

        # Determine content type
        content_type = file.content_type or "image/jpeg"

        # Upload to S3
        result = upload_to_s3(content, file.filename, content_type)

        if result["success"]:
            return UploadResponse(
                success=True,
                url=result["url"],
                s3_key=result["s3_key"]
            )
        else:
            return UploadResponse(
                success=False,
                error=result["error"]
            )
    except Exception as e:
        return UploadResponse(
            success=False,
            error=str(e)
        )

@app.post("/face-swap", response_model=FaceSwapResponse)
async def face_swap(request: FaceSwapRequest):
    """
    Swap face from character into input image

    Uses cdingram/face-swap on Replicate
    """
    try:
        print(f"\n🔄 Face swap request:")
        print(f"   Input image: {request.input_image_url[:60]}...")
        print(f"   Character: {request.character_id}")

        # Get character's featured training image (this is the face to swap in)
        swap_image_url = get_character_featured_image(request.character_id)

        if not swap_image_url:
            raise HTTPException(
                status_code=404,
                detail=f"No training images found for character: {request.character_id}"
            )

        print(f"   Using character face: {swap_image_url[:60]}...")

        # Call Replicate face-swap
        result = await replicate_service.face_swap(
            input_image=request.input_image_url,
            swap_image=swap_image_url
        )

        if not result["success"]:
            return FaceSwapResponse(
                success=False,
                error=result.get("error")
            )

        # Save to database
        content_id = save_content_item({
            "character_id": request.character_id,
            "content_type": "image",
            "status": "ready",
            "original_file_url": request.input_image_url,
            "face_swapped_url": result["output_url"],
            "operations_performed": ["face_swap"],
            "processing_time_seconds": result["processing_time"]
        })

        print(f"   ✅ Saved to database: {content_id}")

        return FaceSwapResponse(
            success=True,
            output_url=result["output_url"],
            content_item_id=content_id,
            processing_time=result["processing_time"]
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return FaceSwapResponse(
            success=False,
            error=str(e)
        )

@app.post("/generate-video", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """Generate video from image using Kling AI (takes 5-10 minutes)"""
    try:
        result = await replicate_service.generate_video(
            image_url=request.image_url,
            prompt=request.prompt,
            duration=request.duration
        )

        if not result["success"]:
            return VideoGenerationResponse(
                success=False,
                error=result.get("error")
            )

        return VideoGenerationResponse(
            success=True,
            prediction_id=result["prediction_id"],
            status=result["status"]
        )

    except Exception as e:
        return VideoGenerationResponse(
            success=False,
            error=str(e)
        )

@app.post("/check-status")
async def check_status(request: CheckStatusRequest):
    """Check status of long-running prediction (video generation, etc.)"""
    try:
        result = await replicate_service.check_prediction_status(request.prediction_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/library")
async def get_library(
    character_id: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get content library with optional filters"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                id, character_id, content_type, status,
                original_file_url, face_swapped_url, video_url,
                caption, created_at
            FROM content_items
            WHERE 1=1
        """
        params = []

        if character_id:
            query += " AND character_id = %s"
            params.append(character_id)

        if content_type:
            query += " AND content_type = %s"
            params.append(content_type)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)

        items = []
        for row in cursor.fetchall():
            items.append({
                "id": str(row[0]),
                "character_id": row[1],
                "content_type": row[2],
                "status": row[3],
                "original_file_url": row[4],
                "face_swapped_url": row[5],
                "video_url": row[6],
                "caption": row[7],
                "created_at": row[8].isoformat() if row[8] else None
            })

        cursor.close()
        conn.close()

        return {
            "success": True,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Content Studio API...")
    print(f"   Server: http://0.0.0.0:8002")
    print(f"   Features: Face Swap, Video Generation, Library")
    uvicorn.run(app, host="0.0.0.0", port=8002)
