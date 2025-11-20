#!/usr/bin/env python3
"""
Test with Milan again (we know this LoRA works) but different reference image
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
    print("🚀 TESTING WITH MILAN + DIFFERENT REFERENCE")
    print("="*60)

    # Use Milan model (we know it works)
    models = supabase.table('models').select('*').eq('id', 1).execute()
    model = models.data[0]

    # Get a DIFFERENT reference image (10th one)
    ref_images = supabase.table('reference_images')\
        .select('*')\
        .not_.is_('vision_description', 'null')\
        .range(10, 10)\
        .execute()

    ref_image = ref_images.data[0]

    print(f"\n✓ Model: {model['name']} (LoRA: {model['lora_file']})")
    print(f"✓ Reference: {ref_image['filename']}")
    print(f"  Vision: {ref_image['vision_description'][:100]}...")

    # Download
    print("\n[1] Downloading...")
    response = supabase.storage.from_('reference-images').download(ref_image['storage_path'])
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_file.write(response)
    temp_file.close()
    print(f"✓ Downloaded")

    # Upload
    print("[2] Uploading...")
    with open(temp_file.name, 'rb') as f:
        files = {'image': (ref_image['filename'], f, 'image/jpeg')}
        resp = requests.post(f"{API_URL}/api/upload-image", files=files, timeout=30)
    os.unlink(temp_file.name)

    uploaded_filename = resp.json().get('filename')
    print(f"✓ Uploaded: {uploaded_filename}")

    # Generate
    print("[3] Generating...")

    payload = {
        "modelId": 1,  # Milan
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

    combined = f"{model['trigger_word']}, {model['hair_style']}, {model['skin_tone']} skin, {ref_image['vision_description'][:60]}..."
    print(f"  Prompt: {combined}")

    resp = requests.post(f"{API_URL}/api/generate", json=payload, timeout=30)

    if not resp.ok:
        print(f"❌ Failed: {resp.text}")
        return

    job_id = resp.json().get('jobId')
    print(f"✓ Job {job_id} submitted!\n")

    # Poll for 3 minutes
    print("[4] Polling (3 min max)...")
    start_time = time.time()

    for i in range(36):  # 36 * 5 = 3 minutes
        time.sleep(5)
        elapsed = int(time.time() - start_time)

        resp = requests.get(f"{API_URL}/api/jobs/{job_id}", timeout=10)
        if resp.ok:
            job = resp.json()
            status = job.get('status')
            print(f"  [{elapsed}s] {status}")

            if status == 'completed':
                print(f"\n✅ COMPLETE!")
                print(f"URL: {job.get('result_image_url')}")
                return

            elif status == 'failed':
                print(f"❌ Failed: {job.get('error_message')}")
                return

            if i % 3 == 0:
                requests.post(f"{API_URL}/api/jobs/{job_id}/check", timeout=10)

    print(f"\n⏱️  Still processing")

if __name__ == '__main__':
    main()
