"""
Proxy router to forward generation requests to RunPod
This solves CORS issues by routing through same origin
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import os

router = APIRouter()

RUNPOD_API_URL = "https://1314jk61pzkjdb-8001.proxy.runpod.net"

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

class GenerationResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    error: Optional[str] = None
    generation_time: Optional[float] = None

@router.post("/generate", response_model=GenerationResponse)
async def proxy_generate(request: GenerationRequest):
    """
    Forward generation request to RunPod API
    This acts as a proxy to avoid CORS issues
    """
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{RUNPOD_API_URL}/generate",
                json=request.dict()
            )

            if response.status_code == 200:
                return response.json()
            else:
                return GenerationResponse(
                    success=False,
                    error=f"RunPod API error: {response.status_code} - {response.text}"
                )

    except httpx.TimeoutException:
        return GenerationResponse(
            success=False,
            error="Generation timed out after 3 minutes"
        )
    except Exception as e:
        return GenerationResponse(
            success=False,
            error=f"Proxy error: {str(e)}"
        )

@router.get("/health")
async def proxy_health():
    """Check if RunPod API is accessible"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{RUNPOD_API_URL}/health")
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "runpod_status": response.json(),
                    "proxy_url": RUNPOD_API_URL
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"RunPod returned {response.status_code}"
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
