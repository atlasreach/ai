#!/usr/bin/env python3
"""
Automated Multi-Model Generation Pipeline

1. Analyzes bikini reference images with Grok Vision API
2. Merges descriptions with model-specific attributes
3. Generates images for each model via ComfyUI
"""

import os
import json
import requests
import psycopg2
import base64
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv()

# Configuration
GROK_API_KEY = os.getenv('GROK_API_KEY')
RUNPOD_HOST = "149.36.1.167"
RUNPOD_PORT = 43613
RUNPOD_SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519")
COMFYUI_URL = "http://127.0.0.1:3001"
REFERENCE_IMAGE_DIR = "/workspace/ComfyUI/input/bikini_pics"

class ModelGenerationPipeline:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv('host'),
            port=int(os.getenv('port')),
            dbname=os.getenv('dbname'),
            user=os.getenv('user'),
            password=os.getenv('password')
        )
        self.cur = self.conn.cursor()

    def analyze_image_with_grok(self, image_path):
        """Use Grok Vision API to describe the bikini reference image"""
        print(f"  Analyzing with Grok Vision API...")

        # Read and encode image
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Call Grok Vision API
        response = requests.post(
            'https://api.x.ai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {GROK_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'grok-vision-beta',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': '''Describe this photo for AI image generation. Focus on:
- Bikini style, color, pattern
- Pose (mirror selfie, holding phone, etc.)
- Setting/background (bathroom, bedroom, etc.)
- Lighting and mood
- Any accessories

Format: Short, comma-separated tags suitable for Stable Diffusion prompt.
DO NOT mention the person's hair color, skin tone, or face - only describe the pose, outfit, and setting.'''
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{image_data}'
                            }
                        }
                    ]
                }],
                'max_tokens': 200,
                'temperature': 0.5
            }
        )

        if response.status_code == 200:
            description = response.json()['choices'][0]['message']['content'].strip()
            print(f"  ✓ Description: {description[:100]}...")
            return description
        else:
            print(f"  ✗ Grok API error: {response.status_code}")
            return None

    def build_prompt(self, model, vision_description):
        """Merge model attributes with vision description"""
        prompt = f"{model['trigger_word']}, {model['hair_style']}, tan skin, beautiful woman, {vision_description}, professional photo, detailed face, 8k, high quality"
        negative = f"{model['negative_prompt']}, blurry, deformed, bad anatomy, low quality, worst quality"
        return prompt, negative

    def generate_via_comfyui(self, model, reference_image, prompt, negative_prompt):
        """Generate image via ComfyUI API on RunPod"""
        print(f"  Generating for {model['name']}...")

        workflow = {
            "1": {
                "inputs": {
                    "image": os.path.basename(reference_image),
                    "upload": "image"
                },
                "class_type": "LoadImage"
            },
            "2": {
                "inputs": {
                    "unet_name": "qwen_image_fp8_e4m3fn.safetensors",
                    "weight_dtype": "fp8_e4m3fn"
                },
                "class_type": "UNETLoader"
            },
            "3": {
                "inputs": {
                    "lora_name": model['lora_file'],
                    "strength_model": float(model['lora_strength']),
                    "model": ["2", 0]
                },
                "class_type": "LoraLoaderModelOnly"
            },
            "4": {
                "inputs": {
                    "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                    "type": "sd3"
                },
                "class_type": "CLIPLoader"
            },
            "5": {
                "inputs": {
                    "vae_name": "qwen_image_vae.safetensors"
                },
                "class_type": "VAELoader"
            },
            "6": {
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "pixels": ["1", 0],
                    "vae": ["5", 0]
                },
                "class_type": "VAEEncode"
            },
            "9": {
                "inputs": {
                    "seed": int(time.time()),
                    "steps": 28,
                    "cfg": 3.8,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 0.65,
                    "model": ["3", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["8", 0]
                },
                "class_type": "KSampler"
            },
            "10": {
                "inputs": {
                    "samples": ["9", 0],
                    "vae": ["5", 0]
                },
                "class_type": "VAEDecode"
            },
            "11": {
                "inputs": {
                    "filename_prefix": f"{model['slug']}_bikini",
                    "images": ["10", 0]
                },
                "class_type": "SaveImage"
            }
        }

        # Submit to ComfyUI via SSH
        import subprocess
        payload = {"prompt": workflow, "client_id": f"auto_{int(time.time())}"}

        # Save payload locally
        temp_file = f"/tmp/workflow_{int(time.time())}.json"
        with open(temp_file, 'w') as f:
            json.dump(payload, f)

        # Upload to RunPod
        subprocess.run([
            "scp", "-o", "StrictHostKeyChecking=no",
            "-P", str(RUNPOD_PORT), "-i", RUNPOD_SSH_KEY,
            temp_file,
            f"root@{RUNPOD_HOST}:/tmp/workflow_payload.json"
        ], check=True, capture_output=True)

        # Submit via curl on RunPod
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-p", str(RUNPOD_PORT), "-i", RUNPOD_SSH_KEY,
            f"root@{RUNPOD_HOST}",
            f"curl -s -X POST {COMFYUI_URL}/prompt -H 'Content-Type: application/json' -d @/tmp/workflow_payload.json"
        ]

        result = subprocess.run(ssh_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                prompt_id = response.get('prompt_id')
                print(f"  ✓ Queued (ID: {prompt_id[:8]}...)")
                return prompt_id
            except:
                print(f"  ✗ Failed to parse response")
                return None
        else:
            print(f"  ✗ SSH command failed")
            return None

    def process_reference_images(self, limit=None):
        """Process all reference images"""
        # Get all models
        self.cur.execute("SELECT * FROM models")
        models = []
        for row in self.cur.fetchall():
            models.append({
                'id': row[0],
                'name': row[1],
                'slug': row[2],
                'skin_tone': row[3],
                'hair_color': row[4],
                'hair_style': row[5],
                'lora_file': row[6],
                'lora_strength': row[7],
                'trigger_word': row[8],
                'negative_prompt': row[9]
            })

        print(f"Found {len(models)} models: {[m['name'] for m in models]}")

        # Get or index reference images
        image_files = sorted(Path(REFERENCE_IMAGE_DIR).glob("*.jpg"))
        if limit:
            image_files = image_files[:limit]

        print(f"\nProcessing {len(image_files)} reference images...")

        for idx, image_path in enumerate(image_files, 1):
            print(f"\n[{idx}/{len(image_files)}] Processing: {image_path.name}")

            # Check if already analyzed
            self.cur.execute(
                "SELECT id, vision_description FROM reference_images WHERE filename = %s",
                (image_path.name,)
            )
            ref_row = self.cur.fetchone()

            if ref_row and ref_row[1]:
                ref_id = ref_row[0]
                vision_description = ref_row[1]
                print(f"  ✓ Already analyzed: {vision_description[:80]}...")
            else:
                # Analyze with Grok
                vision_description = self.analyze_image_with_grok(str(image_path))

                if not vision_description:
                    print(f"  ✗ Skipping - analysis failed")
                    continue

                # Save to database
                if ref_row:
                    self.cur.execute(
                        "UPDATE reference_images SET vision_description = %s, analyzed_at = NOW() WHERE id = %s",
                        (vision_description, ref_row[0])
                    )
                    ref_id = ref_row[0]
                else:
                    self.cur.execute(
                        "INSERT INTO reference_images (filename, file_path, vision_description, analyzed_at) VALUES (%s, %s, %s, NOW()) RETURNING id",
                        (image_path.name, str(image_path), vision_description)
                    )
                    ref_id = self.cur.fetchone()[0]

                self.conn.commit()

            # Generate for each model
            for model in models:
                # Check if already generated
                self.cur.execute(
                    "SELECT id, status FROM generated_images WHERE model_id = %s AND reference_image_id = %s",
                    (model['id'], ref_id)
                )
                gen_row = self.cur.fetchone()

                if gen_row and gen_row[1] == 'completed':
                    print(f"  ✓ {model['name']}: Already generated")
                    continue

                # Build prompt
                prompt, negative = self.build_prompt(model, vision_description)
                print(f"  Prompt: {prompt[:100]}...")

                # Generate
                prompt_id = self.generate_via_comfyui(model, str(image_path), prompt, negative)

                if prompt_id:
                    # Save generation record
                    if gen_row:
                        self.cur.execute(
                            "UPDATE generated_images SET prompt_used = %s, negative_prompt_used = %s, status = 'queued', created_at = NOW() WHERE id = %s",
                            (prompt, negative, gen_row[0])
                        )
                    else:
                        self.cur.execute(
                            """INSERT INTO generated_images
                            (model_id, reference_image_id, prompt_used, negative_prompt_used, status, generation_params)
                            VALUES (%s, %s, %s, %s, 'queued', %s)""",
                            (model['id'], ref_id, prompt, negative, json.dumps({'prompt_id': prompt_id}))
                        )
                    self.conn.commit()

                # Small delay between generations
                time.sleep(0.5)

        print(f"\n✓ Batch processing complete!")
        print(f"   Processed {len(image_files)} images × {len(models)} models = {len(image_files) * len(models)} generations queued")

    def close(self):
        self.cur.close()
        self.conn.close()

if __name__ == "__main__":
    import sys

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    print("=" * 60)
    print("AUTOMATED MULTI-MODEL GENERATION PIPELINE")
    print("=" * 60)

    pipeline = ModelGenerationPipeline()

    try:
        pipeline.process_reference_images(limit=limit)
    finally:
        pipeline.close()
