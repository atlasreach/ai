#!/usr/bin/env python3
"""Generate Captions for All Sofia Images"""

import os
import sys
import json
import base64
from pathlib import Path
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-2-vision-1212"
PARALLEL_WORKERS = 3

def encode_image_base64(image_path: str) -> str:
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_caption_prompt() -> str:
    return """You are an expert at creating training captions for AI image models (LoRA training).

Analyze this image and create a detailed training caption following this EXACT format:

Sofia, [skin tone], [hair color and style], [facial features], [clothing/nude status], [body features], [pose/action], [body orientation], [expression], [camera angle], [background/location], [lighting]

IMPORTANT GUIDELINES:
1. Start with "Sofia" as the trigger word
2. CLOTHING/NUDE - Be specific:
   - nude, topless, wearing [specific clothing items], white thong, lace bra, bikini, etc.
   - What's visible: full body, breasts visible, etc.
3. BODY FEATURES - Be specific:
   - Breasts: small breasts, medium breasts, large breasts, perky breasts, natural breasts
   - Body type: athletic, curvy, slim, toned, thick thighs, wide hips, flat stomach, toned abs, etc.
4. BODY ORIENTATION - Where is her body facing vs head:
   - "standing sideways, head turned to camera"
   - "ass facing camera, looking back over shoulder"
   - "lying on back, legs spread"
   - "bent over showing ass, head turned"
5. Pose: standing, sitting, lying down, kneeling, on bed, legs spread, bent over, arched back, etc.
6. Hand/arm position: hands on hips, left hand on headboard, right hand hanging, covering breasts, arms raised, etc.
7. EXPRESSION - ALWAYS INCLUDE:
   - neutral expression, smiling, playful smile, seductive look, sultry expression
   - Biting lip, mouth open, looking at camera, shy look, head straight
8. Camera angle: front view, back view, side view, side profile, 3/4 view, POV, low angle, close-up, full body
9. Background & lighting: modern bedroom, green wall, soft overhead lighting, natural light, beach, etc.
10. Keep detailed but on one line
11. DO NOT include quality tags or content ratings

Return ONLY the caption text, no JSON, no extra formatting."""

def caption_image_with_grok(image_path: str, image_name: str):
    try:
        print(f"  📸 {image_name}...", end=" ", flush=True)
        image_base64 = encode_image_base64(image_path)

        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": get_caption_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }

        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        caption = result['choices'][0]['message']['content'].strip()

        # Clean up any JSON formatting if present
        if "```" in caption:
            caption = caption.split("```")[1].strip() if caption.count("```") > 1 else caption

        # Remove quotes if wrapped
        caption = caption.strip('"\'')

        print(f"✅")
        return {
            "image": image_name,
            "path": image_path,
            "caption": caption,
            "success": True
        }

    except Exception as e:
        print(f"❌ {str(e)}")
        return {
            "image": image_name,
            "path": image_path,
            "caption": "",
            "success": False,
            "error": str(e)
        }

def process_batch(images, batch_num):
    results = []
    for image_path, image_name in images:
        result = caption_image_with_grok(image_path, image_name)
        results.append(result)
    return results

def save_captions(results, output_dir):
    print(f"\n💾 Saving caption files...")
    saved = 0
    for result in results:
        if result['success'] and result['caption']:
            image_name = result['image']
            caption_file = output_dir / f"{Path(image_name).stem}.txt"
            with open(caption_file, 'w') as f:
                f.write(result['caption'])
            saved += 1
    print(f"✅ Saved {saved}/{len(results)} caption files")
    return saved

def main():
    print("="*80)
    print("🎨 SOFIA CAPTION GENERATION - All Images")
    print("="*80)

    if not GROK_API_KEY:
        print("❌ Error: GROK_API_KEY not found")
        sys.exit(1)

    image_dir = Path("/workspaces/ai/models/Sofia/targets/nsfw")
    all_images = sorted(image_dir.glob("*.jpg"))

    if not all_images:
        print("❌ No images found!")
        return

    print(f"\n📁 Processing {len(all_images)} images from: {image_dir}")
    print(f"🔄 Using {PARALLEL_WORKERS} parallel workers\n")

    # Split into batches
    batch_size = max(1, len(all_images) // PARALLEL_WORKERS)
    batches = []
    start_idx = 0

    for i in range(min(PARALLEL_WORKERS, len(all_images))):
        end_idx = min(start_idx + batch_size + (1 if i < len(all_images) % PARALLEL_WORKERS else 0), len(all_images))
        if start_idx < len(all_images):
            batch = [(str(img), img.name) for img in all_images[start_idx:end_idx]]
            batches.append(batch)
            start_idx = end_idx

    # Process in parallel
    with ThreadPoolExecutor(max_workers=len(batches)) as executor:
        futures = [executor.submit(process_batch, batch, i+1) for i, batch in enumerate(batches)]
        all_results = []
        for future in futures:
            all_results.extend(future.result())

    # Save captions
    saved = save_captions(all_results, image_dir)

    # Print sample captions
    print(f"\n📝 Sample Captions:")
    print("="*80)
    successful = [r for r in all_results if r['success']][:5]
    for result in successful:
        print(f"\n{result['image']}:")
        print(f"  {result['caption']}")

    print("\n" + "="*80)
    print(f"✅ COMPLETE! {saved}/{len(all_images)} captions generated")
    print(f"📁 Location: {image_dir}")
    print("="*80)

if __name__ == "__main__":
    main()
