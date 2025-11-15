"""
ComfyUI API endpoints for programmatic image generation
Integrates with character system and ComfyUI service
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import sys
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import asyncio
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.comfyui_service import ComfyUIService

load_dotenv()

# Database
DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

# Initialize ComfyUI service
comfyui_service = ComfyUIService()

# FastAPI app
app = FastAPI(
    title="ComfyUI API",
    description="Programmatic image generation with ComfyUI",
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

class GenerateRequest(BaseModel):
    character_id: str
    workflow: str = "qwen_single"  # Workflow name shorthand
    input_image_filename: Optional[str] = None  # Image filename in ComfyUI's input directory
    prompt_additions: Optional[str] = ""  # Additional prompt text
    sampler_overrides: Optional[dict] = None  # {"steps": 15, "cfg": 3.5, "denoise": 0.6, ...}
    disable_upscale: bool = False  # Skip upscale for faster generation
    lora_strength: Optional[float] = None  # Override LoRA strength

class GenerateResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None  # Same as prompt_id
    status: str = "queued"  # queued, processing, completed, failed
    error: Optional[str] = None

class StatusResponse(BaseModel):
    success: bool
    job_id: str
    status: str  # processing, completed, failed
    output_url: Optional[str] = None
    output_urls: Optional[list] = None
    progress: Optional[int] = None  # 0-100
    processing_time: Optional[float] = None
    error: Optional[str] = None

class BatchGenerateRequest(BaseModel):
    character_id: str
    workflow: str = "qwen_batch"
    input_images: list[str]  # List of image filenames
    prompt_additions: Optional[str] = ""

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def get_character(character_id: str) -> Optional[Dict[str, Any]]:
    """
    Get character data from database

    Returns:
        {
            "id": str,
            "name": str,
            "trigger_word": str,
            "lora_file": str,
            "lora_strength": float,
            "character_constraints": dict,
            "comfyui_workflow": str
        }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT
                id,
                name,
                trigger_word,
                lora_file,
                lora_strength,
                character_constraints,
                comfyui_workflow,
                description
            FROM characters
            WHERE id = %s
        """, (character_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return dict(row)
        return None

    except Exception as e:
        print(f"Error fetching character: {e}")
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
            data.get('content_type', 'comfyui_generation'),
            data.get('status', 'processing'),
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

def update_content_item(content_id: str, updates: dict):
    """Update content item in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        set_clauses = []
        values = []

        if 'status' in updates:
            set_clauses.append("status = %s")
            values.append(updates['status'])
        if 'video_url' in updates:
            set_clauses.append("video_url = %s")
            values.append(updates['video_url'])
        if 'processing_time_seconds' in updates:
            set_clauses.append("processing_time_seconds = %s")
            values.append(updates['processing_time_seconds'])

        values.append(content_id)

        cursor.execute(f"""
            UPDATE content_items
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """, values)

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        print(f"Error updating content item: {e}")
        return False

# ============================================================================
# WORKFLOW MAPPING
# ============================================================================

WORKFLOW_PATHS = {
    "qwen_single": "workflows/qwen/instagram_single.json",
    "qwen_batch": "workflows/qwen/instagram_batch.json",
    "default": "workflows/qwen/instagram_single.json"
}

def get_workflow_path(workflow_name: str) -> str:
    """Map workflow shorthand to full path"""
    return WORKFLOW_PATHS.get(workflow_name, WORKFLOW_PATHS["default"])

# ============================================================================
# BACKGROUND TASK - Poll and Update Database
# ============================================================================

async def poll_and_save(content_id: str, prompt_id: str, character_id: str):
    """
    Background task to poll ComfyUI and update database when complete
    """
    try:
        print(f"🔄 Started background polling for job {prompt_id[:8]}...")

        # Poll for completion (10 minute timeout)
        result = await comfyui_service.poll_for_completion(prompt_id, timeout=600)

        if result["success"]:
            # Update database with completed status
            update_content_item(content_id, {
                "status": "ready",
                "video_url": result.get("output_url"),
                "processing_time_seconds": result.get("processing_time")
            })
            print(f"✅ Job {prompt_id[:8]}... completed and saved to database")
        else:
            # Mark as failed
            update_content_item(content_id, {"status": "failed"})
            print(f"❌ Job {prompt_id[:8]}... failed: {result.get('error')}")

    except Exception as e:
        print(f"❌ Error in background polling: {e}")
        update_content_item(content_id, {"status": "failed"})

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "ComfyUI API",
        "features": ["image_generation", "character_integration", "workflow_injection"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "comfyui_url": comfyui_service.api_url,
        "database": "connected"
    }

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate image using ComfyUI with character LoRA

    Workflow:
    1. Get character data from database
    2. Load workflow JSON
    3. Inject LoRA, prompts, input image
    4. Submit to ComfyUI
    5. Return job_id immediately
    6. Poll in background and update database when complete
    """
    try:
        print(f"\n🎨 ComfyUI generation request:")
        print(f"   Character: {request.character_id}")
        print(f"   Workflow: {request.workflow}")
        if request.input_image_filename:
            print(f"   Input image: {request.input_image_filename}")
        if request.prompt_additions:
            print(f"   Prompt additions: {request.prompt_additions[:60]}...")

        # 1. Get character data
        character = get_character(request.character_id)
        if not character:
            raise HTTPException(
                status_code=404,
                detail=f"Character not found: {request.character_id}"
            )

        # Use character's workflow if not specified
        workflow_path = get_workflow_path(request.workflow)
        if character.get("comfyui_workflow"):
            workflow_path = character["comfyui_workflow"]

        # 2. Start generation (submit only, don't wait for completion)
        # We'll use manual workflow injection for async submission
        workflow = comfyui_service.load_workflow(workflow_path)

        # Inject parameters
        if lora_file := character.get("lora_file"):
            lora_strength = request.lora_strength if request.lora_strength is not None else character.get("lora_strength", 0.8)
            workflow = comfyui_service.inject_lora(workflow, lora_file, lora_strength)

        positive_prompt = comfyui_service.build_prompt_from_character(
            character,
            request.prompt_additions
        )
        workflow = comfyui_service.inject_prompt(workflow, positive_prompt)

        if request.input_image_filename:
            workflow = comfyui_service.inject_input_image(workflow, request.input_image_filename)

        # Apply overrides
        if request.sampler_overrides:
            workflow = comfyui_service.apply_sampler_overrides(workflow, request.sampler_overrides)

        if request.disable_upscale:
            for node in workflow.get("nodes", []):
                if node.get("type") == "KSampler" and node.get("id") == 79:
                    node["disabled"] = True

        # Submit
        print(f"   📤 Submitting to ComfyUI...")
        submit_result = await comfyui_service.submit_prompt(workflow)

        if not submit_result["success"]:
            return GenerateResponse(
                success=False,
                status="failed",
                error=submit_result.get("error")
            )

        prompt_id = submit_result["prompt_id"]
        print(f"   ✓ Submitted (job_id: {prompt_id[:8]}...)")

        # 3. Save to database with "processing" status
        content_id = save_content_item({
            "character_id": request.character_id,
            "content_type": "comfyui_generation",
            "status": "processing",
            "original_file_url": request.input_image_filename,
            "operations_performed": [{
                "type": "comfyui_generation",
                "workflow": request.workflow,
                "prompt_additions": request.prompt_additions,
                "prompt_id": prompt_id
            }]
        })

        print(f"   ✓ Saved to database (content_id: {content_id})")

        # 4. Start background polling task
        asyncio.create_task(poll_and_save(content_id, prompt_id, request.character_id))

        return GenerateResponse(
            success=True,
            job_id=prompt_id,
            status="processing"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return GenerateResponse(
            success=False,
            status="failed",
            error=str(e)
        )

@app.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """
    Check status of a ComfyUI generation job

    Args:
        job_id: Prompt ID from /generate endpoint

    Returns:
        Status information including output URL when complete
    """
    try:
        print(f"\n📊 Checking status for job {job_id[:8]}...")

        # Get history from ComfyUI
        history = await comfyui_service.get_history(job_id)

        if not history:
            return StatusResponse(
                success=True,
                job_id=job_id,
                status="processing",
                progress=25
            )

        # Check completion status
        status_info = history.get("status", {})

        if status_info.get("completed", False):
            # Get output images
            outputs = history.get("outputs", {})
            output_images = []

            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    output_images.extend(node_output["images"])

            output_urls = [comfyui_service.get_image_url(img) for img in output_images]

            return StatusResponse(
                success=True,
                job_id=job_id,
                status="completed",
                output_url=output_urls[0] if output_urls else None,
                output_urls=output_urls,
                progress=100
            )

        # Check for errors
        if "error" in status_info or status_info.get("status_str") == "error":
            return StatusResponse(
                success=False,
                job_id=job_id,
                status="failed",
                error=status_info.get("error", "Unknown error"),
                progress=0
            )

        # Still processing
        return StatusResponse(
            success=True,
            job_id=job_id,
            status="processing",
            progress=50
        )

    except Exception as e:
        print(f"   ❌ Error checking status: {e}")
        return StatusResponse(
            success=False,
            job_id=job_id,
            status="error",
            error=str(e)
        )

@app.post("/batch-generate", response_model=GenerateResponse)
async def batch_generate(request: BatchGenerateRequest):
    """
    Generate multiple images in batch (future implementation)
    """
    return GenerateResponse(
        success=False,
        status="not_implemented",
        error="Batch generation not yet implemented"
    )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting ComfyUI API...")
    print(f"   Server: http://0.0.0.0:8003")
    print(f"   ComfyUI: {comfyui_service.api_url}")
    uvicorn.run(app, host="0.0.0.0", port=8003)
