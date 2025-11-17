"""
Test complete dataset creation flow
"""
import requests
from dotenv import dotenv_values
from supabase import create_client
import time

# Load env
env = dotenv_values("/workspaces/ai/.env")
supabase = create_client(env.get('SUPABASE_URL'), env.get('SUPABASE_SERVICE_ROLE_KEY'))

API_BASE = "http://localhost:8002"

print("\n" + "="*60)
print("  TESTING COMPLETE DATASET WORKFLOW")
print("="*60 + "\n")

# Step 1: Create model
print("📝 Step 1: Creating test model...")
model_data = {
    "name": "TestModel",
    "trigger_word": "testmodel",
    "defining_features": {},
    "is_active": True
}
result = supabase.table('models').insert(model_data).execute()
model_id = result.data[0]['id']
print(f"  ✅ Model created: {model_id}\n")

# Step 2: Create dataset
print("📂 Step 2: Creating test dataset...")
dataset_data = {
    "model_id": model_id,
    "name": "testmodel_v1",
    "dataset_type": "SFW",
    "image_count": 0,
    "training_status": "preparing"
}
result = supabase.table('datasets').insert(dataset_data).execute()
dataset_id = result.data[0]['id']
print(f"  ✅ Dataset created: {dataset_id}\n")

# Step 3: Add 3 test images
print("🖼️  Step 3: Adding test images...")
test_images = [
    {"dataset_id": dataset_id, "image_url": f"https://picsum.photos/512/512?random={i}", "caption": "", "display_order": i}
    for i in range(3)
]
result = supabase.table('dataset_images').insert(test_images).execute()
print(f"  ✅ Added {len(result.data)} images\n")

# Update dataset image count
supabase.table('datasets').update({"image_count": 3}).eq('id', dataset_id).execute()

# Step 4: Generate captions
print("✨ Step 4: Generating captions...")
response = requests.post(f"{API_BASE}/api/datasets/{dataset_id}/generate-all-captions")
print(f"  Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"  ✅ Generated {data['updated_count']} captions")
    print(f"  📊 Test captions: {len(data.get('test_captions', []))} generated")

    if data.get('test_captions'):
        print("\n  Sample test captions:")
        for i, cap in enumerate(data['test_captions'][:3], 1):
            print(f"    {i}. {cap[:80]}...")
else:
    print(f"  ❌ Failed: {response.text}")

print("\n" + "="*60)
print("  TEST COMPLETE")
print("="*60 + "\n")
print(f"Model ID: {model_id}")
print(f"Dataset ID: {dataset_id}\n")
