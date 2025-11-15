"""
Grok AI service for generating prompts with vision
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

class GrokService:
    """Service for Grok AI prompt generation with vision"""

    @staticmethod
    def generate_video_prompts(image_url: str = None, image_description: str = None) -> dict:
        """
        Generate positive and negative prompts for video generation using vision

        Args:
            image_url: URL of the image to analyze
            image_description: Optional description of the image

        Returns:
            {
                "positive_prompt": str,
                "negative_prompt": str
            }
        """
        try:
            system_prompt = """You are an expert at creating video generation prompts.
Analyze the image and generate a positive prompt and negative prompt for a short 5-second video.
The prompts should describe natural, subtle movements that fit the scene - nothing exaggerated.
Keep movements elegant and professional.

Respond ONLY with JSON in this format:
{
  "positive_prompt": "your positive prompt here",
  "negative_prompt": "your negative prompt here"
}"""

            # Build message content with image
            user_content = []

            if image_url:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })

            text_prompt = "Analyze this image and generate video prompts for natural movement."
            if image_description:
                text_prompt = f"Analyze this image: {image_description}. Generate video prompts for natural movement."

            user_content.append({
                "type": "text",
                "text": text_prompt
            })

            response = requests.post(
                GROK_API_URL,
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-2-vision-1212",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Grok API error: {response.text}")

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse JSON from response
            import json
            prompts = json.loads(content)

            return {
                "positive_prompt": prompts.get("positive_prompt", ""),
                "negative_prompt": prompts.get("negative_prompt", "")
            }

        except Exception as e:
            print(f"Error generating prompts with Grok: {e}")
            # Return defaults if Grok fails
            return {
                "positive_prompt": "strike a confident pose, gently sway hips while keeping it natural and chic",
                "negative_prompt": "unrealistic, too much motion, distorted"
            }

    @staticmethod
    async def generate_caption_from_url(image_url: str, custom_prompt: str) -> str:
        """
        Generate a training caption for an image using Grok vision

        Args:
            image_url: URL of the image to caption
            custom_prompt: Custom prompt with character constraints and formatting rules

        Returns:
            Generated caption string
        """
        try:
            # Build message content with image
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                },
                {
                    "type": "text",
                    "text": custom_prompt
                }
            ]

            response = requests.post(
                GROK_API_URL,
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-2-vision-1212",
                    "messages": [
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 300
                },
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Grok API error: {response.text}")

            result = response.json()
            caption = result['choices'][0]['message']['content'].strip()

            return caption

        except Exception as e:
            print(f"Error generating caption with Grok: {e}")
            raise
