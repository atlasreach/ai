#!/usr/bin/env python3
"""Test Grok Vision API with local image"""

import os
import base64
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Grok API settings
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

def encode_image_to_base64(image_path):
    """Encode image file to base64 string"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def generate_caption_with_grok(image_path, prompt="Describe this image in detail for AI training. Focus on the person, clothing, pose, and setting. Use comma-separated tags."):
    """Generate caption for image using Grok Vision API"""

    print(f"\n📷 Processing: {image_path}")

    # Check if file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Encode image
    print("  • Encoding image to base64...")
    base64_image = encode_image_to_base64(image_path)
    print(f"  ✓ Encoded ({len(base64_image)} chars)")

    # Prepare request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROK_API_KEY}"
    }

    payload = {
        "model": "grok-2-vision-1212",
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

    # Send request
    print("  • Sending to Grok Vision API...")
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()

        # Extract caption
        if 'choices' in data and len(data['choices']) > 0:
            caption = data['choices'][0]['message']['content']
            print("  ✓ Caption received!\n")
            return caption
        else:
            print("  ✗ Unexpected response format")
            print(json.dumps(data, indent=2))
            return None

    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP Error: {e}")
        print(f"  Response: {response.text}")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None

def main():
    """Test Grok Vision with a sample image"""

    print("=" * 60)
    print("  Grok Vision API Test")
    print("=" * 60)

    # Test with andie enhanced image
    test_images = [
        "models/andie/results/nsfw/source_1/enhanced/andie-s1-t1-nsfw-enhanced.jpg",
        "models/andie/results/nsfw/source_1/enhanced/andie_nsfw_001_enhanced.jpg",
        "andie_nsfw_005_enhanced.jpg"
    ]

    # Find first available image
    image_path = None
    for test_path in test_images:
        if os.path.exists(test_path):
            image_path = test_path
            break

    if not image_path:
        print("\n⚠ No test images found. Please provide an image path:")
        image_path = input("Image path: ").strip()

        if not os.path.exists(image_path):
            print(f"✗ File not found: {image_path}")
            return

    # Generate caption
    caption = generate_caption_with_grok(image_path)

    if caption:
        print("=" * 60)
        print("📝 GENERATED CAPTION:")
        print("=" * 60)
        print(caption)
        print("=" * 60)
        print("\n✓ Success!")
    else:
        print("\n✗ Failed to generate caption")

if __name__ == "__main__":
    main()
