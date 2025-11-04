#!/usr/bin/env python3
"""
Test MaxStudio Image Enhancer API
"""

import os
import time
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MAXSTUDIO_API_KEY = os.getenv('MAXSTUDIO_API_KEY')

def image_to_base64(image_path):
    """Convert image to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def base64_to_image(b64_string, output_path):
    """Save base64 string to image file"""
    img_data = base64.b64decode(b64_string)
    with open(output_path, 'wb') as f:
        f.write(img_data)

def enhance_image(image_path, output_path):
    """Enhance image using MaxStudio API"""
    print(f"\n🔄 Enhancing: {Path(image_path).name}")

    # Convert to base64 (without prefix)
    img_b64 = image_to_base64(image_path)
    print(f"  📊 Image size: {len(img_b64)} chars")

    # Start enhancement job
    print(f"  🚀 Sending to MaxStudio...")
    response = requests.post(
        'https://api.maxstudio.ai/image-enhancer',
        headers={
            'x-api-key': MAXSTUDIO_API_KEY,
            'Content-Type': 'application/json'
        },
        json={'image': img_b64}
    )

    if response.status_code != 200:
        raise Exception(f"Enhancement failed: {response.status_code} - {response.text}")

    job_data = response.json()
    job_id = job_data.get('jobId')

    if not job_id:
        raise Exception(f"No jobId returned: {job_data}")

    print(f"  ✓ Job created: {job_id}")

    # Poll for completion
    print(f"  ⏳ Waiting for completion...")
    max_attempts = 60  # 2 minutes max
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        status_response = requests.get(
            f'https://api.maxstudio.ai/image-enhancer/{job_id}',
            headers={'x-api-key': MAXSTUDIO_API_KEY}
        )

        if status_response.status_code != 200:
            print(f"  ⚠️  Status check failed: {status_response.status_code}")
            time.sleep(2)
            continue

        status_data = status_response.json()
        status = status_data.get('status')

        print(f"  📍 Status: {status} (attempt {attempt})")

        if status == 'completed':
            result_b64 = status_data.get('result')
            if not result_b64:
                raise Exception("No result in completed response")

            base64_to_image(result_b64, output_path)
            print(f"  ✅ Enhanced saved: {Path(output_path).name}")
            return output_path

        elif status == 'failed':
            raise Exception(f"Enhancement failed: {status_data}")

        elif status == 'not-found':
            raise Exception(f"Job not found: {job_id}")

        time.sleep(2)

    raise Exception(f"Timeout waiting for job {job_id}")

def main():
    # Create output directory
    os.makedirs('workflow_test/enhanced', exist_ok=True)

    # Test with one image
    test_image = 'download.jpeg'

    print("=" * 60)
    print("  MAXSTUDIO IMAGE ENHANCER - TEST")
    print("=" * 60)
    print(f"\nTest image: {test_image}")

    try:
        enhanced_path = 'workflow_test/enhanced/nude_enh_1.jpg'
        enhance_image(test_image, enhanced_path)
        print(f"\n✅ SUCCESS!")
        print(f"   Original: {test_image}")
        print(f"   Enhanced: {enhanced_path}")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")

if __name__ == '__main__':
    main()
