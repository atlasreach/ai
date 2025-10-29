#!/usr/bin/env python3
"""Quick Flux Redux test - 3 variations"""

import os
import replicate
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Use first enhanced image
image_path = "models/jade/results/nsfw/source_1/enhanced/jade-s1-t10-nsfw-enhanced.jpg"
caption_path = "models/jade/results/nsfw/source_1/enhanced/jade-s1-t10-nsfw-enhanced.txt"

print("=" * 60)
print("  Quick Flux Redux Test - 3 Variations")
print("=" * 60)

# Read caption
with open(caption_path, 'r') as f:
    prompt = f.read().strip()

print(f"\n✓ Image: {image_path}")
print(f"✓ Caption: {prompt[:100]}...")
print(f"\n💰 Cost: ~$0.12 (3 images × $0.04)")

for i in range(1, 4):
    print(f"\n[{i}/3] Generating variation {i}...")

    try:
        output = replicate.run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": prompt,
                "image_prompt": open(image_path, "rb"),
                "aspect_ratio": "3:2",
                "output_format": "jpg",
                "output_quality": 90,
                "safety_tolerance": 6,
            }
        )

        url = output if isinstance(output, str) else output[0]
        print(f"✓ Generated: {url}")

    except Exception as e:
        print(f"✗ Failed: {e}")

print("\n" + "=" * 60)
print("  Complete!")
print("=" * 60)
