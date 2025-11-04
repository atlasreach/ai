#!/usr/bin/env python3
"""
Caption and Rank Images with Grok Vision API
Sends images to Grok for captioning and quality scoring in parallel batches.
"""

import os
import sys
import json
import base64
import asyncio
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

# Configuration
TEST_MODE = False  # Set to False to process all images
TEST_IMAGE_COUNT = 3  # Number of images to test with
PARALLEL_WORKERS = 3  # Number of parallel API calls
MODEL = "grok-2-vision-1212"  # Grok vision model

def encode_image_base64(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_caption_prompt() -> str:
    """Generate the captioning prompt for Grok."""
    return """You are an expert at creating training captions for AI image models (LoRA training).

Analyze this image and create a detailed training caption following this EXACT format:

Milan, [skin tone], [hair color and style], [facial features], [clothing description], [pose/action], [expression], [camera angle], [background/location], [lighting], sfw

IMPORTANT GUIDELINES:
1. Start with "Milan" as the trigger word
2. Be specific about pose (standing, sitting, lying, walking, etc.)
3. Note camera angle (front view, side view, back view, 3/4 view, close-up, full body)
4. Describe bikini details (color, style - two-piece, one-piece, triangle top, etc.)
5. Mention lighting quality (natural light, studio lighting, golden hour, soft light, etc.)
6. Describe background (beach, pool, studio, outdoor, tropical, etc.)
7. Note expression (smiling, serious, playful, confident, etc.)
8. Keep it concise but detailed (one line)
9. End with "sfw" for bikini images

ALSO provide a quality score (0-100) based on:
- Image sharpness and clarity (30 points)
- Lighting quality (20 points)
- Pose variety and appeal (20 points)
- Face visibility and expression (15 points)
- Composition and framing (15 points)

Return your response in this JSON format:
{
  "caption": "Milan, tan skin, long blonde hair, ... sfw",
  "score": 85,
  "reasoning": "Brief explanation of score"
}"""

def caption_image_with_grok(image_path: str, image_name: str) -> Dict:
    """Send single image to Grok for captioning and scoring."""
    try:
        print(f"  📸 Processing: {image_name}")

        # Encode image
        image_base64 = encode_image_base64(image_path)

        # Prepare API request
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

        # Make API call
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        # Parse response
        result = response.json()
        content = result['choices'][0]['message']['content']

        # Try to parse as JSON
        try:
            # Extract JSON from markdown code blocks if present
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
            # Fallback: treat as plain text caption
            print(f"  ⚠️  Could not parse JSON, using plain text for {image_name}")
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
    """Process a batch of images sequentially (called by parallel workers)."""
    print(f"\n🔄 Worker {batch_num} starting ({len(images)} images)...")
    results = []

    for image_path, image_name in images:
        result = caption_image_with_grok(image_path, image_name)
        results.append(result)

    print(f"✅ Worker {batch_num} complete!")
    return results

def save_captions(results: List[Dict], output_dir: Path):
    """Save captions as .txt files alongside images."""
    print(f"\n💾 Saving caption files...")
    saved = 0

    for result in results:
        if result['success'] and result['caption']:
            # Save caption as .txt file
            image_name = result['image']
            caption_file = output_dir / f"{Path(image_name).stem}.txt"

            with open(caption_file, 'w') as f:
                f.write(result['caption'])

            saved += 1

    print(f"✅ Saved {saved} caption files")

def save_ranking(results: List[Dict], output_file: Path):
    """Save ranked results to JSON file."""
    # Sort by score (descending)
    ranked = sorted(results, key=lambda x: x['score'], reverse=True)

    with open(output_file, 'w') as f:
        json.dump(ranked, f, indent=2)

    print(f"✅ Saved ranking to: {output_file}")

def print_summary(results: List[Dict]):
    """Print summary of results."""
    # Sort by score
    ranked = sorted(results, key=lambda x: x['score'], reverse=True)

    print("\n" + "="*80)
    print("📊 RESULTS SUMMARY")
    print("="*80)

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\n✅ Successfully processed: {len(successful)}/{len(results)}")
    if failed:
        print(f"❌ Failed: {len(failed)}")

    # Show top results
    print(f"\n🏆 RANKED IMAGES (by quality score):\n")
    print(f"{'Rank':<6} {'Score':<8} {'Image':<40} {'Caption Preview'}")
    print("-" * 120)

    for i, result in enumerate(ranked, 1):
        caption_preview = result['caption'][:60] + "..." if len(result['caption']) > 60 else result['caption']
        score_display = f"{result['score']}/100" if result['score'] > 0 else "N/A"
        print(f"{i:<6} {score_display:<8} {result['image']:<40} {caption_preview}")

    # Show score distribution
    scores = [r['score'] for r in successful if r['score'] > 0]
    if scores:
        print(f"\n📈 Score Distribution:")
        print(f"   Average: {sum(scores)/len(scores):.1f}")
        print(f"   Highest: {max(scores)}")
        print(f"   Lowest: {min(scores)}")

def main():
    """Main function."""
    print("🎨 Milan Bikini Caption & Ranking Tool")
    print("="*80)

    # Setup paths
    bikini_dir = Path("/workspaces/ai/models_2.0/milan/bikini")
    output_dir = bikini_dir
    ranking_file = bikini_dir.parent / "bikini_ranking.json"

    # Get all images
    all_images = sorted([f for f in bikini_dir.glob("*.jpg")])

    if not all_images:
        print("❌ No images found in bikini directory!")
        return

    # Apply test mode filter
    if TEST_MODE:
        images = all_images[:TEST_IMAGE_COUNT]
        print(f"🧪 TEST MODE: Processing {len(images)}/{len(all_images)} images")
        print(f"   Set TEST_MODE = False to process all images\n")
    else:
        images = all_images
        print(f"🚀 FULL MODE: Processing all {len(images)} images\n")

    # Prepare batches for parallel processing
    batch_size = max(1, len(images) // PARALLEL_WORKERS)
    remainder = len(images) % PARALLEL_WORKERS

    batches = []
    start_idx = 0

    for i in range(min(PARALLEL_WORKERS, len(images))):
        # Distribute remainder across first batches
        current_batch_size = batch_size + (1 if i < remainder else 0)
        end_idx = start_idx + current_batch_size

        if start_idx < len(images):
            batch = [(str(img), img.name) for img in images[start_idx:end_idx]]
            batches.append(batch)
            start_idx = end_idx

    # Print batch info
    print(f"📦 Created {len(batches)} batches:")
    for i, batch in enumerate(batches, 1):
        print(f"   Batch {i}: {len(batch)} images")

    # Process batches in parallel
    print(f"\n🚀 Starting parallel processing with {len(batches)} workers...")

    with ThreadPoolExecutor(max_workers=len(batches)) as executor:
        futures = [executor.submit(process_batch, batch, i+1) for i, batch in enumerate(batches)]
        all_results = []

        for future in futures:
            all_results.extend(future.result())

    # Save results
    save_captions(all_results, output_dir)
    save_ranking(all_results, ranking_file)

    # Print summary
    print_summary(all_results)

    print("\n" + "="*80)
    print("✅ COMPLETE!")
    print("="*80)
    print(f"\n📁 Caption files saved to: {output_dir}")
    print(f"📁 Ranking saved to: {ranking_file}")
    print(f"\n💡 Next steps:")
    print(f"   1. Review the ranked images above")
    print(f"   2. Check caption quality in the .txt files")
    print(f"   3. If happy, set TEST_MODE = False and re-run for all images")
    print(f"   4. Use top 20-60 images for LoRA training")

if __name__ == "__main__":
    if not GROK_API_KEY:
        print("❌ Error: GROK_API_KEY not found in .env file")
        sys.exit(1)

    main()
