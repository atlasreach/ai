"""S3 operations for MaxStudio workflow"""

import os
import json
import boto3
from datetime import datetime
from botocore.client import Config


class S3Manager:
    """Manages all S3 operations for the workflow"""

    def __init__(self):
        self.access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region = os.getenv('AWS_REGION', 'us-east-2')
        self.bucket_name = os.getenv('AWS_S3_BUCKET')

        self.client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
        )

    def create_bucket(self, model_name):
        """Create S3 bucket with timestamp"""
        timestamp = int(datetime.now().timestamp())
        bucket_name = f"{model_name}-workflow-{timestamp}"

        try:
            # Create bucket with region configuration
            if self.region == 'us-east-1':
                self.client.create_bucket(Bucket=bucket_name)
            else:
                self.client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )

            # Attempt bucket policy (may fail due to Block Public Access)
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }]
            }

            try:
                self.client.put_bucket_policy(
                    Bucket=bucket_name,
                    Policy=json.dumps(bucket_policy)
                )
            except Exception:
                # Silently continue without public access
                pass

            # Update instance bucket name
            self.bucket_name = bucket_name

            return bucket_name

        except Exception as e:
            raise RuntimeError(f"Failed to create bucket: {e}")

    def upload_file(self, filepath, s3_key, content_type='image/jpeg'):
        """Upload file to S3 and return presigned URL"""
        if not self.bucket_name:
            raise ValueError("Bucket name not set. Create or load bucket first.")

        with open(filepath, 'rb') as f:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=f,
                ContentType=content_type
            )

        # Generate presigned URL (7 days)
        url = self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': s3_key},
            ExpiresIn=604800
        )

        return url

    def upload_multiple(self, files_dict):
        """
        Upload multiple files and return dict of presigned URLs

        Args:
            files_dict: dict like {'originals/source.jpg': 'path/to/source.jpg', ...}

        Returns:
            dict like {'originals/source.jpg': 'https://...', ...}
        """
        urls = {}
        for s3_key, filepath in files_dict.items():
            urls[s3_key] = self.upload_file(filepath, s3_key)
        return urls
