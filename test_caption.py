#!/usr/bin/env python3
"""
Simple Test Captioning with Grok Vision API
Tests captioning on 2-3 images only.
"""

import os
import sys
import json
import base64
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

# Configuration
MODEL = "grok-2-vision-1212"
TEST_IMAGE_COUNT = 3  # Test with 3 images

def encode_image_base64(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_caption_prompt() -> str:
    """Generate the captioning prompt for Grok."""
    return """You are an expert at creating training captions for AI image models (LoRA training).

Analyze this image and create a detailed training caption following this EXACT format:

Milan, [skin tone], [hair color and style], [facial features], [clothing description], [pose/action], [expression], [camera angle], [background/location], [lighting], sfw

IMPORTANT GUIDELINES:
1. Start with "Milan" as the trigger word
2. Be specific about pose (standing, sitting, lying, walking, etc.)
3. Note camera angle (front view, side view, back view, 3/4 view, close-up, full body)
4. Describe bikini details (color, style - two-piece, one-piece, triangle top, etc.)
5. Mention lighting quality (natural light, studio lighting, golden hour, soft light, etc.)
6. Describe background (beach, pool, studio, outdoor, tropical, etc.)
7. Note expression (smiling, serious, playful, confident, etc.)
8. Keep it concise but detailed (one line)
9. End with "sfw" for bikini images

Return your response as plain text - just the caption."""

def caption_image_with_grok(image_path: str, image_name: str) -> str:
    """Send single image to Grok for captioning."""
    try:
        print(f"📸 Processing: {image_name}")

        # Encode image
        image_base64 = encode_image_base64(image_path)

        # Prepare API request
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": get_caption_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }

        # Make API call
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        # Parse response
        result = response.json()
        caption = result['choices'][0]['message']['content'].strip()

        print(f"✅ Caption: {caption[:100]}...")
        return caption

    except Exception as e:
        print(f"❌ Error processing {image_name}: {str(e)}")
        return ""

def main():
    """Main function."""
    print("🎨 Simple Milan Caption Test")
    print("="*50)

    # Setup paths (adjust if needed)
    bikini_dir = Path(".")  # Current directory for simplicity
    output_dir = bikini_dir

    # Get images (jpg files in current dir)
    all_images = sorted([f for f in bikini_dir.glob("*.jpg")])

    if not all_images:
        print("❌ No .jpg images found in current directory!")
        return

    # Test with first 3 images
    images = all_images[:TEST_IMAGE_COUNT]
    print(f"🧪 Testing with {len(images)} images\n")

    # Process each image
    for img_path in images:
        caption = caption_image_with_grok(str(img_path), img_path.name)

        if caption:
            # Save caption as .txt file
            txt_file = img_path.with_suffix('.txt')
            with open(txt_file, 'w') as f:
                f.write(caption)
            print(f"💾 Saved: {txt_file}\n")

    print("✅ Test complete!")

if __name__ == "__main__":
    if not GROK_API_KEY:
        print("❌ Error: API key not set")
        sys.exit(1)

    main()