#!/usr/bin/env python3
"""
Analyze reference images with Grok Vision API and save descriptions to database
"""
import os
import sys
import requests
import psycopg2
import base64
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Configuration
GROK_API_KEY = os.getenv('GROK_API_KEY')
CATEGORY = "bikini-mirror-pics"

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Database
conn = psycopg2.connect(
    host=os.getenv('host'),
    port=int(os.getenv('port')),
    dbname=os.getenv('dbname'),
    user=os.getenv('user'),
    password=os.getenv('password')
)
cur = conn.cursor()

def analyze_with_grok(image_url):
    """Use Grok Vision API to describe the bikini reference image"""
    # Download image
    response = requests.get(image_url)
    if response.status_code != 200:
        return None

    # Encode to base64
    image_data = base64.b64encode(response.content).decode('utf-8')

    # Call Grok Vision API
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
                        'text': '''Describe this photo for AI image generation. Focus on:
- Bikini style, color, pattern
- Pose (mirror selfie, holding phone, etc.)
- Setting/background (bathroom, bedroom, etc.)
- Lighting and mood
- Any accessories

Format: Short, comma-separated tags suitable for Stable Diffusion prompt.
DO NOT mention the person's hair color, skin tone, or face - only describe the pose, outfit, and setting.'''
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_data}'
                        }
                    }
                ]
            }],
            'max_tokens': 200,
            'temperature': 0.5
        }
    )

    if grok_response.status_code == 200:
        description = grok_response.json()['choices'][0]['message']['content'].strip()
        return description
    else:
        print(f"    ✗ Grok API error: {grok_response.status_code} - {grok_response.text}")
        return None

def test_prompt_combining(vision_description):
    """Test prompt combining with Milan model"""
    cur.execute("SELECT name, hair_style, skin_tone, trigger_word, negative_prompt FROM models WHERE slug = 'milan'")
    model = cur.fetchone()

    if not model:
        return None, None

    name, hair_style, skin_tone, trigger_word, negative_prompt = model

    # Build combined prompt
    prompt = f"{trigger_word}, {hair_style}, {skin_tone} skin, beautiful woman, {vision_description}, professional photo, detailed face, 8k, high quality"
    negative = f"{negative_prompt}, blurry, deformed, bad anatomy, low quality, worst quality"

    return prompt, negative

def main():
    # Get limit from command line (default 3 for testing)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    print("=" * 80)
    print("GROK VISION API ANALYSIS")
    print("=" * 80)

    # List files in category folder
    print(f"\n📁 Loading images from: reference-images/{CATEGORY}/")
    try:
        files = supabase.storage.from_('reference-images').list(CATEGORY)
    except:
        print("✗ Category folder not found. Run reorganize_storage.py first")
        return

    if not files:
        print("✗ No images found")
        return

    print(f"✓ Found {len(files)} images")

    # Limit for testing
    files = files[:limit]
    print(f"\n🔍 Analyzing {len(files)} images...\n")

    for idx, file in enumerate(files, 1):
        filename = file['name']
        storage_path = f"{CATEGORY}/{filename}"
        image_url = supabase.storage.from_('reference-images').get_public_url(storage_path)

        print(f"[{idx}/{len(files)}] {filename[:60]}")
        print(f"  URL: {image_url[:70]}...")

        # Check if already analyzed
        cur.execute(
            "SELECT id, vision_description FROM reference_images WHERE filename = %s AND category = %s",
            (filename, CATEGORY)
        )
        existing = cur.fetchone()

        if existing and existing[1]:
            print(f"  ✓ Already analyzed")
            print(f"  Description: {existing[1][:80]}...")

            # Test prompt combining
            prompt, negative = test_prompt_combining(existing[1])
            if prompt:
                print(f"  📝 Combined prompt: {prompt[:100]}...")
            print()
            continue

        # Analyze with Grok
        print(f"  🔍 Analyzing with Grok Vision API...")
        vision_description = analyze_with_grok(image_url)

        if not vision_description:
            print(f"  ✗ Analysis failed\n")
            continue

        print(f"  ✓ Description: {vision_description[:80]}...")

        # Test prompt combining
        prompt, negative = test_prompt_combining(vision_description)
        if prompt:
            print(f"  📝 Combined prompt: {prompt[:100]}...")

        # Save to database
        if existing:
            cur.execute(
                "UPDATE reference_images SET vision_description = %s, analyzed_at = NOW() WHERE id = %s",
                (vision_description, existing[0])
            )
        else:
            cur.execute(
                "INSERT INTO reference_images (filename, category, storage_path, vision_description, analyzed_at) VALUES (%s, %s, %s, %s, NOW())",
                (filename, CATEGORY, storage_path, vision_description)
            )

        conn.commit()
        print(f"  ✓ Saved to database\n")

    print("=" * 80)
    print(f"✓ ANALYSIS COMPLETE")
    print(f"  Analyzed: {len(files)} images")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    finally:
        cur.close()
        conn.close()
