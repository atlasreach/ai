#!/usr/bin/env python3
"""
Test face detection on original image
"""

import os
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
    print(f"📤 Uploading {Path(file_path).name} to S3...")

    s3_client = boto3.client('s3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    key = f'workflow_test/{Path(file_path).name}'
    s3_client.upload_file(file_path, AWS_S3_BUCKET, key)

    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': AWS_S3_BUCKET, 'Key': key},
        ExpiresIn=604800
    )

    print(f"✓ URL: {url[:80]}...")
    return url

def detect_face(image_url):
    """Detect face in image"""
    print(f"\n🔍 Detecting face...")

    response = requests.post(
        'https://api.maxstudio.ai/detect-face-image',
        headers={
            'x-api-key': MAXSTUDIO_API_KEY,
            'Content-Type': 'application/json'
        },
        json={'imageUrl': image_url}
    )

    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")

    if response.status_code != 200:
        raise Exception(f"Failed: {response.status_code} - {response.text}")

    data = response.json()
    return data

# Test both images
print("Testing original image:")
print("=" * 60)
original_url = upload_to_s3('download.jpeg')
result = detect_face(original_url)
print(f"✓ Result: {result}")

print("\n\nTesting enhanced image:")
print("=" * 60)
enhanced_url = upload_to_s3('workflow_test/enhanced/nude_enh_1.jpg')
result = detect_face(enhanced_url)
print(f"✓ Result: {result}")
