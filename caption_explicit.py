#!/usr/bin/env python3
"""Caption and Rank Explicit/Sex Images"""

import os
import sys
import json
import base64
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import requests

load_dotenv()
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

# Configuration
TEST_MODE = False
TEST_IMAGE_COUNT = 3
PARALLEL_WORKERS = 3
MODEL = "grok-2-vision-1212"

def encode_image_base64(image_path: str) -> str:
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_caption_prompt() -> str:
    return """You are an expert at creating training captions for AI image models (LoRA training).

Analyze this EXPLICIT/SEX image and create a VERY DETAILED training caption following this EXACT format:

Milan, [skin tone], [hair color and style], [facial features], nude, [body features], [detailed sex act/position], [body position details], [what hands are doing], [partner if visible], [detailed expression], [eye contact/gaze], [mouth position], [camera angle], [background], [lighting], nsfw

IMPORTANT GUIDELINES - BE VERY DETAILED:

1. Start with "Milan" as the trigger word, always include "nude"

2. BODY FEATURES:
   - Breasts visible, breast size, nipples visible
   - Pussy visible, pussy spread, legs spread wide
   - Ass visible, ass up, on all fours
   - Body type: curvy, slim, athletic, thick thighs, etc.

3. SEX ACT/POSITION - BE EXPLICIT AND DETAILED:
   - Blowjob: "giving blowjob, cock in mouth, deepthroating, licking cock, sucking dick"
   - Penetration: "having sex, cock inside pussy, being fucked, riding cock, dick inside"
   - Position: "missionary position, doggy style, reverse cowgirl, on top straddling, bent over"
   - Other: "fingering herself, touching pussy, masturbating, lesbian sex, pussy eating"

4. BODY POSITION DETAILS:
   - "on knees between legs"
   - "lying on back with legs spread wide"
   - "bent over on all fours, ass up"
   - "straddling on top, bouncing"
   - "face down ass up"

5. HANDS/ARMS - What are they doing:
   - "hand on cock, stroking"
   - "hands on ass cheeks spreading"
   - "hand on partner's chest"
   - "fingers in pussy"
   - "gripping sheets/bed"

6. PARTNER (if visible):
   - "with man, male partner"
   - "with woman, female partner"
   - "cock visible, penis in frame"
   - Note position relative to Milan

7. FACIAL EXPRESSION - BE VERY SPECIFIC:
   - Pleasure: "moaning in pleasure, ecstasy, face of pleasure, orgasm face"
   - Eyes: "eyes closed in pleasure, looking up at camera, eye contact, looking at partner"
   - Mouth: "mouth open moaning, tongue out, lips wrapped around cock, biting lip"
   - Emotion: "intense pleasure, passionate, lustful, concentrated, enjoying"

8. CAMERA ANGLE:
   - POV (from partner's perspective)
   - Close-up (focus on face/action)
   - Side view, back view, 3/4 view
   - Low angle, high angle

9. Background & Lighting

10. Keep DETAILED but in one line - don't hold back on explicit details!

11. End with "nsfw"

ALSO provide a quality score (0-100) based on:
- Image sharpness and clarity (30 points)
- Lighting quality (20 points)
- Pose/action clarity (20 points)
- Face visibility and expression (15 points)
- Composition and framing (15 points)

Return your response in this JSON format:
{
  "caption": "Milan, tan skin, long dark hair, nude, ... nsfw",
  "score": 85,
  "reasoning": "Brief explanation of score"
}"""

def caption_image_with_grok(image_path: str, image_name: str) -> Dict:
    try:
        print(f"  📸 Processing: {image_name}")
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
            "max_tokens": 500
        }

        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        content = result['choices'][0]['message']['content']

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            return {
                "image": image_name,
                "path": image_path,
                "caption": data.get("caption", ""),
                "score": data.get("score", 0),
                "reasoning": data.get("reasoning", ""),
                "success": True
            }
        except json.JSONDecodeError:
            print(f"  ⚠️  Could not parse JSON for {image_name}")
            return {
                "image": image_name,
                "path": image_path,
                "caption": content.strip(),
                "score": 0,
                "reasoning": "JSON parsing failed",
                "success": True
            }

    except Exception as e:
        print(f"  ❌ Error processing {image_name}: {str(e)}")
        return {
            "image": image_name,
            "path": image_path,
            "caption": "",
            "score": 0,
            "reasoning": f"Error: {str(e)}",
            "success": False
        }

def process_batch(images: List[Tuple[str, str]], batch_num: int) -> List[Dict]:
    print(f"\n🔄 Worker {batch_num} starting ({len(images)} images)...")
    results = []
    for image_path, image_name in images:
        result = caption_image_with_grok(image_path, image_name)
        results.append(result)
    print(f"✅ Worker {batch_num} complete!")
    return results

def save_captions(results: List[Dict], output_dir: Path):
    print(f"\n💾 Saving caption files...")
    saved = 0
    for result in results:
        if result['success'] and result['caption']:
            image_name = result['image']
            caption_file = output_dir / f"{Path(image_name).stem}.txt"
            with open(caption_file, 'w') as f:
                f.write(result['caption'])
            saved += 1
    print(f"✅ Saved {saved} caption files")

def save_ranking(results: List[Dict], output_file: Path):
    ranked = sorted(results, key=lambda x: x['score'], reverse=True)
    with open(output_file, 'w') as f:
        json.dump(ranked, f, indent=2)
    print(f"✅ Saved ranking to: {output_file}")

def print_summary(results: List[Dict], category: str):
    ranked = sorted(results, key=lambda x: x['score'], reverse=True)
    print("\n" + "="*80)
    print(f"📊 {category.upper()} RESULTS")
    print("="*80)

    successful = [r for r in results if r['success']]
    print(f"\n✅ Successfully processed: {len(successful)}/{len(results)}")

    print(f"\n🏆 TOP RANKED:\n")
    for i, result in enumerate(ranked[:10], 1):
        caption_preview = result['caption'][:60] + "..." if len(result['caption']) > 60 else result['caption']
        score_display = f"{result['score']}/100" if result['score'] > 0 else "N/A"
        print(f"{i}. [{score_display}] {result['image']}")
        print(f"   {caption_preview}")

def main():
    print("🔞 EXPLICIT/SEX Caption Tool")
    print("="*80)

    image_dir = Path("/workspaces/ai/models_2.0/milan/explicit")
    ranking_file = image_dir.parent / "explicit_ranking.json"

    all_images = sorted([f for f in image_dir.glob("milan_explicit_*")])
    if not all_images:
        print("❌ No images found!")
        return

    images = all_images[:TEST_IMAGE_COUNT] if TEST_MODE else all_images
    mode_text = f"🧪 TEST MODE: {len(images)}/{len(all_images)}" if TEST_MODE else f"🚀 FULL MODE: {len(images)}"
    print(f"{mode_text} images\n")

    batch_size = max(1, len(images) // PARALLEL_WORKERS)
    batches = []
    start_idx = 0

    for i in range(min(PARALLEL_WORKERS, len(images))):
        end_idx = min(start_idx + batch_size + (1 if i < len(images) % PARALLEL_WORKERS else 0), len(images))
        if start_idx < len(images):
            batch = [(str(img), img.name) for img in images[start_idx:end_idx]]
            batches.append(batch)
            start_idx = end_idx

    print(f"🚀 Processing with {len(batches)} workers...")
    with ThreadPoolExecutor(max_workers=len(batches)) as executor:
        futures = [executor.submit(process_batch, batch, i+1) for i, batch in enumerate(batches)]
        all_results = []
        for future in futures:
            all_results.extend(future.result())

    save_captions(all_results, image_dir)
    save_ranking(all_results, ranking_file)
    print_summary(all_results, "EXPLICIT")

    print("\n" + "="*80)
    print("✅ COMPLETE!")
    print(f"📁 Captions: {image_dir}")
    print(f"📁 Ranking: {ranking_file}")

if __name__ == "__main__":
    if not GROK_API_KEY:
        print("❌ Error: GROK_API_KEY not found")
        sys.exit(1)
    main()
