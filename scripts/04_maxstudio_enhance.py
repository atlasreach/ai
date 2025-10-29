#!/usr/bin/env python3
"""Enhance swapped images using MaxStudio API"""

import os
import json
import time
import base64
import requests
import boto3
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('MAXSTUDIO_API_KEY')
BASE_URL = 'https://api.maxstudio.ai'

def image_to_base64(filepath):
    """Convert image file to base64 (no prefix)"""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def base64_to_image(b64_string, filepath):
    """Convert base64 to image file"""
    # Remove data URI prefix if present
    if ',' in b64_string:
        b64_string = b64_string.split(',', 1)[1]

    img_data = base64.b64decode(b64_string)
    with open(filepath, 'wb') as f:
        f.write(img_data)

def enhance_image(image_base64):
    """Initiate image enhancement job"""
    url = f"{BASE_URL}/image-enhancer"
    headers = {'x-api-key': API_KEY}
    payload = {
        'image': image_base64,
        'upscale': 2  # 2x upscale
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    return data.get('jobId')

def check_job_status(job_id):
    """Check enhancement job status"""
    url = f"{BASE_URL}/image-enhancer/{job_id}"
    headers = {'x-api-key': API_KEY}

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def upload_to_s3(filepath, s3_key):
    """Upload enhanced image to S3"""
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-2')
    bucket_name = os.getenv('AWS_S3_BUCKET')

    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    with open(filepath, 'rb') as f:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=f,
            ContentType='image/jpeg'
        )

    # Generate presigned URL (valid for 7 days)
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': s3_key},
        ExpiresIn=604800  # 7 days
    )

    return presigned_url

def main():
    # Load swap results
    with open('swap_results.json', 'r') as f:
        swap_results = json.load(f)

    results = []

    print(f"Enhancing {len(swap_results)} swapped images...\n")

    for swap_info in swap_results:
        swap_id = swap_info['id']
        swap_file = swap_info['local_path']

        print(f"[{swap_id}/{len(swap_results)}] Enhancing {swap_file}...")

        # Step 1: Convert to base64
        print(f"  • Converting to base64...")
        try:
            image_b64 = image_to_base64(swap_file)
            print(f"  ✓ Base64 size: {len(image_b64)} chars")
        except Exception as e:
            print(f"  ✗ Conversion failed: {e}")
            continue

        # Step 2: Initiate enhancement
        print(f"  • Starting enhancement...")
        try:
            job_id = enhance_image(image_b64)
            print(f"  ✓ Job created: {job_id}")
        except Exception as e:
            print(f"  ✗ Enhancement failed: {e}")
            continue

        # Step 3: Poll for completion
        print(f"  • Polling for completion...")
        max_attempts = 60
        attempt = 0

        while attempt < max_attempts:
            try:
                status_data = check_job_status(job_id)
                status = status_data.get('status')

                if status == 'completed':
                    result_base64 = status_data.get('result')
                    print(f"  ✓ Completed! Base64 size: {len(result_base64)} chars")

                    # Save enhanced image
                    output_file = f'enhanced/andie_nsfw_{swap_id:03d}_enhanced.jpg'
                    base64_to_image(result_base64, output_file)
                    print(f"  ✓ Saved to {output_file}")

                    # Upload to S3
                    s3_key = f'enhanced/andie_nsfw_{swap_id:03d}_enhanced.jpg'
                    s3_url = upload_to_s3(output_file, s3_key)
                    print(f"  ✓ Uploaded to S3: {s3_url}")

                    results.append({
                        'id': swap_id,
                        'job_id': job_id,
                        'local_path': output_file,
                        's3_url': s3_url
                    })
                    break

                elif status == 'failed':
                    print(f"  ✗ Job failed: {status_data.get('error', 'Unknown error')}")
                    break

                else:
                    print(f"  ⏳ Status: {status} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(5)
                    attempt += 1

            except Exception as e:
                print(f"  ✗ Error checking status: {e}")
                break

        if attempt >= max_attempts:
            print(f"  ✗ Timeout waiting for job {job_id}")

        print()

    # Save results
    with open('enhance_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"✓ Enhancement complete: {len(results)}/{len(swap_results)} successful")
    print(f"✓ Results saved to enhance_results.json")

if __name__ == "__main__":
    main()
