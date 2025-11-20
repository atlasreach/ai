#!/usr/bin/env python3
"""
Test both fixes:
1. Template variables in filename should be replaced properly
2. Generated image should be saved to Supabase Storage
"""
import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client
import tempfile

load_dotenv('api/.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
API_URL = "http://localhost:3001"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("="*70)
print("TESTING FIXES: Template Variables + Supabase Storage Upload")
print("="*70)

# Get Milan model and a reference image
models = supabase.table('models').select('*').eq('id', 1).execute()
model = models.data[0]

ref_images = supabase.table('reference_images')\
    .select('*')\
    .not_.is_('vision_description', 'null')\
    .range(15, 15)\
    .execute()
ref_image = ref_images.data[0]

print(f"\n✓ Model: {model['name']} (slug: {model['slug']})")
print(f"✓ Reference: {ref_image['filename']}")
print(f"  Vision: {ref_image['vision_description'][:80]}...")

# Download and upload
print("\n[1] Downloading reference from Supabase...")
response = supabase.storage.from_('reference-images').download(ref_image['storage_path'])
temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
temp_file.write(response)
temp_file.close()

print("[2] Uploading to ComfyUI...")
with open(temp_file.name, 'rb') as f:
    files = {'image': (ref_image['filename'], f, 'image/jpeg')}
    resp = requests.post(f"{API_URL}/api/upload-image", files=files, timeout=30)
os.unlink(temp_file.name)

if not resp.ok:
    print(f"❌ Upload failed: {resp.text}")
    exit(1)

uploaded_filename = resp.json().get('filename')
print(f"✓ Uploaded: {uploaded_filename}")

# Submit generation
print("\n[3] Submitting generation job...")
ref_filename_no_ext = ref_image['filename'].split('.')[0]
print(f"  Expected output filename: {model['slug']}_{ref_filename_no_ext}_XXXXX_.png")

payload = {
    "modelId": 1,
    "workflowSlug": "img2img-lora",
    "uploadedImageFilename": uploaded_filename,
    "parameters": {
        "denoise": 0.75,
        "cfg": 3.8,
        "steps": 28,
        "seed": -1,
        "lora_strength": 0.65,
        "positive_prompt_suffix": ref_image['vision_description']
    }
}

resp = requests.post(f"{API_URL}/api/generate", json=payload, timeout=30)

if not resp.ok:
    print(f"❌ Generation failed: {resp.text}")
    exit(1)

job_id = resp.json().get('jobId')
print(f"✓ Job {job_id} submitted!\n")

# Poll for completion
print("[4] Polling for completion (max 3 minutes)...")
for i in range(36):
    time.sleep(5)

    resp = requests.get(f"{API_URL}/api/jobs/{job_id}", timeout=10)
    if resp.ok:
        job = resp.json()
        status = job.get('status')
        print(f"  [{(i+1)*5}s] {status}")

        if status == 'completed':
            result_url = job.get('result_image_url')
            print("\n" + "="*70)
            print("✅ SUCCESS! Both fixes verified:")
            print("="*70)
            print(f"\n1. Template Variables:")
            print(f"   Expected filename pattern: {model['slug']}_{ref_filename_no_ext}_*")
            if model['slug'] in result_url and ref_filename_no_ext in result_url:
                print("   ✅ Variables properly replaced!")
            else:
                print("   ⚠️  Variables might not be replaced correctly")

            print(f"\n2. Supabase Storage:")
            print(f"   Result URL: {result_url}")
            if 'supabase' in result_url:
                print("   ✅ Image saved to Supabase Storage!")

                # Verify file exists in bucket
                filename = result_url.split('/')[-1].split('?')[0]
                files = supabase.storage.from_('generated-images').list()
                if any(f['name'] == filename for f in files):
                    print(f"   ✅ File verified in generated-images bucket: {filename}")
                else:
                    print(f"   ⚠️  File not found in bucket listing")
            else:
                print("   ⚠️  Still using ComfyUI URL (not Supabase)")

            print("\n" + "="*70)
            exit(0)

        elif status == 'failed':
            print(f"\n❌ Failed: {job.get('error_message')}")
            exit(1)

        if i % 3 == 0:
            requests.post(f"{API_URL}/api/jobs/{job_id}/check", timeout=10)

print("\n⏱️  Timeout - job still processing")
