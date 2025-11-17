#!/usr/bin/env python3
"""
Re-host Instagram Images to Supabase Storage
Downloads Instagram CDN images and uploads them to Supabase storage
so they don't expire and are accessible without authentication
"""
import os
import requests
import json
from supabase import create_client
from dotenv import load_dotenv
from time import sleep

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

def download_and_upload_image(image_url: str, storage_path: str) -> str:
    """Download image from Instagram CDN and upload to Supabase storage"""
    try:
        # Download from Instagram
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(image_url, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"  ⚠️  Failed to download: HTTP {response.status_code}")
            return None

        # Upload to Supabase storage
        result = supabase.storage.from_('images').upload(
            storage_path,
            response.content,
            {'content-type': 'image/jpeg', 'upsert': 'true'}
        )

        # Get public URL
        public_url = supabase.storage.from_('images').get_public_url(storage_path)
        return public_url

    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")
        return None

def main():
    print("=" * 70)
    print("RE-HOSTING INSTAGRAM IMAGES TO SUPABASE STORAGE")
    print("=" * 70)

    # Get all posts
    posts_result = supabase.table('instagram_posts').select('*').execute()
    posts = posts_result.data

    print(f"\n📊 Found {len(posts)} posts to process\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for idx, post in enumerate(posts, 1):
        post_id = post['id']
        account_id = post['account_id']
        instagram_id = post['instagram_id']
        short_code = post['short_code']

        print(f"[{idx}/{len(posts)}] Processing {short_code}...")

        # Check if already re-hosted
        if post['display_url'] and 'supabase' in post['display_url']:
            print(f"  ⏭️  Already re-hosted")
            skip_count += 1
            continue

        # Download and upload display image
        new_display_url = None
        if post['display_url']:
            storage_path = f"instagram/{account_id}/{instagram_id}_display.jpg"
            print(f"  📥 Downloading display image...")
            new_display_url = download_and_upload_image(post['display_url'], storage_path)

            if new_display_url:
                print(f"  ✅ Uploaded to Supabase")

        # Download and upload carousel images
        new_media_urls = []
        if post['media_urls']:
            try:
                media_urls = json.loads(post['media_urls']) if isinstance(post['media_urls'], str) else post['media_urls']

                if media_urls and len(media_urls) > 0:
                    print(f"  📥 Downloading {len(media_urls)} carousel images...")

                    for i, media_url in enumerate(media_urls):
                        storage_path = f"instagram/{account_id}/{instagram_id}_carousel_{i}.jpg"
                        uploaded_url = download_and_upload_image(media_url, storage_path)

                        if uploaded_url:
                            new_media_urls.append(uploaded_url)

                    print(f"  ✅ Uploaded {len(new_media_urls)}/{len(media_urls)} carousel images")
            except Exception as e:
                print(f"  ⚠️  Carousel processing failed: {e}")

        # Update database
        if new_display_url:
            update_data = {'display_url': new_display_url}

            if new_media_urls:
                update_data['media_urls'] = json.dumps(new_media_urls)

            supabase.table('instagram_posts').update(update_data).eq('id', post_id).execute()
            success_count += 1
            print(f"  💾 Updated database")
        else:
            fail_count += 1
            print(f"  ❌ Failed to process")

        # Rate limiting
        sleep(0.5)
        print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Success: {success_count}")
    print(f"⏭️  Skipped: {skip_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📊 Total: {len(posts)}")
    print("\n✅ All images re-hosted to Supabase storage!")

if __name__ == "__main__":
    main()
