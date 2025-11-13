#!/usr/bin/env python3
"""
Test script for inpainting endpoint
Creates a simple mask and tests the inpaint API
"""
import base64
import json
import requests
from PIL import Image, ImageDraw
import io

# Configuration
API_URL = "http://localhost:8001"
TEST_IMAGE_PATH = "/workspaces/ai/outputs/milan/20251113_111311/output.png"

print("🧪 Testing Inpaint Endpoint")
print("=" * 50)

# 1. Load test image
print(f"\n1️⃣  Loading test image: {TEST_IMAGE_PATH}")
with open(TEST_IMAGE_PATH, "rb") as f:
    image_data = f.read()
    image_base64 = base64.b64encode(image_data).decode()
print(f"   ✅ Image loaded ({len(image_base64)} chars)")

# 2. Create a simple test mask (mask the center area)
print("\n2️⃣  Creating test mask...")
img = Image.open(TEST_IMAGE_PATH)
width, height = img.size
print(f"   Image size: {width}x{height}")

# Create mask (white = inpaint this area, black = keep)
mask = Image.new('L', (width, height), 0)  # Black background
draw = ImageDraw.Draw(mask)

# Draw white rectangle in center (this will be inpainted)
mask_width = width // 3
mask_height = height // 3
x1 = (width - mask_width) // 2
y1 = (height - mask_height) // 2
x2 = x1 + mask_width
y2 = y1 + mask_height

draw.rectangle([x1, y1, x2, y2], fill=255)  # White rectangle
print(f"   Mask area: {x1},{y1} to {x2},{y2}")

# Convert mask to base64
mask_buffer = io.BytesIO()
mask.save(mask_buffer, format='PNG')
mask_base64 = base64.b64encode(mask_buffer.getvalue()).decode()
print(f"   ✅ Mask created ({len(mask_base64)} chars)")

# Save mask for inspection
mask.save("/tmp/test_mask.png")
print(f"   💾 Mask saved to /tmp/test_mask.png")

# 3. Prepare inpaint request
print("\n3️⃣  Preparing inpaint request...")
payload = {
    "image_base64": image_base64,
    "mask_base64": mask_base64,
    "prompt": "elegant red evening gown with sparkles",
    "negative_prompt": "blurry, low quality, distorted",
    "character": "milan",
    "num_inference_steps": 25,
    "guidance_scale": 4.0,
    "seed": 42,
    "use_grok_enhancement": False
}
print(f"   ✅ Payload ready")
print(f"   Prompt: {payload['prompt']}")

# 4. Send request
print("\n4️⃣  Sending inpaint request...")
print("   (This may take 60-90 seconds...)")

try:
    response = requests.post(
        f"{API_URL}/inpaint",
        json=payload,
        timeout=300
    )

    print(f"\n5️⃣  Response received (Status: {response.status_code})")

    if response.status_code == 200:
        result = response.json()

        if result.get("success"):
            print("   ✅ SUCCESS!")
            print(f"   Generation time: {result.get('generation_time', 0):.1f}s")

            # Save result image
            if result.get("image_base64"):
                output_data = base64.b64decode(result["image_base64"])
                output_path = "/tmp/inpaint_result.png"
                with open(output_path, "wb") as f:
                    f.write(output_data)
                print(f"   💾 Result saved to: {output_path}")

            if result.get("s3_output_url"):
                print(f"   ☁️  S3 URL: {result['s3_output_url']}")

            print("\n" + "=" * 50)
            print("✅ INPAINTING WORKS!")
            print("=" * 50)
        else:
            print(f"   ❌ FAILED: {result.get('error')}")
    else:
        print(f"   ❌ HTTP Error: {response.status_code}")
        print(f"   {response.text[:500]}")

except requests.Timeout:
    print("   ⏱️  Request timed out (generation may still be running)")
except Exception as e:
    print(f"   ❌ Error: {e}")
