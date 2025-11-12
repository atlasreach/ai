"""
Grok AI Service
Handles prompt enhancement and image analysis using Grok API
"""

import os
import httpx
from typing import Optional


class GroqService:
    """Service for interacting with Grok AI API"""

    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise ValueError("GROK_API_KEY not found in environment variables")

        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-beta"

    async def enhance_prompt(
        self,
        user_prompt: str,
        character_name: str,
        style: str = "instagram influencer"
    ) -> str:
        """
        Enhance a user's basic prompt into a detailed, optimized prompt

        Args:
            user_prompt: User's basic prompt (e.g., "tennis player")
            character_name: Character trigger word (e.g., "Milan")
            style: Desired style (default: "instagram influencer")

        Returns:
            Enhanced detailed prompt
        """
        system_prompt = f"""You are an expert prompt engineer for AI image generation.
Your task is to expand simple prompts into detailed, vivid descriptions optimized for Qwen image models.

Guidelines:
1. Always include the character name "{character_name}" at the start
2. Describe physical appearance, clothing, pose, and setting in detail
3. Add photography style (e.g., "2024 photo", "professional photography")
4. Keep it natural and realistic for {style} style
5. Avoid overly artistic or abstract descriptions
6. Output ONLY the enhanced prompt, no explanations

Example:
Input: "tennis player"
Output: "{character_name}, woman, 25 years old, athletic build, wearing white tennis dress, swinging tennis racket, mid-action shot on outdoor tennis court, professional sports photography, natural sunlight, high detail"
"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 200
                    }
                )

                if response.status_code != 200:
                    print(f"Grok API error: {response.status_code} - {response.text}")
                    # Fallback to basic enhancement
                    return f"{character_name}, {user_prompt}, professional photography, high detail"

                result = response.json()
                enhanced = result["choices"][0]["message"]["content"].strip()

                # Ensure character name is at the start
                if not enhanced.startswith(character_name):
                    enhanced = f"{character_name}, {enhanced}"

                return enhanced

        except Exception as e:
            print(f"Error calling Grok API: {e}")
            # Fallback: return basic enhanced prompt
            return f"{character_name}, {user_prompt}, professional photography, high detail"

    async def suggest_negative_prompt(self, positive_prompt: str) -> str:
        """
        Generate appropriate negative prompts based on the positive prompt

        Args:
            positive_prompt: The main generation prompt

        Returns:
            Suggested negative prompt
        """
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Generate negative prompts for AI image generation. List unwanted elements concisely, comma-separated. Focus on common issues like: blurry, distorted, low quality, bad anatomy, deformed, etc."
                            },
                            {
                                "role": "user",
                                "content": f"Negative prompt for: {positive_prompt}"
                            }
                        ],
                        "temperature": 0.5,
                        "max_tokens": 100
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"Error generating negative prompt: {e}")

        # Default negative prompt
        return "blurry, low quality, distorted, bad anatomy, deformed, ugly, bad proportions, extra limbs, duplicate, watermark, text"

    async def analyze_reference_image(self, image_description: str) -> dict:
        """
        Analyze a reference image and suggest generation parameters
        (Placeholder for future vision API integration)

        Args:
            image_description: Description of the reference image

        Returns:
            Dictionary with suggested parameters
        """
        # TODO: Integrate Grok vision API when available
        # For now, return default recommendations
        return {
            "suggested_cfg": 4.0,
            "suggested_steps": 30,
            "suggested_denoise": 0.85,
            "notes": "Default parameters recommended"
        }
