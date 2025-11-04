#!/usr/bin/env python3
"""
Enhance and Face Swap Workflow
1. Enhance target image
2. Swap source face onto enhanced image
"""

import os
import sys
import time
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MAXSTUDIO_API_KEY = os.getenv('MAXSTUDIO_API_KEY')
BASE_URL = 'https://api.maxstudio.ai/v1'

def image_to_base64(image_path):
    """Convert image to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def base64_to_image(b64_string, output_path):
    """Save base64 string to image file"""
    img_data = base64.b64decode(b64_string)
    with open(output_path, 'wb') as f:
        f.write(img_data)

def enhance_image(image_path, output_path, upscale=2):
    """Enhance image using MaxStudio API"""
    print(f"\n🔄 Enhancing: {Path(image_path).name}")

    # Convert to base64
    img_b64 = image_to_base64(image_path)

    # Start enhancement job
    response = requests.post(
        f'{BASE_URL}/enhance',
        headers={'x-api-key': MAXSTUDIO_API_KEY},
        json={
            'image': img_b64,
            'upscale': upscale,
            'webhook': None
        }
    )

    if response.status_code != 200:
        raise Exception(f"Enhancement failed: {response.text}")

    job_id = response.json()['id']
    print(f"  ✓ Job created: {job_id}")

    # Poll for completion
    print("  ⏳ Waiting for enhancement...")
    while True:
        status_response = requests.get(
            f'{BASE_URL}/enhance/{job_id}',
            headers={'x-api-key': MAXSTUDIO_API_KEY}
        )

        status_data = status_response.json()

        if status_data['status'] == 'succeeded':
            result_b64 = status_data['output']['image']
            base64_to_image(result_b64, output_path)
            print(f"  ✓ Enhanced: {Path(output_path).name}")
            return output_path
        elif status_data['status'] == 'failed':
            raise Exception(f"Enhancement failed: {status_data.get('error')}")

        time.sleep(2)

def detect_face(image_url):
    """Detect face in image"""
    response = requests.post(
        f'{BASE_URL}/detect-face',
        headers={'x-api-key': MAXSTUDIO_API_KEY},
        json={'image': image_url}
    )

    if response.status_code != 200:
        raise Exception(f"Face detection failed: {response.text}")

    faces = response.json()['detectedFaces']
    if not faces:
        raise Exception("No face detected")

    return faces[0]  # Return first face

def swap_face(source_url, target_url, face_coords):
    """Swap face using MaxStudio API"""
    print(f"\n🔄 Swapping face...")

    # Start swap job
    response = requests.post(
        f'{BASE_URL}/swap-image',
        headers={'x-api-key': MAXSTUDIO_API_KEY},
        json={
            'newFace': source_url,
            'image': target_url,
            'face': face_coords
        }
    )

    if response.status_code != 200:
        raise Exception(f"Face swap failed: {response.text}")

    job_id = response.json()['id']
    print(f"  ✓ Job created: {job_id}")

    # Poll for completion
    print("  ⏳ Waiting for face swap...")
    while True:
        status_response = requests.get(
            f'{BASE_URL}/swap-image/{job_id}',
            headers={'x-api-key': MAXSTUDIO_API_KEY}
        )

        status_data = status_response.json()

        if status_data['status'] == 'succeeded':
            result_url = status_data['output']['url']
            print(f"  ✓ Swap complete")
            return result_url
        elif status_data['status'] == 'failed':
            raise Exception(f"Swap failed: {status_data.get('error')}")

        time.sleep(2)

def download_image(url, output_path):
    """Download image from URL"""
    response = requests.get(url)
    with open(output_path, 'wb') as f:
        f.write(response.content)

def upload_to_s3(file_path):
    """Upload file to S3 and return presigned URL"""
    import boto3

    s3_client = boto3.client('s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )

    bucket = os.getenv('AWS_S3_BUCKET')
    key = f'workflow_test/{Path(file_path).name}'

    s3_client.upload_file(file_path, bucket, key)

    # Generate presigned URL (7 days)
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=604800
    )

    return url

def main():
    # Create output directories
    os.makedirs('workflow_test/enhanced', exist_ok=True)
    os.makedirs('workflow_test/swapped', exist_ok=True)

    # Test images
    test_images = [
        'download.jpeg',
        '12480716.jpg'
    ]

    source_face = 'source.jpg'

    print("=" * 60)
    print("  ENHANCE & FACE SWAP WORKFLOW - TEST RUN")
    print("=" * 60)
    print(f"\nSource face: {source_face}")
    print(f"Test images: {len(test_images)}")

    # Upload source face to S3
    print(f"\n📤 Uploading source face to S3...")
    source_s3_url = upload_to_s3(source_face)
    print(f"  ✓ Source uploaded")

    for idx, image in enumerate(test_images, 1):
        print(f"\n{'=' * 60}")
        print(f"  PROCESSING IMAGE {idx}/{len(test_images)}: {image}")
        print(f"{'=' * 60}")

        try:
            # Step 1: Enhance
            enhanced_path = f'workflow_test/enhanced/nude_enh_{idx}.jpg'
            enhance_image(image, enhanced_path)

            # Upload enhanced to S3
            print(f"\n📤 Uploading enhanced image to S3...")
            enhanced_s3_url = upload_to_s3(enhanced_path)
            print(f"  ✓ Enhanced uploaded")

            # Step 2: Detect face in enhanced image
            print(f"\n🔍 Detecting face in enhanced image...")
            face = detect_face(enhanced_s3_url)
            print(f"  ✓ Face detected at ({face['x']}, {face['y']})")

            # Step 3: Swap face
            result_url = swap_face(source_s3_url, enhanced_s3_url, face)

            # Step 4: Download result
            swapped_path = f'workflow_test/swapped/nude_swap_{idx}.jpg'
            print(f"\n💾 Downloading result...")
            download_image(result_url, swapped_path)
            print(f"  ✓ Saved: {swapped_path}")

            print(f"\n✅ SUCCESS: Image {idx} complete!")

        except Exception as e:
            print(f"\n❌ FAILED: {e}")
            continue

    print(f"\n{'=' * 60}")
    print("  WORKFLOW COMPLETE!")
    print(f"{'=' * 60}")
    print(f"\nResults saved in workflow_test/")

if __name__ == '__main__':
    main()
