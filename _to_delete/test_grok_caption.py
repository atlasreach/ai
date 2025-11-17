#!/usr/bin/env python3
"""
Test Grok caption generation
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.grok_service import GrokService
from dotenv import load_dotenv

load_dotenv()

def test_grok_caption():
    print("🧪 Testing Grok Caption Generation")
    print("=" * 50)

    # Test image URL (using one that we know exists)
    test_image_url = "https://yiriqesejsbzmzxdxiqt.supabase.co/storage/v1/object/public/training-images/c7154011-9b83-4a30-99db-7acbdba89123/1763193506941_0.jpg"

    # Build test prompt
    test_prompt = """Generate a training caption for this image.

CAPTION STRUCTURE: testchar, a woman with blonde hair, blue eyes, [describe pose, clothing, setting, expression]

REQUIRED ELEMENTS:
- Trigger word: "testchar" (MUST be first word)
- Character constants: blonde hair, blue eyes
- VARIABLE elements: Describe what you see - pose, clothing, setting, facial expression

RULES:
- Start with trigger word
- Include ALL character constants
- Describe visible variable elements accurately
- Keep it concise (one sentence)
- No hashtags, no explanations

Example: "testchar, a woman with blonde hair, blue eyes, wearing a white dress, standing in a garden, smiling at camera"
"""

    print(f"\n📸 Test image: {test_image_url[:80]}...")
    print(f"\n📝 Prompt length: {len(test_prompt)} chars")

    try:
        print("\n🤖 Calling Grok AI...")
        import asyncio
        caption = asyncio.run(GrokService.generate_caption_from_url(test_image_url, test_prompt))

        print(f"\n✅ Caption generated successfully!")
        print(f"📄 Caption: {caption}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_grok_caption()
    exit(0 if success else 1)
