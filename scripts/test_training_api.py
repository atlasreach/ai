#!/usr/bin/env python3
"""
Test the training API with an existing dataset
"""
import os
import sys
import requests
sys.path.insert(0, '/workspaces/ai')
os.chdir('/workspaces/ai')

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

print("🧪 Testing Training API")
print("=" * 50)

# Find datasets with images
datasets = supabase.table('training_datasets').select('*').execute()

print("\n📊 Existing datasets:")
for ds in datasets.data:
    img_count = ds.get('image_count', 0)
    status = ds.get('training_status', 'not_started')
    print(f"\n  📦 {ds['name']}")
    print(f"     ID: {ds['id']}")
    print(f"     Images: {img_count}")
    print(f"     Type: {ds['dataset_type']}")
    print(f"     Status: {status}")

# Pick first one with images
datasets_with_images = [d for d in datasets.data if d.get('image_count', 0) > 0]

if not datasets_with_images:
    print("\n❌ No datasets with images found!")
    exit(1)

test_dataset = datasets_with_images[0]
print(f"\n✅ Testing with: {test_dataset['name']}")
print(f"   Dataset ID: {test_dataset['id']}")
print(f"   Images: {test_dataset['image_count']}")

# Test API call
print("\n📤 Calling /api/training/start...")

api_url = "http://localhost:8002/api/training/start"
payload = {
    "dataset_id": test_dataset['id'],
    "gpu_type": "rtx6000",
    "rank": 16,
    "steps": 2000,
    "lr": 0.0002
}

print(f"   Payload: {payload}")

try:
    response = requests.post(api_url, json=payload, timeout=120)

    print(f"\n📥 Response status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS!")
        print(f"   Job ID: {result.get('job_id')}")
        print(f"   Message: {result.get('message')}")
    else:
        print(f"❌ Error: {response.text}")

except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()
