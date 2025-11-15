"""
Replicate API service for face swap, video generation, etc.
"""
import replicate
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import time

load_dotenv()

REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')

# Initialize Replicate client
if REPLICATE_API_TOKEN:
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

class ReplicateService:
    """Service for calling Replicate API models"""

    @staticmethod
    async def face_swap(
        input_image: str,
        swap_image: str,
        model_version: str = "cdingram/face-swap:d1d6ea8c8be89d664a07a457526f7128109dee7030fdac424788d762c71ed111"
    ) -> Dict[str, Any]:
        """
        Swap face from swap_image into input_image

        Args:
            input_image: URL of target image (where face will be swapped to)
            swap_image: URL of source image (face to swap in)
            model_version: Replicate model version to use

        Returns:
            {
                "success": bool,
                "output_url": str,
                "prediction_id": str,
                "processing_time": float,
                "error": str (optional)
            }
        """
        try:
            print(f"🔄 Starting face swap with {model_version.split(':')[0]}")
            print(f"   Input (target): {input_image[:60]}...")
            print(f"   Swap (source):  {swap_image[:60]}...")

            start_time = time.time()

            # Run prediction
            output = replicate.run(
                model_version,
                input={
                    "input_image": input_image,
                    "swap_image": swap_image
                }
            )

            processing_time = time.time() - start_time

            # Output is the URL string directly
            output_url = str(output) if output else None

            print(f"   ✅ Face swap complete in {processing_time:.1f}s")
            print(f"   Output: {output_url[:60] if output_url else 'None'}...")

            return {
                "success": True,
                "output_url": output_url,
                "processing_time": processing_time,
                "model": model_version.split(':')[0]
            }

        except Exception as e:
            print(f"   ❌ Face swap failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": model_version.split(':')[0]
            }

    @staticmethod
    async def generate_reel(
        start_image_url: str,
        prompt: str,
        negative_prompt: str = "",
        mode: str = "standard",
        duration: int = 5,
        end_image_url: str = None
    ) -> Dict[str, Any]:
        """
        Generate video reel using Kling v2.1

        Args:
            start_image_url: First frame of the video (required for v2.1)
            prompt: Text prompt for video generation
            negative_prompt: Things you do not want to see
            mode: "standard" (720p) or "pro" (1080p)
            duration: Video duration in seconds (default 5)
            end_image_url: Optional last frame

        Returns:
            {
                "success": bool,
                "prediction_id": str,
                "status": str,
                "output_url": str (when complete),
                "error": str (optional)
            }
        """
        try:
            print(f"🎬 Starting reel generation with Kling v2.1")
            print(f"   Mode: {mode}")
            print(f"   Start image: {start_image_url[:60]}...")
            print(f"   Prompt: {prompt[:100]}...")
            print(f"   Duration: {duration}s")

            input_params = {
                "start_image": start_image_url,
                "prompt": prompt,
                "mode": mode,
                "duration": duration
            }

            if negative_prompt:
                input_params["negative_prompt"] = negative_prompt

            if end_image_url:
                input_params["end_image"] = end_image_url

            # Start async prediction (returns immediately)
            prediction = replicate.predictions.create(
                version="kwaivgi/kling-v2.1",
                input=input_params
            )

            print(f"   ✅ Reel generation started (async)")
            print(f"   Prediction ID: {prediction.id}")
            print(f"   Status: {prediction.status}")

            return {
                "success": True,
                "prediction_id": prediction.id,
                "status": prediction.status
            }

        except Exception as e:
            print(f"   ❌ Reel generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def check_prediction_status(prediction_id: str) -> Dict[str, Any]:
        """
        Check status of a long-running prediction

        Args:
            prediction_id: Replicate prediction ID

        Returns:
            {
                "status": str,
                "output_url": str (if succeeded),
                "progress": float (0-100),
                "error": str (if failed)
            }
        """
        try:
            prediction = replicate.predictions.get(prediction_id)

            result = {
                "status": prediction.status,
                "prediction_id": prediction_id
            }

            if prediction.status == "succeeded":
                result["output_url"] = str(prediction.output) if prediction.output else None
            elif prediction.status == "failed":
                result["error"] = str(prediction.error) if prediction.error else "Unknown error"

            # Calculate rough progress
            if prediction.status == "starting":
                result["progress"] = 5
            elif prediction.status == "processing":
                result["progress"] = 50
            elif prediction.status == "succeeded":
                result["progress"] = 100
            elif prediction.status == "failed":
                result["progress"] = 0

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    @staticmethod
    async def remove_background(image_url: str) -> Dict[str, Any]:
        """
        Remove background from image

        Args:
            image_url: URL of input image

        Returns:
            {
                "success": bool,
                "output_url": str,
                "processing_time": float
            }
        """
        try:
            print(f"✂️  Removing background...")
            start_time = time.time()

            output = replicate.run(
                "lucataco/remove-bg:95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1",
                input={"image": image_url}
            )

            processing_time = time.time() - start_time

            return {
                "success": True,
                "output_url": str(output),
                "processing_time": processing_time
            }

        except Exception as e:
            print(f"   ❌ Background removal failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
