#!/usr/bin/env python3
"""
Test Grok caption generation
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.grok_service import GrokService

async def test_caption_generation():
    """Test image caption generation"""
    print("🧪 Testing Grok caption generation...\n")

    # Test 1: Image caption generation
    print("Test 1: Generate caption from image URL")
    test_image = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400"
    test_prompt = """Generate a natural language caption for this image.
Keep it concise (1-2 sentences) and describe what you see.
Format: Just the caption text, no extra formatting."""

    try:
        grok_service = GrokService()
        caption = await grok_service.generate_caption_from_url(test_image, test_prompt)
        print(f"✅ Caption generated: {caption}\n")
    except Exception as e:
        print(f"❌ Caption generation failed: {e}\n")
        return False

    # Test 2: Text-based prompt generation
    print("Test 2: Generate validation prompts from captions")
    validation_prompt = """Based on these captions, generate 3 test prompts in JSON format:
- "a woman in a blue dress standing outdoors"
- "a professional portrait with studio lighting"

Format: ["prompt 1", "prompt 2", "prompt 3"]"""

    try:
        validation_prompts_json = await grok_service.generate_text_completion(validation_prompt)
        print(f"✅ Validation prompts generated: {validation_prompts_json}\n")
    except Exception as e:
        print(f"❌ Validation prompt generation failed: {e}\n")
        return False

    print("✅ All Grok tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_caption_generation())
    sys.exit(0 if success else 1)
