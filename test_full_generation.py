#!/usr/bin/env python3
"""
Full end-to-end test of the image generation pipeline:
1. Fetch model + reference image from Supabase
2. Download reference image from Supabase Storage
3. Upload to ComfyUI
4. Submit generation job (combines model attributes + Grok Vision caption)
5. Poll for completion
6. Display result
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv
from supabase import create_client
import tempfile

load_dotenv('api/.env')

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
API_URL = "http://localhost:3001"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_step(step_num, description):
    print(f"[{step_num}] {description}")

def main():
    print_section("FULL END-TO-END GENERATION TEST")

    # Step 1: Select a model
    print_step(1, "Selecting a model from database...")
    models = supabase.table('models').select('*').limit(1).execute()
    if not models.data:
        print("❌ No models found!")
        return

    model = models.data[0]
    print(f"✓ Selected: {model['name']}")
    print(f"  ID: {model['id']}")
    print(f"  Trigger: {model['trigger_word']}")
    print(f"  LoRA: {model['lora_file']}")
    print(f"  Attributes: {model['skin_tone']} skin, {model['hair_style']}")
    print(f"  Negative: {model['negative_prompt']}")

    # Step 2: Select a reference image with vision description
    print_step(2, "Selecting reference image with Grok Vision caption...")
    ref_images = supabase.table('reference_images')\
        .select('*')\
        .not_.is_('vision_description', 'null')\
        .limit(1)\
        .execute()

    if not ref_images.data:
        print("❌ No reference images found!")
        return

    ref_image = ref_images.data[0]
    print(f"✓ Selected: {ref_image['filename']}")
    print(f"  Category: {ref_image['category']}")
    print(f"  Storage path: {ref_image['storage_path']}")
    print(f"  Vision caption: {ref_image['vision_description'][:150]}...")

    # Step 3: Download image from Supabase Storage
    print_step(3, "Downloading reference image from Supabase Storage...")
    try:
        # Get public URL for the image
        bucket_name = 'reference-images'
        file_path = ref_image['storage_path']

        # Generate signed URL
        response = supabase.storage.from_(bucket_name).download(file_path)

        if response:
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(response)
            temp_file.close()
            print(f"✓ Downloaded to: {temp_file.name}")
            print(f"  Size: {len(response)} bytes")
        else:
            print("❌ Failed to download image")
            return
    except Exception as e:
        print(f"❌ Download error: {e}")
        return

    # Step 4: Upload image to ComfyUI
    print_step(4, "Uploading image to ComfyUI...")
    try:
        with open(temp_file.name, 'rb') as f:
            files = {'image': (ref_image['filename'], f, 'image/jpeg')}
            response = requests.post(
                f"{API_URL}/api/upload-image",
                files=files,
                timeout=30
            )

        if response.ok:
            upload_result = response.json()
            uploaded_filename = upload_result.get('filename')
            print(f"✓ Uploaded as: {uploaded_filename}")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)
            return
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return
    finally:
        # Clean up temp file
        os.unlink(temp_file.name)

    # Step 5: Submit generation job
    print_step(5, "Submitting generation job...")

    # Build the combined prompt
    vision_snippet = ref_image['vision_description'][:100]

    generation_payload = {
        "modelId": model['id'],
        "workflowSlug": "img2img-lora",
        "uploadedImageFilename": uploaded_filename,
        "parameters": {
            "denoise": 0.75,
            "cfg": 3.8,
            "steps": 28,
            "seed": -1,  # Random seed
            "lora_strength": 0.65,
            "positive_prompt_suffix": ref_image['vision_description']
        }
    }

    print("  Payload:")
    print(f"    Model: {model['name']} (ID: {model['id']})")
    print(f"    Workflow: img2img-lora")
    print(f"    Reference: {uploaded_filename}")
    print(f"    Parameters: denoise={generation_payload['parameters']['denoise']}, cfg={generation_payload['parameters']['cfg']}, steps={generation_payload['parameters']['steps']}")

    print("\n  Combined Prompt Preview:")
    combined_positive = f"{model['trigger_word']}, {model['hair_style']}, {model['skin_tone']} skin, {vision_snippet}..."
    print(f"    Positive: {combined_positive}")
    print(f"    Negative: {model['negative_prompt']}")

    try:
        response = requests.post(
            f"{API_URL}/api/generate",
            json=generation_payload,
            timeout=30
        )

        if response.ok:
            job_result = response.json()
            job_id = job_result.get('jobId')
            runpod_job_id = job_result.get('runpodJobId')
            print(f"\n✓ Job submitted!")
            print(f"  Job ID: {job_id}")
            print(f"  RunPod Job ID: {runpod_job_id}")
        else:
            print(f"❌ Generation failed: {response.status_code}")
            print(response.text)
            return
    except Exception as e:
        print(f"❌ Generation error: {e}")
        return

    # Step 6: Poll for completion
    print_step(6, "Polling for completion...")
    max_attempts = 60  # 5 minutes max
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        time.sleep(5)  # Poll every 5 seconds

        try:
            # Check job status in database
            response = requests.get(f"{API_URL}/api/jobs/{job_id}", timeout=10)

            if response.ok:
                job = response.json()
                status = job.get('status')

                print(f"  [{attempt}/{max_attempts}] Status: {status}")

                if status == 'completed':
                    print_section("✓ GENERATION COMPLETE!")
                    print(f"Job ID: {job_id}")
                    print(f"Status: {status}")
                    print(f"Result URL: {job.get('result_image_url')}")
                    print(f"Prompt used: {job.get('prompt_used')}")
                    print(f"Created: {job.get('created_at')}")
                    print(f"Completed: {job.get('completed_at')}")
                    print(f"\nView your generated image at:")
                    print(f"  {job.get('result_image_url')}")
                    return

                elif status == 'failed':
                    print(f"\n❌ Generation failed!")
                    print(f"Error: {job.get('error_message')}")
                    return

                # Try checking with ComfyUI
                if attempt % 3 == 0:  # Every 15 seconds
                    check_response = requests.post(
                        f"{API_URL}/api/jobs/{job_id}/check",
                        timeout=10
                    )
                    if check_response.ok:
                        check_result = check_response.json()
                        print(f"      ComfyUI status: {check_result.get('status')}")

        except Exception as e:
            print(f"  Error checking status: {e}")

    print("\n⏱️  Timeout reached. Job may still be processing.")
    print(f"Check status manually: GET {API_URL}/api/jobs/{job_id}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
