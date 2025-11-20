#!/usr/bin/env python3
"""
Quick generation test with a different reference image
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

def main():
    print("🚀 QUICK GENERATION TEST (2nd run)")
    print("="*60)

    # Use a different model and reference image
    print("\n[1] Fetching model and reference image...")

    # Get second model
    models = supabase.table('models').select('*').eq('id', 2).execute()
    model = models.data[0] if models.data else None

    # Get a different reference image (offset by 5)
    ref_images = supabase.table('reference_images')\
        .select('*')\
        .not_.is_('vision_description', 'null')\
        .range(5, 5)\
        .execute()

    ref_image = ref_images.data[0] if ref_images.data else None

    if not model or not ref_image:
        print("❌ Could not fetch data")
        return

    print(f"✓ Model: {model['name']} ({model['trigger_word']})")
    print(f"✓ Reference: {ref_image['filename']}")
    print(f"  Vision: {ref_image['vision_description'][:80]}...")

    # Download from Supabase Storage
    print("\n[2] Downloading from Supabase Storage...")
    response = supabase.storage.from_('reference-images').download(ref_image['storage_path'])

    if not response:
        print("❌ Failed to download")
        return

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_file.write(response)
    temp_file.close()
    print(f"✓ Downloaded ({len(response)} bytes)")

    # Upload to ComfyUI
    print("\n[3] Uploading to ComfyUI...")
    with open(temp_file.name, 'rb') as f:
        files = {'image': (ref_image['filename'], f, 'image/jpeg')}
        resp = requests.post(f"{API_URL}/api/upload-image", files=files, timeout=30)

    os.unlink(temp_file.name)

    if not resp.ok:
        print(f"❌ Upload failed: {resp.text}")
        return

    uploaded_filename = resp.json().get('filename')
    print(f"✓ Uploaded as: {uploaded_filename}")

    # Submit generation
    print("\n[4] Submitting generation job...")

    payload = {
        "modelId": model['id'],
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

    combined_prompt = f"{model['trigger_word']}, {model['hair_style']}, {model['skin_tone']} skin, {ref_image['vision_description'][:80]}..."
    print(f"  Combined prompt: {combined_prompt}")

    resp = requests.post(f"{API_URL}/api/generate", json=payload, timeout=30)

    if not resp.ok:
        print(f"❌ Generation failed: {resp.text}")
        return

    result = resp.json()
    job_id = result.get('jobId')
    print(f"\n✓ Job submitted! ID: {job_id}")
    print(f"  RunPod Job: {result.get('runpodJobId')}")

    # Quick polling (30 checks = 2.5 minutes)
    print("\n[5] Polling for completion (2.5 min max)...")
    for i in range(30):
        time.sleep(5)

        resp = requests.get(f"{API_URL}/api/jobs/{job_id}", timeout=10)
        if resp.ok:
            job = resp.json()
            status = job.get('status')
            print(f"  [{i+1}/30] {status}")

            if status == 'completed':
                print(f"\n✅ SUCCESS!")
                print(f"Result URL: {job.get('result_image_url')}")
                print(f"Prompt: {job.get('prompt_used')[:100]}...")
                return

            elif status == 'failed':
                print(f"❌ Failed: {job.get('error_message')}")
                return

            # Check with ComfyUI every 3rd attempt
            if i % 3 == 0:
                requests.post(f"{API_URL}/api/jobs/{job_id}/check", timeout=10)

    print(f"\n⏱️  Still processing after 2.5 min")
    print(f"Check: GET {API_URL}/api/jobs/{job_id}")

if __name__ == '__main__':
    main()
