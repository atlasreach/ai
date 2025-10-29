#!/usr/bin/env python3
"""Generate captions for all enhanced images using Grok Vision"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from lib import (
    list_all_models,
    load_config,
    S3Manager
)
from lib.caption_generator import CaptionGenerator

# Load environment variables
load_dotenv()


def main():
    print("=" * 60)
    print("  Caption Generation for LoRA Training")
    print("=" * 60)

    # Get Grok API key
    grok_key = os.getenv('GROK_API_KEY')
    if not grok_key:
        print("\n✗ GROK_API_KEY not found in .env")
        print("Add this line to .env:")
        print("GROK_API_KEY=your_api_key_here")
        return

    # List models
    models = list_all_models()
    if not models:
        print("\n✗ No models found")
        return

    print("\nAvailable models:")
    for i, model in enumerate(models, 1):
        print(f"  [{i}] {model}")

    # Select model
    choice = input(f"\nChoose model (1-{len(models)}): ").strip()
    try:
        model_name = models[int(choice) - 1]
    except:
        print("✗ Invalid choice")
        return

    # Find enhanced images
    model_path = Path('models') / model_name
    enhanced_dirs = list(model_path.glob('results/*/source_*/enhanced'))

    all_images = []
    for enhanced_dir in enhanced_dirs:
        all_images.extend(enhanced_dir.glob('*.jpg'))
        all_images.extend(enhanced_dir.glob('*.jpeg'))
        all_images.extend(enhanced_dir.glob('*.png'))

    if not all_images:
        print(f"\n✗ No enhanced images found for '{model_name}'")
        print(f"Run face swap + enhancement first!")
        return

    print(f"\nFound {len(all_images)} enhanced image(s)")

    # Check for existing captions
    existing_captions = [img for img in all_images if img.with_suffix('.txt').exists()]
    if existing_captions:
        print(f"⚠ {len(existing_captions)} already have captions")
        overwrite = input("Overwrite existing captions? (y/n): ").strip().lower()
        if overwrite != 'y':
            all_images = [img for img in all_images if not img.with_suffix('.txt').exists()]
            print(f"Will process {len(all_images)} images without captions")

    if not all_images:
        print("\n✓ All images already have captions!")
        return

    # Initialize S3 (required)
    print("\nInitializing S3...")
    try:
        s3_manager = S3Manager()
        print("✓ S3 Manager initialized")
    except Exception as e:
        print(f"✗ Could not initialize S3: {e}")
        print("S3 upload is required. Check your AWS credentials in .env")
        return

    # Generate captions
    print("\n" + "=" * 60)
    print(f"Generating captions for {len(all_images)} images...")
    print("(Saving locally + uploading to S3)")
    print("=" * 60)

    generator = CaptionGenerator(grok_key)

    results = generator.batch_generate(
        [str(img) for img in all_images],
        model_name=model_name,
        s3_manager=s3_manager
    )

    # Summary
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"✓ Generated: {len(results)}/{len(all_images)} captions")
    print(f"✓ Saved as .txt files next to images")
    print(f"✓ Uploaded to S3 bucket: {s3_manager.bucket_name}")
    print("\nReady for LoRA training!")


if __name__ == "__main__":
    main()
