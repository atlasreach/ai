#!/usr/bin/env python3
"""
Quick test script for Flux Redux variations
Usage: python test_flux_redux.py
"""

import os
import replicate
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configuration
MODEL_NAME = "jade"
SOURCE_ID = 1
TARGET_ID = 1
CONTENT_TYPE = "nsfw"

def find_enhanced_image():
    """Find an enhanced image to use"""
    enhanced_dir = Path(f"models/{MODEL_NAME}/results/{CONTENT_TYPE}/source_{SOURCE_ID}/enhanced")

    if not enhanced_dir.exists():
        print(f"✗ No enhanced images found at: {enhanced_dir}")
        return None

    images = list(enhanced_dir.glob("*.jpg"))
    if not images:
        print(f"✗ No .jpg files found in: {enhanced_dir}")
        return None

    return str(images[0])

def upload_to_replicate(image_path):
    """Upload image and get URL for Flux Redux"""
    print(f"\n📤 Uploading image: {image_path}")

    # Replicate handles the upload
    with open(image_path, "rb") as file:
        # Return the path - Replicate will upload it
        return image_path

def generate_variations(image_path, num_variations=6):
    """Generate variations using Flux Redux"""

    print(f"\n🎨 Generating {num_variations} variations...")
    print("=" * 60)

    # Load existing Grok caption
    caption_path = Path(image_path).with_suffix('.txt')

    if caption_path.exists():
        with open(caption_path, 'r') as f:
            base_prompt = f.read().strip()
        print(f"\n✓ Using Grok caption: {base_prompt[:100]}...")
    else:
        # Fallback if no caption exists
        base_prompt = f"{MODEL_NAME} woman, beautiful, high quality photography"
        print(f"\n⚠ No caption found, using basic prompt")

    results = []

    for i in range(1, num_variations + 1):
        print(f"\n[{i}/{num_variations}] Generating variation {i}...")

        try:
            output = replicate.run(
                "black-forest-labs/flux-1.1-pro",
                input={
                    "prompt": base_prompt,  # Use Grok's detailed caption
                    "image_prompt": open(image_path, "rb"),  # Your enhanced image
                    "aspect_ratio": "3:2",
                    "output_format": "jpg",
                    "output_quality": 90,
                    "safety_tolerance": 6,  # Max tolerance for NSFW
                    "seed": None  # Random seed = natural variations
                }
            )

            # Output is a single URL (or list of URLs if num_outputs > 1)
            image_url = output if isinstance(output, str) else output[0]
            results.append({
                'variation': i,
                'prompt': base_prompt,
                'url': image_url
            })

            print(f"✓ Generated: {image_url[:80]}...")

        except Exception as e:
            print(f"✗ Failed: {e}")
            continue

    return results

def download_variations(results):
    """Download generated variations"""
    import requests

    output_dir = Path(f"models/{MODEL_NAME}/variations")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📥 Downloading variations to: {output_dir}")

    for result in results:
        try:
            filename = f"{MODEL_NAME}-flux-var-{result['variation']:03d}.jpg"
            filepath = output_dir / filename

            response = requests.get(result['url'], stream=True)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"✓ Downloaded: {filename}")

            # Save prompt as txt file
            txt_path = filepath.with_suffix('.txt')
            with open(txt_path, 'w') as f:
                f.write(result['prompt'])

        except Exception as e:
            print(f"✗ Failed to download variation {result['variation']}: {e}")

def main():
    print("=" * 60)
    print("  Flux Redux Variation Generator - Quick Test")
    print("=" * 60)

    # Check for API token
    if not os.getenv('REPLICATE_API_TOKEN'):
        print("\n✗ REPLICATE_API_TOKEN not found in .env")
        print("\n📝 To get your token:")
        print("   1. Go to: https://replicate.com/account/api-tokens")
        print("   2. Copy your token")
        print("   3. Add to .env: REPLICATE_API_TOKEN=r8_...")
        return

    # Find enhanced image
    image_path = find_enhanced_image()
    if not image_path:
        print("\n💡 First run the main workflow to create enhanced images:")
        print("   python master.py")
        return

    print(f"✓ Found image: {image_path}")

    # Ask for confirmation
    print(f"\n💰 Cost estimate: ~$0.24 (6 images × $0.04)")
    confirm = input("\nGenerate 6 variations? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Cancelled.")
        return

    # Generate variations
    results = generate_variations(image_path, num_variations=6)

    if not results:
        print("\n✗ No variations generated")
        return

    print(f"\n✓ Generated {len(results)} variations!")

    # Download results
    download = input("\nDownload variations locally? (y/n): ").strip().lower()
    if download == 'y':
        download_variations(results)

    print("\n" + "=" * 60)
    print("  Complete!")
    print("=" * 60)
    print(f"\nGenerated {len(results)} variations")
    print(f"View results at: models/{MODEL_NAME}/variations/")

if __name__ == "__main__":
    main()
