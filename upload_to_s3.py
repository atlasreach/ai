"""
Upload training images to S3 and update Supabase with public URLs
"""
import os
import boto3
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# AWS S3 Setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-2')
)
S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'ai-character-generations')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')

# Database
DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

# Training images directory
TRAINING_IMAGES_DIR = "/workspaces/ai/generated_samples"

print("☁️  Uploading training images to S3...")

# Get images
images_dir = Path(TRAINING_IMAGES_DIR)
image_files = sorted([f for f in images_dir.glob("*.jpg")])

print(f"📸 Found {len(image_files)} images to upload")

# Upload each to S3
uploaded_urls = {}
for img_path in image_files:
    # S3 key
    s3_key = f"training-images/milan/{img_path.name}"

    # Upload
    try:
        with open(img_path, 'rb') as f:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=f,
                ContentType='image/jpeg',
                CacheControl='max-age=31536000'  # Cache for 1 year
            )

        # Public URL
        url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        uploaded_urls[img_path.name] = url

        print(f"   ✅ {img_path.name} → {url[:70]}...")

    except Exception as e:
        print(f"   ❌ Failed to upload {img_path.name}: {e}")

print(f"\n🎉 Uploaded {len(uploaded_urls)} images to S3!")

# Update Supabase with real URLs
print("\n📝 Updating database with S3 URLs...")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

for filename, url in uploaded_urls.items():
    # Update the record
    cursor.execute("""
        UPDATE model_gallery
        SET image_url = %s
        WHERE image_url LIKE %s
    """, (url, f'%{filename}%'))

conn.commit()
print("✅ Database updated!")

# Verify
cursor.execute("""
    SELECT image_url FROM model_gallery
    WHERE character_id = 'milan' AND is_featured = true
    LIMIT 3
""")
sample_urls = cursor.fetchall()

print("\n🔗 Sample URLs:")
for (url,) in sample_urls:
    print(f"   {url}")

cursor.close()
conn.close()

print("\n✅ All done! Training images are live on S3 and in Supabase!")
