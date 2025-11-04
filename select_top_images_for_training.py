#!/usr/bin/env python3
"""
Select Top Images for Milan LoRA Training
Picks best images from each category based on quality scores.
"""

import json
import shutil
from pathlib import Path

# Configuration
BIKINI_COUNT = 18    # 18 bikini/sfw images
NUDE_COUNT = 18      # 18 nude images
EXPLICIT_COUNT = 18  # 18 explicit images
TOTAL_TARGET = 54    # Total: 54 images (good size for training)

# Paths
BASE_DIR = Path("/workspaces/ai/models_2.0/milan")
OUTPUT_DIR = BASE_DIR / "training_dataset"

def load_rankings(category):
    """Load ranking JSON for a category."""
    ranking_file = BASE_DIR / f"{category}_ranking.json"
    with open(ranking_file) as f:
        return json.load(f)

def select_top_images():
    """Select top images from each category."""
    print("🎯 Milan LoRA Training Dataset Selection")
    print("=" * 80)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    selected = []

    # Process each category
    categories = {
        'bikini': BIKINI_COUNT,
        'nude': NUDE_COUNT,
        'explicit': EXPLICIT_COUNT
    }

    for category, count in categories.items():
        print(f"\n📂 {category.upper()} Category:")
        print(f"   Selecting top {count} images...")

        # Load rankings
        rankings = load_rankings(category)

        # Get top N images
        top_images = rankings[:count]

        # Copy images and captions
        copied = 0
        for i, item in enumerate(top_images, 1):
            image_path = Path(item['path'])
            caption_path = image_path.with_suffix('.txt')

            # New naming: milan_selected_N.jpg
            new_num = len(selected) + 1
            new_image = OUTPUT_DIR / f"milan_selected_{new_num}.jpg"
            new_caption = OUTPUT_DIR / f"milan_selected_{new_num}.txt"

            # Copy files
            if image_path.exists() and caption_path.exists():
                shutil.copy2(image_path, new_image)
                shutil.copy2(caption_path, new_caption)

                selected.append({
                    'number': new_num,
                    'category': category,
                    'original': image_path.name,
                    'score': item['score'],
                    'caption': item['caption'][:80] + "..." if len(item['caption']) > 80 else item['caption']
                })
                copied += 1

        print(f"   ✓ Copied {copied}/{count} images")

    # Print summary
    print("\n" + "=" * 80)
    print("📊 TRAINING DATASET SUMMARY")
    print("=" * 80)

    print(f"\n✅ Total images selected: {len(selected)}/{TOTAL_TARGET}")

    # Category breakdown
    bikini_imgs = [s for s in selected if s['category'] == 'bikini']
    nude_imgs = [s for s in selected if s['category'] == 'nude']
    explicit_imgs = [s for s in selected if s['category'] == 'explicit']

    print(f"\n📦 Category Breakdown:")
    print(f"   • Bikini/SFW:  {len(bikini_imgs)} images ({len(bikini_imgs)/len(selected)*100:.0f}%)")
    print(f"   • Nude:        {len(nude_imgs)} images ({len(nude_imgs)/len(selected)*100:.0f}%)")
    print(f"   • Explicit:    {len(explicit_imgs)} images ({len(explicit_imgs)/len(selected)*100:.0f}%)")

    # Score stats
    scores = [s['score'] for s in selected]
    print(f"\n📈 Quality Scores:")
    print(f"   • Average: {sum(scores)/len(scores):.1f}")
    print(f"   • Highest: {max(scores)}")
    print(f"   • Lowest:  {min(scores)}")
    print(f"   • 90+: {len([s for s in scores if s >= 90])} images")
    print(f"   • 85+: {len([s for s in scores if s >= 85])} images")

    # Show top 10
    print(f"\n🏆 TOP 10 IMAGES SELECTED:")
    print(f"{'#':<4} {'Score':<7} {'Category':<10} {'Original':<30} {'Caption Preview'}")
    print("-" * 120)
    for item in sorted(selected, key=lambda x: x['score'], reverse=True)[:10]:
        print(f"{item['number']:<4} {item['score']}/100  {item['category']:<10} {item['original']:<30} {item['caption'][:50]}")

    print("\n" + "=" * 80)
    print("✅ DATASET READY FOR TRAINING!")
    print("=" * 80)
    print(f"\n📁 Location: {OUTPUT_DIR}")
    print(f"📁 Files: {len(selected)} images + {len(selected)} captions")

    print(f"\n💾 Next step: Upload to RunPod")
    print(f"   1. Zip the dataset:")
    print(f"      cd {BASE_DIR}")
    print(f"      zip -r milan_training_dataset.zip training_dataset/")
    print(f"   ")
    print(f"   2. Upload to RunPod:")
    print(f"      scp milan_training_dataset.zip runpod:/workspace/")
    print(f"   ")
    print(f"   3. Extract on RunPod:")
    print(f"      unzip milan_training_dataset.zip")
    print(f"      mv training_dataset lora_training/10_milan")
    print(f"   ")
    print(f"   4. Run training script:")
    print(f"      bash runpod_train_milan.sh")
    print()

if __name__ == "__main__":
    select_top_images()
