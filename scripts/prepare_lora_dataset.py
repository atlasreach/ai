#!/usr/bin/env python3
"""
Prepare LoRA training dataset from enhanced images + captions
Usage: python scripts/prepare_lora_dataset.py <model_name>
"""

import sys
import shutil
import json
from pathlib import Path


def prepare_dataset(model_name):
    """Prepare LoRA training dataset"""

    print("=" * 60)
    print(f"  Preparing LoRA Dataset: {model_name}")
    print("=" * 60)

    # Paths
    model_dir = Path(f"models/{model_name}")
    results_dir = model_dir / "results"
    output_dir = model_dir / "lora_training"

    if not results_dir.exists():
        print(f"\n✗ No results found for model '{model_name}'")
        print(f"   Run the main workflow first: python master.py")
        return

    # Create output structure
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📂 Output: {output_dir}")

    # Find all enhanced images
    enhanced_images = list(results_dir.glob("**/enhanced/*.jpg"))

    if not enhanced_images:
        print("\n✗ No enhanced images found")
        print("   Make sure you've completed face swap + enhancement")
        return

    print(f"\n✓ Found {len(enhanced_images)} enhanced images")

    # Copy images and captions
    copied = 0
    missing_captions = []

    print("\n📸 Copying training data...")

    for img_path in enhanced_images:
        caption_path = img_path.with_suffix('.txt')

        # Skip if no caption
        if not caption_path.exists():
            missing_captions.append(img_path.name)
            continue

        # Copy image
        dest_img = images_dir / img_path.name
        shutil.copy2(img_path, dest_img)

        # Copy caption
        dest_caption = images_dir / caption_path.name
        shutil.copy2(caption_path, dest_caption)

        copied += 1

    print(f"✓ Copied {copied} image + caption pairs")

    if missing_captions:
        print(f"\n⚠ {len(missing_captions)} images missing captions:")
        for name in missing_captions[:5]:
            print(f"   - {name}")
        if len(missing_captions) > 5:
            print(f"   ... and {len(missing_captions) - 5} more")

    # Verify all images are 1024x1024
    print("\n🔍 Verifying image dimensions...")

    from PIL import Image

    wrong_size = []
    for img_path in images_dir.glob("*.jpg"):
        img = Image.open(img_path)
        if img.size != (1024, 1024):
            wrong_size.append(f"{img_path.name}: {img.size}")

    if wrong_size:
        print(f"⚠ {len(wrong_size)} images not 1024x1024:")
        for info in wrong_size[:5]:
            print(f"   - {info}")
    else:
        print("✓ All images are 1024x1024")

    # Create training config
    print("\n⚙️ Creating training config...")

    config = {
        "model_name": model_name,
        "trigger_word": f"{model_name} woman",
        "num_images": copied,
        "image_size": 1024,
        "recommended_settings": {
            "epochs": 10,
            "batch_size": 1,
            "learning_rate": 1e-4,
            "network_dim": 32,
            "network_alpha": 16
        },
        "base_model": "stabilityai/stable-diffusion-xl-base-1.0",
        "notes": "Dataset prepared automatically from enhanced face-swap images"
    }

    config_path = output_dir / "dataset_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✓ Config saved: {config_path}")

    # Create ZIP for easy upload
    print("\n📦 Creating dataset archive...")

    shutil.make_archive(
        str(output_dir.parent / f"{model_name}_lora_dataset"),
        'zip',
        output_dir
    )

    zip_path = output_dir.parent / f"{model_name}_lora_dataset.zip"
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)

    print(f"✓ Archive created: {zip_path}")
    print(f"   Size: {zip_size_mb:.1f} MB")

    # Summary
    print("\n" + "=" * 60)
    print("  Dataset Ready!")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   Images: {copied}")
    print(f"   Trigger word: \"{model_name} woman\"")
    print(f"   Dataset location: {output_dir}")
    print(f"   Archive: {zip_path}")

    print(f"\n🚀 Next steps:")
    print(f"   1. Upload {zip_path.name} to RunPod")
    print(f"   2. Follow LORA_TRAINING_GUIDE.md")
    print(f"   3. Train for 10 epochs (~1 hour)")
    print(f"   4. Download {model_name}-v1.safetensors")

    print(f"\n💡 Estimated cost: $0.34 (1 hour on RTX 4090)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/prepare_lora_dataset.py <model_name>")
        print("Example: python scripts/prepare_lora_dataset.py jade")
        sys.exit(1)

    model_name = sys.argv[1]
    prepare_dataset(model_name)
