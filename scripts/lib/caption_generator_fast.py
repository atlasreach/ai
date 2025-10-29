"""
Faster caption generation with async batching
"""

import asyncio
import aiohttp
from typing import List, Dict
from pathlib import Path
import base64

class FastCaptionGenerator:
    def __init__(self, grok_api_key: str, batch_size: int = 5):
        self.api_key = grok_api_key
        self.api_url = "https://api.x.ai/v1/chat/completions"
        self.model = "grok-2-vision-1212"
        self.batch_size = batch_size  # Process 5 at once

    async def generate_one(self, session, image_path: str, model_name: str) -> tuple:
        """Generate caption for one image asynchronously"""

        prompt = f"""Generate a concise LoRA training caption for this NSFW image. Format as comma-separated tags, 75-150 words max.

Required structure:
1. Start: "{model_name} woman"
2. Physical: age, ethnicity, skin, hair, face, body
3. Clothing: outfit or "nude"
4. Action: pose, sexual position, activity
5. Setting: location, lighting
6. Details: explicit anatomy (labia, clitoris, penetration), fluids, mood
7. Style: "photorealistic, 8k"

Be explicit but concise. No repetition."""

        # Encode image
        with open(image_path, 'rb') as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            "temperature": 0.7,
            "max_tokens": 500
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                data = await response.json()
                caption = data['choices'][0]['message']['content'].strip()
                return (image_path, caption, None)
        except Exception as e:
            return (image_path, None, str(e))

    async def generate_batch(self, image_paths: List[str], model_name: str) -> Dict[str, str]:
        """Generate captions for multiple images in parallel"""

        results = {}

        async with aiohttp.ClientSession() as session:
            # Process in batches to avoid rate limits
            for i in range(0, len(image_paths), self.batch_size):
                batch = image_paths[i:i + self.batch_size]
                print(f"Processing batch {i//self.batch_size + 1} ({len(batch)} images)...")

                # Run batch concurrently
                tasks = [self.generate_one(session, path, model_name) for path in batch]
                batch_results = await asyncio.gather(*tasks)

                # Collect results
                for path, caption, error in batch_results:
                    if caption:
                        results[path] = caption
                        print(f"  ✓ {Path(path).name}")
                    else:
                        print(f"  ✗ {Path(path).name}: {error}")

                # Rate limiting (Grok allows ~50 req/min)
                if i + self.batch_size < len(image_paths):
                    await asyncio.sleep(3)  # 3 sec between batches

        return results


def generate_captions_fast(image_paths: List[str], model_name: str, grok_api_key: str) -> Dict[str, str]:
    """Convenience function for fast batch caption generation"""
    generator = FastCaptionGenerator(grok_api_key, batch_size=5)
    return asyncio.run(generator.generate_batch(image_paths, model_name))
