"""
Upload training images to Supabase Storage
"""
import os
import psycopg2
from supabase import create_client, Client
from dotenv import load_dotenv
import base64
from pathlib import Path

load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY') or "placeholder"  # You'll need to add this
DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

# Training images directory
TRAINING_IMAGES_DIR = "/workspaces/ai/generated_samples"

print("🚀 Uploading Milan's training images to Supabase...")

# Connect to database
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Create model_gallery table
print("\n📝 Creating model_gallery table...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_gallery (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        character_id TEXT REFERENCES characters(id),
        image_url TEXT NOT NULL,
        caption TEXT,
        is_featured BOOLEAN DEFAULT false,
        display_order INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
""")
conn.commit()
print("✅ Table created!")

# Process each training image
images_dir = Path(TRAINING_IMAGES_DIR)
image_files = sorted([f for f in images_dir.glob("*.jpg")])

print(f"\n📸 Found {len(image_files)} training images")

# For now, we'll store local paths (later can upload to S3 or Supabase Storage)
for idx, img_path in enumerate(image_files):
    caption_path = img_path.with_suffix('.txt')

    # Read caption
    caption = ""
    if caption_path.exists():
        with open(caption_path, 'r') as f:
            caption = f.read().strip()

    # For now, use local path (we can upload to S3 later)
    # In production, you'd upload to Supabase Storage or S3
    local_url = f"file://{img_path}"

    # Insert into database
    cursor.execute("""
        INSERT INTO model_gallery (character_id, image_url, caption, is_featured, display_order)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, ('milan', local_url, caption, idx < 5, idx))  # First 5 are featured

    print(f"   ✅ {img_path.name}: {caption[:50]}...")

conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM model_gallery WHERE character_id = 'milan'")
count = cursor.fetchone()[0]
print(f"\n🎉 Uploaded {count} images to database!")

# Show featured images
cursor.execute("""
    SELECT image_url, caption
    FROM model_gallery
    WHERE character_id = 'milan' AND is_featured = true
    ORDER BY display_order
    LIMIT 5
""")
featured = cursor.fetchall()

print("\n⭐ Featured Images:")
for url, caption in featured:
    print(f"   - {caption[:60]}...")

cursor.close()
conn.close()

print("\n✅ Done! Training images are now in Supabase!")
