#!/usr/bin/env python3
"""
Test MaxStudio Face Swap API
"""

import os
import time
import requests
import boto3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MAXSTUDIO_API_KEY = os.getenv('MAXSTUDIO_API_KEY')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')

def upload_to_s3(file_path):
    """Upload file to S3 and return presigned URL"""
    print(f"  📤 Uploading {Path(file_path).name} to S3...")

    s3_client = boto3.client('s3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    key = f'workflow_test/{Path(file_path).name}'
    s3_client.upload_file(file_path, AWS_S3_BUCKET, key)

    # Generate presigned URL (7 days)
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': AWS_S3_BUCKET, 'Key': key},
        ExpiresIn=604800
    )

    print(f"  ✓ Uploaded: {Path(file_path).name}")
    return url

def detect_face(image_url):
    """Detect face in image using MaxStudio API"""
    print(f"\n🔍 Detecting face in target image...")

    response = requests.post(
        'https://api.maxstudio.ai/detect-face-image',
        headers={
            'x-api-key': MAXSTUDIO_API_KEY,
            'Content-Type': 'application/json'
        },
        json={'imageUrl': image_url}
    )

    if response.status_code != 200:
        raise Exception(f"Face detection failed: {response.status_code} - {response.text}")

    data = response.json()
    faces = data.get('detectedFaces', [])

    if not faces:
        raise Exception("No faces detected in image")

    face = faces[0]  # Use first detected face
    print(f"  ✓ Face detected at x={face['x']}, y={face['y']}, w={face['width']}, h={face['height']}")

    return face

def swap_face(target_url, source_url, face_coords):
    """Swap face using MaxStudio API"""
    print(f"\n🔄 Starting face swap...")

    # Build request body
    payload = {
        "mediaUrl": target_url,
        "faces": [
            {
                "originalFace": {
                    "x": face_coords['x'],
                    "y": face_coords['y'],
                    "width": face_coords['width'],
                    "height": face_coords['height']
                },
                "newFace": source_url
            }
        ]
    }

    response = requests.post(
        'https://api.maxstudio.ai/swap-image',
        headers={
            'x-api-key': MAXSTUDIO_API_KEY,
            'Content-Type': 'application/json'
        },
        json=payload
    )

    if response.status_code != 200:
        raise Exception(f"Face swap failed: {response.status_code} - {response.text}")

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
            f'https://api.maxstudio.ai/swap-image/{job_id}',
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
            result = status_data.get('result', {})
            result_url = result.get('mediaUrl')

            if not result_url:
                raise Exception("No mediaUrl in completed response")

            print(f"  ✅ Swap completed!")
            return result_url

        elif status == 'failed':
            raise Exception(f"Face swap failed: {status_data}")

        elif status == 'not-found':
            raise Exception(f"Job not found: {job_id}")

        time.sleep(2)

    raise Exception(f"Timeout waiting for job {job_id}")

def download_image(url, output_path):
    """Download image from URL"""
    print(f"\n💾 Downloading result...")
    response = requests.get(url)
    with open(output_path, 'wb') as f:
        f.write(response.content)
    print(f"  ✓ Saved: {Path(output_path).name}")

def main():
    # Create output directory
    os.makedirs('workflow_test/swapped', exist_ok=True)

    print("=" * 60)
    print("  MAXSTUDIO FACE SWAP - TEST")
    print("=" * 60)

    enhanced_image = 'workflow_test/enhanced/nude_enh_1.jpg'
    source_face = 'source.jpg'
    output_image = 'workflow_test/swapped/nude_swap_1.jpg'

    print(f"\nEnhanced image: {enhanced_image}")
    print(f"Source face: {source_face}")

    try:
        # Step 1: Upload images to S3
        print(f"\n{'=' * 60}")
        print("  STEP 1: Upload to S3")
        print(f"{'=' * 60}")

        enhanced_url = upload_to_s3(enhanced_image)
        source_url = upload_to_s3(source_face)

        # Step 2: Detect face in enhanced image
        print(f"\n{'=' * 60}")
        print("  STEP 2: Detect Face")
        print(f"{'=' * 60}")

        face_coords = detect_face(enhanced_url)

        # Step 3: Swap face
        print(f"\n{'=' * 60}")
        print("  STEP 3: Swap Face")
        print(f"{'=' * 60}")

        result_url = swap_face(enhanced_url, source_url, face_coords)

        # Step 4: Download result
        print(f"\n{'=' * 60}")
        print("  STEP 4: Download Result")
        print(f"{'=' * 60}")

        download_image(result_url, output_image)

        print(f"\n{'=' * 60}")
        print("  ✅ SUCCESS!")
        print(f"{'=' * 60}")
        print(f"\n  Enhanced: {enhanced_image}")
        print(f"  Swapped:  {output_image}")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")

if __name__ == '__main__':
    main()
