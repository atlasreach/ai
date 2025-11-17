#!/usr/bin/env python3
"""
Test the complete workflow via API
"""
import requests
import json
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

API_BASE = "http://localhost:8002"
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("  TESTING COMPLETE WORKFLOW")
print("=" * 60)

# Step 1: Create a model
print("\n📝 Step 1: Creating test model...")
model_data = {
    "name": "TestModel",
    "trigger_word": "testmodel",
    "defining_features": {},
    "is_active": True
}

result = supabase.table('models').insert(model_data).execute()
if result.data:
    model = result.data[0]
    model_id = model['id']
    print(f"  ✅ Model created: {model['name']} (ID: {model_id})")
else:
    print("  ❌ Failed to create model")
    exit(1)

# Step 2: Create a dataset
print("\n📂 Step 2: Creating test dataset...")
dataset_data = {
    "model_id": model_id,
    "name": "testmodel_v1",
    "dataset_type": "SFW",
    "description": "Test dataset",
    "image_count": 0,
    "training_status": "preparing"
}

result = supabase.table('datasets').insert(dataset_data).execute()
if result.data:
    dataset = result.data[0]
    dataset_id = dataset['id']
    print(f"  ✅ Dataset created: {dataset['name']} (ID: {dataset_id})")
else:
    print("  ❌ Failed to create dataset")
    exit(1)

# Step 3: Add test images
print("\n🖼️  Step 3: Adding test images...")
test_images = [
    {"image_url": "https://picsum.photos/512/512?random=1", "display_order": 0},
    # Only 1 image to save Grok API costs during testing
]

for img in test_images:
    img_data = {
        "dataset_id": dataset_id,
        "image_url": img["image_url"],
        "caption": "",
        "display_order": img["display_order"]
    }
    result = supabase.table('dataset_images').insert(img_data).execute()
    if result.data:
        print(f"  ✅ Image {img['display_order'] + 1} added")
    else:
        print(f"  ❌ Failed to add image {img['display_order'] + 1}")

# Update image count
supabase.table('datasets').update({"image_count": len(test_images)}).eq('id', dataset_id).execute()

# Step 4: Test caption generation API
print("\n✨ Step 4: Testing caption generation API...")
print(f"  Calling: POST /api/datasets/{dataset_id}/generate-all-captions")

try:
    response = requests.post(f"{API_BASE}/api/datasets/{dataset_id}/generate-all-captions")
    print(f"  Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ Success!")
        print(f"     Updated: {data.get('updated_count', 0)}/{data.get('total_images', 0)} images")
        if data.get('errors'):
            print(f"     Errors: {len(data['errors'])}")
            for error in data['errors']:
                print(f"       - {error}")
    else:
        print(f"  ❌ Failed!")
        print(f"  Response: {response.text}")
except Exception as e:
    print(f"  ❌ Exception: {e}")

# Step 5: Verify captions were saved
print("\n🔍 Step 5: Verifying captions in database...")
result = supabase.table('dataset_images').select('*').eq('dataset_id', dataset_id).execute()

if result.data:
    print(f"  Found {len(result.data)} images:")
    for img in result.data:
        caption = img.get('caption', '')
        if caption:
            print(f"  ✅ Image {img['display_order'] + 1}: {caption[:60]}...")
        else:
            print(f"  ❌ Image {img['display_order'] + 1}: No caption")
else:
    print("  ❌ No images found")

# Step 6: List all models and datasets
print("\n📊 Step 6: Current database state...")
models = supabase.table('models').select('*').execute()
print(f"  Models: {len(models.data) if models.data else 0}")

datasets = supabase.table('datasets').select('*').execute()
print(f"  Datasets: {len(datasets.data) if datasets.data else 0}")

images = supabase.table('dataset_images').select('*').execute()
print(f"  Images: {len(images.data) if images.data else 0}")

print("\n" + "=" * 60)
print("  TEST COMPLETE")
print("=" * 60)
print(f"\n💡 Test model ID: {model_id}")
print(f"💡 Test dataset ID: {dataset_id}")
print("\nYou can view these in the UI at http://localhost:5173")
