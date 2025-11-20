#!/usr/bin/env python3
"""
Reorganize storage: move images into category folders
reference-images/ → reference-images/bikini-mirror-pics/
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CATEGORY = "bikini-mirror-pics"

print("📁 Reorganizing storage with category folders...")

# List all files in reference-images bucket
files = supabase.storage.from_('reference-images').list()

print(f"Found {len(files)} files to move")

for idx, file in enumerate(files, 1):
    old_path = file['name']
    new_path = f"{CATEGORY}/{old_path}"

    print(f"[{idx:3d}/{len(files)}] {old_path[:50]:<50}", end=" → ")

    try:
        # Copy to new location
        old_url = supabase.storage.from_('reference-images').get_public_url(old_path)

        # Download file
        import requests
        response = requests.get(old_url)
        if response.status_code == 200:
            # Upload to new path
            supabase.storage.from_('reference-images').upload(
                new_path,
                response.content,
                file_options={"content-type": "image/jpeg"}
            )

            # Delete old file
            supabase.storage.from_('reference-images').remove([old_path])

            print(f"✓ {new_path}")
        else:
            print(f"✗ Failed to download")
    except Exception as e:
        print(f"✗ Error: {e}")

print(f"\n✓ Reorganization complete!")
