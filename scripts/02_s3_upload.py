#!/usr/bin/env python3
"""Upload source and target images to S3, generate public URLs"""

import os
import json
import boto3
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_to_s3():
    # Get AWS credentials and bucket name
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-2')
    bucket_name = os.getenv('AWS_S3_BUCKET')

    if not bucket_name:
        raise ValueError("AWS_S3_BUCKET not set in .env")

    # Create S3 client with regional endpoint
    from botocore.client import Config
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region,
        config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
    )

    urls = {}

    # Upload source image
    source_file = 'source/andie_source.jpg'
    s3_key = 'originals/andie_source.jpg'

    print(f"Uploading {source_file}...")
    with open(source_file, 'rb') as f:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=f,
            ContentType='image/jpeg'
        )

    # Generate presigned URL (valid for 7 days)
    urls['source'] = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': s3_key},
        ExpiresIn=604800  # 7 days
    )
    print(f"✓ Source URL: {urls['source']}")

    # Upload target images
    urls['targets'] = []
    for i in range(1, 6):
        target_file = f'targets/nsfw/{i:03d}.jpg'
        s3_key = f'originals/nsfw_{i:03d}.jpg'

        print(f"Uploading {target_file}...")
        with open(target_file, 'rb') as f:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=f,
                ContentType='image/jpeg'
            )

        # Generate presigned URL (valid for 7 days)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=604800  # 7 days
        )
        urls['targets'].append({
            'id': i,
            'url': url
        })
        print(f"✓ Target {i:03d} URL: {url}")

    # Save URLs to JSON
    with open('urls.json', 'w') as f:
        json.dump(urls, f, indent=2)

    print(f"\n✓ All 6 images uploaded to S3")
    print(f"✓ URLs saved to urls.json")

    return urls

if __name__ == "__main__":
    upload_to_s3()
