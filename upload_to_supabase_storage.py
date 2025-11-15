"""
Upload training images to Supabase Storage
"""
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
import requests

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', 'placeholder')
DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

TRAINING_IMAGES_DIR = "/workspaces/ai/generated_samples"

print("☁️  Uploading training images to Supabase Storage...")
print(f"   URL: {SUPABASE_URL}")

# Note: To actually upload to Supabase Storage, you need the anon key
# For now, let's just update the database to point to the local files
# and we'll set up Supabase Storage bucket in the Supabase dashboard

print("\n📝 For now, let's check what we have in the database...")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Check current gallery
cursor.execute("""
    SELECT id, character_id, caption, is_featured
    FROM model_gallery
    WHERE character_id = 'milan'
    ORDER BY display_order
    LIMIT 10
""")

rows = cursor.fetchall()
print(f"\n✅ Found {len(rows)} training images in database:")
for row in rows:
    featured = "⭐" if row[3] else "  "
    print(f"   {featured} {row[1]}: {row[2][:60]}...")

cursor.close()
conn.close()

print("\n" + "="*60)
print("NEXT STEPS:")
print("="*60)
print("""
1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Navigate to: Storage → Create a new bucket called 'training-images'
3. Make it public
4. I can then upload the images programmatically

OR

We can skip Supabase Storage and just:
- Use S3 for image storage (you already have it set up)
- Use Supabase only for the database

What would you prefer?
""")
