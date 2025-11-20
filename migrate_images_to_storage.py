#!/usr/bin/env python3
"""
Migrate images from RunPod to Supabase Storage:
1. Delete all existing images in Supabase Storage
2. Download images from RunPod
3. Upload to Supabase Storage
"""
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Configuration
RUNPOD_HOST = "149.36.1.167"
RUNPOD_PORT = 43613
RUNPOD_SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519")
RUNPOD_IMAGE_DIR = "/workspace/ComfyUI/input/bikini_pics"
LOCAL_TEMP_DIR = "/tmp/bikini_pics"

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_supabase_storage():
    """Delete all existing images from Supabase Storage"""
    print("\n🗑️  Cleaning Supabase Storage...")

    try:
        # List all files in reference-images bucket
        files = supabase.storage.from_('reference-images').list()

        if files:
            print(f"  Found {len(files)} existing files")

            # Delete each file
            for file in files:
                filename = file['name']
                supabase.storage.from_('reference-images').remove([filename])
                print(f"  ✓ Deleted: {filename}")

            print(f"✓ Cleaned {len(files)} files from storage")
        else:
            print("  ✓ Storage already empty")

    except Exception as e:
        print(f"  ✗ Error cleaning storage: {e}")

def download_images_from_runpod():
    """Download all bikini images from RunPod to local temp directory"""
    print("\n📥 Downloading images from RunPod...")

    # Create temp directory
    Path(LOCAL_TEMP_DIR).mkdir(parents=True, exist_ok=True)

    # Use rsync to download all images
    cmd = [
        "rsync", "-avz", "-e",
        f"ssh -o StrictHostKeyChecking=no -p {RUNPOD_PORT} -i {RUNPOD_SSH_KEY}",
        f"root@{RUNPOD_HOST}:{RUNPOD_IMAGE_DIR}/",
        f"{LOCAL_TEMP_DIR}/"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        image_files = list(Path(LOCAL_TEMP_DIR).glob("*.jpg"))
        print(f"✓ Downloaded {len(image_files)} images to {LOCAL_TEMP_DIR}")
        return image_files
    else:
        print(f"✗ Download failed: {result.stderr}")
        return []

def upload_to_supabase_storage(image_path):
    """Upload image to Supabase Storage and return public URL"""
    filename = image_path.name

    try:
        # Read image file
        with open(image_path, 'rb') as f:
            image_data = f.read()

        # Upload to Supabase Storage bucket "reference-images"
        supabase.storage.from_('reference-images').upload(
            filename,
            image_data,
            file_options={"content-type": "image/jpeg"}
        )

        # Get public URL
        public_url = supabase.storage.from_('reference-images').get_public_url(filename)

        return public_url
    except Exception as e:
        print(f"  ✗ Upload failed for {filename}: {e}")
        return None

def main():
    print("=" * 60)
    print("MIGRATE IMAGES TO SUPABASE STORAGE")
    print("=" * 60)

    # Step 1: Clean existing storage
    clean_supabase_storage()

    # Step 2: Download from RunPod
    image_files = download_images_from_runpod()

    if not image_files:
        print("\n✗ No images to process")
        return

    # Step 3: Upload to Supabase
    print(f"\n☁️  Uploading {len(image_files)} images to Supabase Storage...")
    uploaded = 0

    for idx, image_path in enumerate(image_files, 1):
        print(f"[{idx:3d}/{len(image_files)}] {image_path.name[:50]:<50}", end=" ")

        public_url = upload_to_supabase_storage(image_path)

        if public_url:
            print("✓")
            uploaded += 1
        else:
            print("✗")

    print("\n" + "=" * 60)
    print(f"✓ MIGRATION COMPLETE")
    print(f"  Uploaded: {uploaded}/{len(image_files)} images")
    print(f"  Bucket: reference-images")
    print("=" * 60)

if __name__ == "__main__":
    main()
