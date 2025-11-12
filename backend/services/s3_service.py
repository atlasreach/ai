"""
AWS S3 Service
Handles image upload and storage to S3 bucket
"""

import os
import boto3
from datetime import datetime
from typing import Optional
from io import BytesIO
from PIL import Image


class S3Service:
    """Service for uploading and managing images in AWS S3"""

    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("AWS_S3_BUCKET")
        self.region = os.getenv("AWS_REGION", "us-east-2")

        if not all([self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError("AWS credentials not found in environment variables")

        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )

        self.base_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com"

    def generate_filename(
        self,
        character_id: str,
        user_id: Optional[str] = None,
        prefix: str = "generated"
    ) -> str:
        """
        Generate a unique filename for uploaded image

        Args:
            character_id: ID of the character used
            user_id: Optional user identifier
            prefix: Folder prefix (e.g., "generated", "uploads")

        Returns:
            S3 key path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        user_part = f"{user_id}_" if user_id else ""

        return f"{prefix}/{character_id}/{user_part}{timestamp}.png"

    async def upload_image(
        self,
        image_bytes: bytes,
        character_id: str,
        user_id: Optional[str] = None,
        prefix: str = "generated"
    ) -> str:
        """
        Upload image to S3 and return public URL

        Args:
            image_bytes: Image data as bytes
            character_id: Character ID for organization
            user_id: Optional user identifier
            prefix: Folder prefix

        Returns:
            Public URL of uploaded image
        """
        try:
            # Generate unique filename
            filename = self.generate_filename(character_id, user_id, prefix)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=image_bytes,
                ContentType='image/png',
                CacheControl='max-age=31536000',  # 1 year cache
            )

            # Return public URL
            public_url = f"{self.base_url}/{filename}"
            return public_url

        except Exception as e:
            print(f"Error uploading to S3: {e}")
            raise

    async def upload_from_url(
        self,
        image_url: str,
        character_id: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        Download image from URL and upload to S3

        Args:
            image_url: URL of image to download
            character_id: Character ID
            user_id: Optional user identifier

        Returns:
            Public URL of uploaded image
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()

                image_bytes = response.content

                return await self.upload_image(
                    image_bytes,
                    character_id,
                    user_id,
                    prefix="generated"
                )

        except Exception as e:
            print(f"Error downloading/uploading image: {e}")
            raise

    async def upload_reference_image(
        self,
        image_bytes: bytes,
        user_id: Optional[str] = None
    ) -> str:
        """
        Upload user's reference image

        Args:
            image_bytes: Image data
            user_id: Optional user identifier

        Returns:
            Public URL of uploaded reference image
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        user_part = f"{user_id}_" if user_id else ""
        filename = f"uploads/reference/{user_part}{timestamp}.png"

        try:
            # Optionally resize/optimize image before upload
            image = Image.open(BytesIO(image_bytes))

            # Convert to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')

            # Save optimized version
            output = BytesIO()
            image.save(output, format='PNG', optimize=True)
            optimized_bytes = output.getvalue()

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=optimized_bytes,
                ContentType='image/png',
            )

            public_url = f"{self.base_url}/{filename}"
            return public_url

        except Exception as e:
            print(f"Error uploading reference image: {e}")
            raise

    def list_user_generations(
        self,
        user_id: str,
        character_id: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """
        List user's generated images

        Args:
            user_id: User identifier
            character_id: Optional filter by character
            limit: Maximum number of results

        Returns:
            List of image URLs
        """
        try:
            prefix = f"generated/{character_id}/{user_id}_" if character_id else f"generated/"

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=limit
            )

            if 'Contents' not in response:
                return []

            images = [
                f"{self.base_url}/{obj['Key']}"
                for obj in response['Contents']
            ]

            return images

        except Exception as e:
            print(f"Error listing user generations: {e}")
            return []
