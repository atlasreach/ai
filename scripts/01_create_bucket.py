#!/usr/bin/env python3
"""Create S3 bucket with dynamic name from .env"""

import os
import json
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_bucket():
    # Generate bucket name with timestamp
    timestamp = int(datetime.now().timestamp())
    bucket_name = f"andie-workflow-{timestamp}"

    # Get AWS credentials
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-2')

    # Create S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    try:
        # Create bucket with region configuration
        if aws_region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': aws_region}
            )

        # Set bucket policy for public read access
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }

        try:
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print(f"✓ Bucket policy set for public read access")
        except Exception as policy_error:
            print(f"⚠ Warning: Could not set bucket policy: {policy_error}")
            print(f"  Continuing without public access...")

        # Update .env with actual bucket name
        with open('.env', 'r') as f:
            lines = f.readlines()

        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('AWS_S3_BUCKET='):
                    f.write(f'AWS_S3_BUCKET={bucket_name}\n')
                else:
                    f.write(line)

        print(f"✓ Bucket created: {bucket_name}")
        print(f"✓ Region: {aws_region}")
        return bucket_name

    except Exception as e:
        print(f"✗ Error creating bucket: {e}")
        raise

if __name__ == "__main__":
    create_bucket()
