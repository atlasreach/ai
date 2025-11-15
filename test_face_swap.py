"""
Test face-swap endpoint
"""
import requests
import json

API_URL = "http://localhost:8002"

# Test image URL (using one from S3)
TEST_IMAGE = "https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/1.jpg"

print("🧪 Testing face-swap endpoint...")
print(f"   Test image: {TEST_IMAGE}")
print(f"   Character: milan")

response = requests.post(
    f"{API_URL}/face-swap",
    json={
        "input_image_url": TEST_IMAGE,
        "character_id": "milan"
    },
    timeout=120  # Face swap takes ~10-60 seconds
)

result = response.json()

print("\n📊 Response:")
print(json.dumps(result, indent=2))

if result.get("success"):
    print(f"\n✅ SUCCESS!")
    print(f"   Output URL: {result.get('output_url')}")
    print(f"   Content ID: {result.get('content_item_id')}")
    print(f"   Time: {result.get('processing_time'):.1f}s")
else:
    print(f"\n❌ FAILED: {result.get('error')}")
