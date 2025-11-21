#!/usr/bin/env python3
"""
Upload Milan reference images and analyze with Grok Vision API
"""
import os
import sys
import requests
import base64
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Configuration
GROK_API_KEY = os.getenv('GROK_API_KEY')
CATEGORY = "milan"
ROOT_FOLDER = "/workspaces/ai"

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://yiriqesejsbzmzxdxiqt.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_KEY:
    print("❌ Missing SUPABASE_SERVICE_ROLE_KEY in .env file")
    print("Please add your Supabase service role key to .env")
    sys.exit(1)

if not GROK_API_KEY:
    print("❌ Missing GROK_API_KEY in .env file")
    print("Please add your Grok API key to .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_image_to_storage(file_path, filename):
    """Upload image to Supabase storage"""
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()

        storage_path = f"{CATEGORY}/{filename}"

        # Detect content type
        content_type = "image/jpeg"
        if filename.lower().endswith('.png'):
            content_type = "image/png"
        elif filename.lower().endswith('.webp'):
            content_type = "image/webp"

        # Upload to storage
        response = supabase.storage.from_('reference-images').upload(
            storage_path,
            file_data,
            file_options={"content-type": content_type, "upsert": "true"}
        )

        return storage_path
    except Exception as e:
        print(f"    ✗ Upload error: {e}")
        return None

def analyze_with_grok(image_url):
    """Use Grok Vision API to describe the Milan reference image"""
    try:
        # Download image
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"    ✗ Failed to download image: {response.status_code}")
            return None

        # Encode to base64
        image_data = base64.b64encode(response.content).decode('utf-8')

        # Call Grok Vision API with enhanced prompt
        grok_response = requests.post(
            'https://api.x.ai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {GROK_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'grok-2-vision-1212',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': '''Describe this photo for AI image generation. Combine related elements into continuous phrases:
- Outfit: ONE phrase (e.g., "black leather jacket with white t-shirt and blue jeans"). If nude, say "nude"
- Pose with hand positioning: ONE phrase (e.g., "sitting on chair with hands resting on knees", "standing with left hand on hip and right hand extended")
- Facial expression with eyes: ONE phrase (e.g., "mouth slightly open with confident expression and eyes at camera", "closed mouth smile with eyes looking away")
- Setting with lighting: ONE phrase (e.g., "bedroom setting with soft lighting", "studio setting with natural light")

Format: Comma-separated tags suitable for Stable Diffusion prompt.
DO NOT use category labels like "pose:", "setting:", "outfit:" - just list descriptive tags directly.
DO NOT mention hair color, skin tone, or face features.
Keep it concise and natural.

Example: "black leather jacket with white t-shirt and blue jeans, sitting on chair with hands resting on armrests, closed mouth confident smile with eyes at camera, studio setting with soft lighting"'''
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{image_data}'
                            }
                        }
                    ]
                }],
                'max_tokens': 300,
                'temperature': 0.5
            }
        )

        if grok_response.status_code == 200:
            description = grok_response.json()['choices'][0]['message']['content'].strip()
            return description
        else:
            print(f"    ✗ Grok API error: {grok_response.status_code}")
            print(f"    {grok_response.text}")
            return None

    except Exception as e:
        print(f"    ✗ Analysis error: {e}")
        return None

def save_to_database(filename, storage_path, vision_description):
    """Save reference image metadata to database"""
    try:
        response = supabase.table('reference_images').insert({
            'filename': filename,
            'category': CATEGORY,
            'storage_path': storage_path,
            'vision_description': vision_description
        }).execute()

        return True
    except Exception as e:
        print(f"    ✗ Database error: {e}")
        return False

def main():
    # Get limit from command line (default: process all)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    print("=" * 80)
    print("UPLOAD & ANALYZE MILAN REFERENCE IMAGES")
    print("=" * 80)

    # Get all jpg/png/webp files from root folder
    root_path = Path(ROOT_FOLDER)
    if not root_path.exists():
        print(f"✗ Folder not found: {ROOT_FOLDER}")
        return

    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
        image_files.extend([f for f in root_path.glob(ext) if f.is_file()])

    if not image_files:
        print(f"✗ No images found in {ROOT_FOLDER}")
        return

    print(f"\n✓ Found {len(image_files)} images in root folder")

    # Apply limit if specified
    if limit:
        image_files = image_files[:limit]
        print(f"🧪 Processing {len(image_files)} images (limited)")
    else:
        print(f"📤 Processing all {len(image_files)} images")

    print(f"\n📤 Uploading and analyzing...\n")

    success_count = 0
    failed_count = 0

    for idx, file_path in enumerate(image_files, 1):
        filename = file_path.name
        print(f"[{idx}/{len(image_files)}] {filename}")

        # Step 1: Upload to storage
        print(f"  📤 Uploading to Supabase storage...")
        storage_path = upload_image_to_storage(file_path, filename)

        if not storage_path:
            failed_count += 1
            print(f"  ✗ Upload failed\n")
            continue

        print(f"  ✓ Uploaded to: {storage_path}")

        # Step 2: Get public URL
        image_url = supabase.storage.from_('reference-images').get_public_url(storage_path)
        print(f"  🔗 URL: {image_url[:70]}...")

        # Step 3: Analyze with Grok
        print(f"  🔍 Analyzing with Grok Vision API...")
        vision_description = analyze_with_grok(image_url)

        if not vision_description:
            failed_count += 1
            print(f"  ✗ Analysis failed\n")
            continue

        print(f"  ✓ Description: {vision_description}")

        # Step 4: Save to database
        print(f"  💾 Saving to database...")
        if save_to_database(filename, storage_path, vision_description):
            print(f"  ✓ Saved successfully")
            success_count += 1
        else:
            failed_count += 1
            print(f"  ✗ Failed to save")

        print()

    print("=" * 80)
    print("✓ PROCESS COMPLETE")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(image_files)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
