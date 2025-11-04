#!/usr/bin/env python3
"""Test Grok caption generation with first 2 Sara images"""

import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from lib.caption_generator import CaptionGenerator

# Load environment
load_dotenv()
GROK_API_KEY = os.getenv('GROK_API_KEY')

if not GROK_API_KEY:
    print("❌ GROK_API_KEY not found in .env")
    sys.exit(1)

# Setup
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / 'models_2.0' / 'sara'

# Get ALL Sara images with NUMERIC sorting
def natural_sort_key(path):
    """Extract number from sara_X for proper sorting"""
    match = re.search(r'sara_(\d+)', path.stem)
    return int(match.group(1)) if match else 0

all_sara_files = list(BASE_DIR.glob('sara_*.png')) + list(BASE_DIR.glob('sara_*.jpg'))
all_sara = sorted(all_sara_files, key=natural_sort_key)
test_images = [str(img) for img in all_sara]

print("=" * 50)
print("Sara Caption Generation - FULL DATASET")
print("=" * 50)
print(f"\nImages to process: {len(test_images)}")
for img in test_images:
    print(f"  - {Path(img).name}")
print(f"\nOutput: {OUTPUT_DIR}")
print()

# Generate captions
generator = CaptionGenerator(GROK_API_KEY)

for i, img_path in enumerate(test_images, 1):
    print(f"\n[{i}/{len(test_images)}] Processing: {Path(img_path).name}")
    print("  → Calling Grok Vision API...")

    caption = generator.generate_caption(img_path, i)

    if caption:
        print(f"  ✓ Caption: {caption}")

        # Save to models_2.0/sara/
        new_img, new_txt = generator.save_renamed(img_path, caption, str(OUTPUT_DIR), i)
        print(f"  ✓ Saved: {Path(new_img).name}, {Path(new_txt).name}")
    else:
        print(f"  ✗ Failed to generate caption")

print("\n" + "=" * 50)
print("Done!")
print("=" * 50)
print(f"\nCheck results in: {OUTPUT_DIR}/")
