"""
Vision API Router
Analyze images with Grok Vision and generate prompts
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
import base64

router = APIRouter()

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

class ImageAnalysisRequest(BaseModel):
    image_base64: str

class ImageAnalysisResponse(BaseModel):
    success: bool
    positive_prompt: str = ""
    negative_prompt: str = ""
    error: str = ""

@router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(request: ImageAnalysisRequest):
    """
    Analyze uploaded image with Grok Vision
    Generate positive and negative prompts for recreation
    """

    if not GROK_API_KEY:
        return ImageAnalysisResponse(
            success=False,
            error="Grok API key not configured"
        )

    try:
        # Prepare Grok Vision request
        grok_request = {
            "model": "grok-2-vision-1212",
            "messages": [
                {
                    "role": "system",
                    "content": """You are an AI image analysis expert. Analyze images and generate two types of prompts:

1. POSITIVE PROMPT: Detailed description to recreate the image (subject, pose, clothing, background, lighting, style, quality terms)
2. NEGATIVE PROMPT: Things to avoid (artifacts, distortions, unwanted elements)

Format your response EXACTLY like this:
POSITIVE: [your positive prompt here]
NEGATIVE: [your negative prompt here]

Be specific and detailed. Include Milan as the character name if it's a woman."""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{request.image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Analyze this image and generate positive and negative prompts to recreate it."
                        }
                    ]
                }
            ],
            "temperature": 0.7
        }

        # Call Grok Vision API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROK_API_URL,
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=grok_request
            )

            if response.status_code != 200:
                return ImageAnalysisResponse(
                    success=False,
                    error=f"Grok API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Parse positive and negative prompts
            positive_prompt = ""
            negative_prompt = "blurry, low quality, distorted"

            if "POSITIVE:" in content and "NEGATIVE:" in content:
                parts = content.split("NEGATIVE:")
                positive_prompt = parts[0].replace("POSITIVE:", "").strip()
                negative_prompt = parts[1].strip()
            else:
                # Fallback: use entire response as positive prompt
                positive_prompt = content.strip()

            return ImageAnalysisResponse(
                success=True,
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt
            )

    except httpx.TimeoutException:
        return ImageAnalysisResponse(
            success=False,
            error="Grok Vision request timed out"
        )
    except Exception as e:
        return ImageAnalysisResponse(
            success=False,
            error=f"Analysis error: {str(e)}"
        )
