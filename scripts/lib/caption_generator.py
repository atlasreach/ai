"""Caption generation with Grok Vision for LoRA training"""

import os
import base64
import requests
import json
from pathlib import Path
from typing import Optional, Dict, List


class CaptionGenerator:
    """Generate captions for images using Grok Vision API"""

    def __init__(self, grok_api_key: str):
        self.api_key = grok_api_key
        self.api_url = "https://api.x.ai/v1/chat/completions"
        self.model = "grok-4"  # Best model for detailed captions

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def generate_caption(
        self,
        image_path: str,
        model_name: str,
        custom_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate caption for image

        Args:
            image_path: Path to image file
            model_name: Model name (e.g., "anna", "andie")
            custom_prompt: Optional custom prompt override

        Returns:
            Caption string or None if failed
        """

        # Default prompt with model name - optimized for shorter, better captions
        if custom_prompt is None:
            custom_prompt = f"""Generate a concise LoRA training caption for this image. Format as comma-separated tags, 75-150 words max.ust 

Required structure:
1. Start: "{model_name} woman"
2. Physical: age, skin tone, hair (length, color, style), face features, body type, breast size
3. Clothing: describe outfit or state "nude" or "completely nude"
4. Action/Pose: what is she doing? (e.g., sitting, standing, kneeling, lying down, masturbating, sexual position like missionary/doggy/cowgirl/oral)
5. Setting: location (bedroom, bathroom, outdoor, etc.), lighting (soft, golden hour, overhead, etc.)
6. Explicit details (NSFW only): visible anatomy (erect nipples, labia, clitoris, vaginal opening, anus), penetration details, fluids, arousal state
7. Style: end with "photorealistic, 8k resolution, high detail"

Be explicit and anatomically precise for NSFW content. Don't repeat basic info - focus on what makes THIS image unique. Keep it concise but descriptive."""

        base64_image = self.encode_image(image_path)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": custom_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.7,
            "max_tokens": 600
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            data = response.json()

            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']

            return None

        except Exception as e:
            print(f"Error generating caption: {e}")
            return None

    def save_caption(self, image_path: str, caption: str, s3_manager):
        """
        Save caption as .txt file next to image and upload to S3

        Args:
            image_path: Path to image
            caption: Caption text
            s3_manager: S3Manager instance (required)
        """
        # Save locally (required for LoRA training)
        txt_path = Path(image_path).with_suffix('.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(caption)

        # Always upload to S3 for backup/reference
        try:
            # Remove 'models/{model_name}/' prefix for S3 key
            # e.g., 'models/sar/results/nsfw/...' → 'results/nsfw/...'
            txt_path_str = str(txt_path).replace('\\', '/')
            parts = txt_path_str.split('/')
            if 'models' in parts and 'results' in parts:
                results_idx = parts.index('results')
                s3_key = '/'.join(parts[results_idx:])
            else:
                # Fallback: just remove 'models/' prefix
                s3_key = txt_path_str.replace('models/', '')

            s3_url = s3_manager.upload_file(str(txt_path), s3_key, 'text/plain')
            return s3_url
        except Exception as e:
            print(f"  ⚠ Warning: Could not upload caption to S3: {e}")
            import traceback
            traceback.print_exc()
            return None

    def batch_generate(
        self,
        image_paths: List[str],
        model_name: str,
        s3_manager,
        progress_callback = None
    ) -> Dict[str, str]:
        """
        Generate captions for multiple images

        Args:
            image_paths: List of image paths
            model_name: Model name
            s3_manager: S3Manager instance (required - always uploads to S3)
            progress_callback: Optional callback(current, total, image_path, caption)

        Returns:
            Dict mapping image_path -> caption
        """
        results = {}

        for i, image_path in enumerate(image_paths, 1):
            print(f"\n[{i}/{len(image_paths)}] Processing: {Path(image_path).name}")

            caption = self.generate_caption(image_path, model_name)

            if caption:
                results[image_path] = caption
                print(f"✓ Caption generated ({len(caption)} chars)")

                # Always save locally + upload to S3
                self.save_caption(image_path, caption, s3_manager)
                print(f"✓ Saved locally + uploaded to S3")

                if progress_callback:
                    progress_callback(i, len(image_paths), image_path, caption)
            else:
                print(f"✗ Failed to generate caption")

        return results


def find_similar_outfits(image_paths: List[str], similarity_threshold: float = 0.85):
    """
    Group images by clothing similarity using CLIP

    NOTE: Requires CLIP installed: pip install clip-interrogator

    Args:
        image_paths: List of image paths
        similarity_threshold: Similarity score threshold (0-1)

    Returns:
        Dict of outfit groups: {outfit_id: [image_paths]}
    """
    try:
        import torch
        from PIL import Image
        import clip

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)

        # Get image embeddings
        embeddings = []
        for img_path in image_paths:
            image = preprocess(Image.open(img_path)).unsqueeze(0).to(device)
            with torch.no_grad():
                embedding = model.encode_image(image)
                embeddings.append(embedding)

        # Compute similarity matrix and cluster
        # TODO: Implement clustering algorithm
        # For now, return placeholder
        return {"outfit_1": image_paths}

    except ImportError:
        print("⚠ CLIP not installed. Install with: pip install clip-interrogator")
        return {}
