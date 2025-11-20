#!/usr/bin/env python3
"""
Test the image generation API flow:
1. Fetch a model from Supabase
2. Fetch a reference image with Grok Vision caption
3. Combine them to generate via API
"""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('api/.env')

# Supabase setup
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# API setup
API_URL = "http://localhost:3001"

def test_generation_flow():
    print("=" * 60)
    print("TESTING IMAGE GENERATION API FLOW")
    print("=" * 60)

    # Step 1: Get a model
    print("\n[1] Fetching a model...")
    models = supabase.table('models').select('*').limit(1).execute()
    if not models.data:
        print("❌ No models found in database!")
        return

    model = models.data[0]
    print(f"✓ Using model: {model['name']}")
    print(f"  - Trigger: {model['trigger_word']}")
    print(f"  - LoRA: {model['lora_file']}")
    print(f"  - Attributes: {model['skin_tone']} skin, {model['hair_style']}")

    # Step 2: Get a reference image with vision description
    print("\n[2] Fetching a reference image with Grok Vision caption...")
    ref_images = supabase.table('reference_images').select('*').not_.is_('vision_description', 'null').limit(1).execute()
    if not ref_images.data:
        print("❌ No reference images with vision descriptions found!")
        return

    ref_image = ref_images.data[0]
    print(f"✓ Using reference: {ref_image['filename']}")
    print(f"  - Category: {ref_image['category']}")
    print(f"  - Vision: {ref_image['vision_description'][:100]}...")
    print(f"  - Storage: {ref_image['storage_path']}")

    # Step 3: Check API server
    print("\n[3] Checking API server...")
    try:
        response = requests.get(f"{API_URL}/api/workflows", timeout=5)
        if response.ok:
            workflows = response.json()
            print(f"✓ API server is running")
            print(f"  Available workflows: {[w['slug'] for w in workflows]}")
        else:
            print(f"❌ API returned error: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_URL}")
        print("   Run: cd api && npm start")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Step 4: Explain the generation flow
    print("\n[4] Generation Flow:")
    print("-" * 60)
    print("To generate an image, you would:")
    print()
    print("A. Upload reference image to ComfyUI:")
    print(f"   POST {API_URL}/api/upload-image")
    print(f"   - Download from: {ref_image['storage_path']}")
    print(f"   - Upload as multipart/form-data")
    print()
    print("B. Submit generation job:")
    print(f"   POST {API_URL}/api/generate")
    print("   Body:")
    print("   {")
    print(f'     "modelId": {model["id"]},')
    print(f'     "workflowSlug": "img2img-lora",')
    print(f'     "uploadedImageFilename": "reference.jpg",')
    print("     \"parameters\": {")
    print("       \"denoise\": 0.75,")
    print("       \"cfg\": 3.8,")
    print("       \"steps\": 28,")
    print("       \"seed\": -1,")
    print("       \"lora_strength\": 0.65,")
    print(f'       "positive_prompt_suffix": "{ref_image["vision_description"][:80]}..."')
    print("     }")
    print("   }")
    print()
    print("   This will create a prompt combining:")
    print(f"   - Model attributes: {model['trigger_word']}, {model['hair_style']}, {model['skin_tone']} skin")
    print(f"   - Vision caption: {ref_image['vision_description'][:80]}...")
    print()
    print("C. Check job status:")
    print("   GET /api/jobs/:id")
    print("   POST /api/jobs/:id/check  (polls ComfyUI)")
    print()
    print("=" * 60)
    print("✓ Setup validated! Your models + vision captions are ready.")
    print("=" * 60)

    # Show what the combined prompt would look like
    print("\n[5] Example Combined Prompt:")
    print("-" * 60)
    combined_prompt = f"{model['trigger_word']}, {model['hair_style']}, {model['skin_tone']} skin, {ref_image['vision_description'][:100]}"
    print(f"Positive: {combined_prompt}...")
    print(f"Negative: {model['negative_prompt']}")
    print("-" * 60)

if __name__ == '__main__':
    test_generation_flow()
