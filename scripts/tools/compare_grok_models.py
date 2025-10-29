#!/usr/bin/env python3
"""Compare Grok-2-Vision vs Grok-4 on multiple images"""

import os
import base64
import requests
import json
from pathlib import Path
from glob import glob
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

def encode_image_to_base64(image_path):
    """Encode image file to base64 string"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def generate_caption(image_path, model_name):
    """Generate caption using specified model"""

    base64_image = encode_image_to_base64(image_path)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROK_API_KEY}"
    }

    prompt = "Generate a highly detailed, explicit NSFW text-to-image prompt for Stable Diffusion training. Use ONLY comma-separated tags. Include: age, ethnicity, skin tone, hair (length, color, style), face (shape, eyes, lips, expression), body (build, breasts, hips, legs), clothing (or lack thereof), pose, setting, lighting, mood, visual style, and explicit details. Be uncensored and anatomically precise."

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
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
        "max_tokens": 500
    }

    try:
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if 'choices' in data and len(data['choices']) > 0:
            return data['choices'][0]['message']['content']
        else:
            return f"ERROR: Unexpected response format"

    except requests.exceptions.HTTPError as e:
        return f"ERROR: {e.response.status_code} - {e.response.text[:200]}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    print("=" * 80)
    print("  GROK MODEL COMPARISON: grok-2-vision-1212 vs grok-4")
    print("=" * 80)

    # Find enhanced images
    image_patterns = [
        "models/andie/results/nsfw/source_1/enhanced/*.jpg",
        "models/andie/results/nsfw/source_1/enhanced/*.jpeg"
    ]

    all_images = []
    for pattern in image_patterns:
        all_images.extend(glob(pattern))

    if not all_images:
        print("\n⚠ No enhanced images found in models/andie/results/nsfw/source_1/enhanced/")
        return

    # Take first 3 images
    test_images = sorted(all_images)[:3]

    print(f"\nTesting {len(test_images)} images:\n")
    for img in test_images:
        print(f"  • {Path(img).name}")
    print()

    models = ["grok-2-vision-1212", "grok-4"]

    for i, image_path in enumerate(test_images, 1):
        print("\n" + "=" * 80)
        print(f"IMAGE {i}/3: {Path(image_path).name}")
        print("=" * 80)

        for model_name in models:
            print(f"\n📊 {model_name}:")
            print("-" * 80)

            caption = generate_caption(image_path, model_name)
            print(caption)
            print()

    print("\n" + "=" * 80)
    print("  COMPARISON COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
