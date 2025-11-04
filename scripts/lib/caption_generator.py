"""Caption generation with Grok Vision for LoRA training - Optimized for Sara"""
import os
import base64
import requests
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import re

class CaptionGenerator:
    """Generate concise LoRA captions using Grok Vision API"""
    
    def __init__(self, grok_api_key: str):
        self.api_key = grok_api_key
        self.api_url = "https://api.x.ai/v1/chat/completions"
        self.model = "grok-4"

    def encode_image(self, image_path: str) -> str:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def generate_caption(self, image_path: str, idx: int) -> Optional[str]:
        base64_image = self.encode_image(image_path)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # OPTIMIZED PROMPT: Short, consistent, token-efficient
        prompt = f"""Analyze this image and generate a LoRA training caption.
Rules:
- Start with: Sara
- Use comma-separated tags only
- Max 75 tokens (~150 chars)
- Include: skin, hair, brows, clothing/nude, pose, setting
- End with: sfw or nsfw
- Be explicit only if visible
- No sentences, no fluff, no repetition

Examples:
sara_1.txt → Sara, olive skin, dark ponytail, thick brows, blue tank top, lying in bed, selfie, bedroom, sfw
sara_2.txt → Sara, long dark hair, thick brows, black lace lingerie, pulling bra strap, kneeling, luxury room, nsfw
sara_3.txt → Sara, nude, small breasts, spread legs, using shower head on pussy, open mouth, bathtub, nsfw

Now describe this image:"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.5,
            "max_tokens": 150
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            
            # Clean up
            caption = re.sub(r'\s+', ' ', content)
            caption = re.sub(r'^Sara\s*,?\s*', 'Sara, ', caption)  # enforce trigger
            if not caption.lower().endswith(('sfw', 'nsfw')):
                caption += ', nsfw' if 'nude' in caption.lower() or 'pussy' in caption.lower() else ', sfw'
            return caption
        except Exception as e:
            print(f"Error: {e}")
            return None

    def save_renamed(self, image_path: str, caption: str, output_dir: str, idx: int):
        """Save image and caption as sara_1.png, sara_1.txt etc."""
        os.makedirs(output_dir, exist_ok=True)
        
        new_name = f"sara_{idx}"
        img_ext = Path(image_path).suffix
        new_img_path = Path(output_dir) / f"{new_name}{img_ext}"
        new_txt_path = Path(output_dir) / f"{new_name}.txt"

        # Copy image
        import shutil
        shutil.copy2(image_path, new_img_path)
        
        # Save caption
        with open(new_txt_path, 'w', encoding='utf-8') as f:
            f.write(caption)

        print(f"→ Saved: {new_img_path.name}, {new_txt_path.name}")
        return str(new_img_path), str(new_txt_path)

    def batch_generate(
        self,
        image_paths: List[str],
        output_dir: str,
        s3_manager = None,
        progress_callback = None
    ) -> Dict[str, Tuple[str, str]]:
        """
        Process all images → sara_1.png/txt, sara_2.png/txt...
        Returns: {original_path: (new_img_path, new_txt_path)}
        """
        os.makedirs(output_dir, exist_ok=True)
        results = {}

        for i, img_path in enumerate(sorted(image_paths), 1):
            print(f"\n[{i}/{len(image_paths)}] Processing: {Path(img_path).name}")
            caption = self.generate_caption(img_path, i)
            
            if caption:
                new_img, new_txt = self.save_renamed(img_path, caption, output_dir, i)
                results[img_path] = (new_img, new_txt)

                # Upload to S3 (optional)
                if s3_manager:
                    try:
                        s3_manager.upload_file(new_img, f"lora/sara/{Path(new_img).name}")
                        s3_manager.upload_file(new_txt, f"lora/sara/{Path(new_txt).name}")
                    except Exception as e:
                        print(f"S3 upload failed: {e}")

                if progress_callback:
                    progress_callback(i, len(image_paths), img_path, caption, new_img, new_txt)
            else:
                print("✗ Failed")

        return results


# ——— CLIP OUTFIT GROUPING (Optional) ———
def group_by_outfit(image_paths: List[str], threshold: float = 0.85) -> Dict[str, List[str]]:
    """Group images by visual outfit similarity using CLIP"""
    try:
        import torch
        from PIL import Image
        import clip

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)

        embeddings = []
        for path in image_paths:
            img = preprocess(Image.open(path).convert("RGB")).unsqueeze(0).to(device)
            with torch.no_grad():
                emb = model.encode_image(img).cpu()
            embeddings.append(emb / emb.norm(dim=-1, keepdim=True))

        embeddings = torch.cat(embeddings)
        sim_matrix = embeddings @ embeddings.T

        visited = set()
        groups = {}
        group_id = 0

        for i in range(len(image_paths)):
            if i in visited:
                continue
            group = [image_paths[i]]
            visited.add(i)
            for j in range(i + 1, len(image_paths)):
                if sim_matrix[i][j] > threshold and j not in visited:
                    group.append(image_paths[j])
                    visited.add(j)
            if len(group) > 1 or True:  # keep singles too
                groups[f"outfit_{group_id}"] = group
                group_id += 1

        return groups

    except ImportError:
        print("CLIP not available. Run: pip install torch torchvision clip-interrogator")
        return {f"outfit_0": image_paths}
    except Exception as e:
        print(f"CLIP error: {e}")
        return {}
