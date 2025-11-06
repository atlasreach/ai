#!/usr/bin/env python3
"""Test Caption Generation for Sofia - 2 Images Only"""

import os
import sys
import json
import base64
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-2-vision-1212"

def encode_image_base64(image_path: str) -> str:
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_caption_prompt() -> str:
    return """You are an expert at creating training captions for AI image models (LoRA training).

Analyze this NSFW image and create a detailed training caption following this EXACT format:

Sofia, [skin tone], [hair color and style], [facial features], [clothing/nude status], [body features], [pose/action], [body orientation], [expression - REQUIRED!], [camera angle], [background/location], [lighting], [sfw/nsfw]

IMPORTANT GUIDELINES:
1. Start with "Sofia" as the trigger word
2. CLOTHING/NUDE - Be specific:
   - nude, topless, wearing [specific clothing items], white thong, lace bra, etc.
   - What's visible: full body, breasts visible, pussy visible, ass visible, etc.
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
   - neutral expression, smiling, playful smile, naughty grin, seductive look, sultry expression
   - Biting lip, mouth open, eyes closed, looking at camera, shy look, head straight
   - Confident, inviting, teasing, innocent look, bedroom eyes
8. Camera angle: front view, back view, side view, side profile, 3/4 view, POV, low angle, close-up, full body
9. Background & lighting: modern bedroom, green wall, gray curtains, soft overhead lighting, natural light, etc.
10. Keep detailed but on one line
11. Add quality tags: masterpiece, best quality, photorealistic, 8k
12. End with "nsfw" or "sfw" depending on content

Return your response in this JSON format:
{
  "caption": "Sofia, tan skin, long straight brown hair, small breasts, toned abs, ... masterpiece, best quality, photorealistic, 8k, nsfw",
  "score": 85,
  "reasoning": "Brief explanation of quality"
}"""

def caption_image_with_grok(image_path: str, image_name: str):
    try:
        print(f"\n📸 Processing: {image_name}")
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

        print(f"   🔄 Sending to Grok API...")
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        content = result['choices'][0]['message']['content']

        # Parse JSON response
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            print(f"   ✅ Success!")
            print(f"   📝 Caption: {data.get('caption', '')[:100]}...")
            print(f"   ⭐ Score: {data.get('score', 0)}/100")
            print(f"   💭 Reasoning: {data.get('reasoning', '')}")

            return {
                "image": image_name,
                "caption": data.get("caption", ""),
                "score": data.get("score", 0),
                "reasoning": data.get("reasoning", ""),
                "success": True
            }
        except json.JSONDecodeError:
            print(f"   ⚠️  Could not parse JSON, raw response:")
            print(f"   {content}")
            return {
                "image": image_name,
                "caption": content.strip(),
                "score": 0,
                "reasoning": "JSON parsing failed",
                "success": True
            }

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {
            "image": image_name,
            "caption": "",
            "score": 0,
            "reasoning": f"Error: {str(e)}",
            "success": False
        }

def main():
    print("="*80)
    print("🧪 SOFIA CAPTION TEST - 2 Images")
    print("="*80)

    if not GROK_API_KEY:
        print("❌ Error: GROK_API_KEY not found in environment")
        print("Please set it: export GROK_API_KEY='your-key-here'")
        sys.exit(1)

    image_dir = Path("/workspaces/ai/models/Sofia/targets/nsfw")

    # Get first 2 images
    all_images = sorted(image_dir.glob("*.jpg"))
    test_images = all_images[:2]

    if not test_images:
        print("❌ No images found!")
        return

    print(f"\n📁 Processing {len(test_images)} images from: {image_dir}\n")

    results = []
    for img_path in test_images:
        result = caption_image_with_grok(str(img_path), img_path.name)
        results.append(result)

    # Print summary
    print("\n" + "="*80)
    print("📊 RESULTS SUMMARY")
    print("="*80)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['image']}")
        if result['success'] and result['caption']:
            print(f"   Caption: {result['caption']}")
            print(f"   Score: {result['score']}/100")
        else:
            print(f"   ❌ Failed: {result['reasoning']}")

    print("\n" + "="*80)
    print("✅ TEST COMPLETE!")
    print("="*80)

if __name__ == "__main__":
    main()
