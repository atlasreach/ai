#!/usr/bin/env python3
"""Resize existing enhanced images to 1024x1024"""

from pathlib import Path
from scripts.lib.image_utils import resize_image

model_name = "jade"
results_dir = Path(f"models/{model_name}/results")

print("=" * 60)
print(f"  Resizing Enhanced Images: {model_name}")
print("=" * 60)

# Find all enhanced images
enhanced_images = list(results_dir.glob("**/enhanced/*.jpg"))

print(f"\n✓ Found {len(enhanced_images)} enhanced images")
print("\n🔄 Resizing to 1024x1024...\n")

resized = 0
for img_path in enhanced_images:
    print(f"  Processing: {img_path.name}...")

    # Resize in place (overwrites original)
    resize_image(str(img_path), str(img_path), target_size=1024)
    resized += 1

print(f"\n✓ Resized {resized} images to 1024x1024")
print("✓ All captions (.txt files) unchanged")
print("\n" + "=" * 60)
print("  Complete! Ready for LoRA training")
print("=" * 60)
