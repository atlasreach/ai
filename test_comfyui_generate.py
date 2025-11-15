"""
End-to-End ComfyUI Generation Test
Actually submits a job and generates an image
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.comfyui_service import ComfyUIService

async def test_full_generation():
    """
    Full end-to-end test: Submit job → Poll → Get image
    Using new API-format workflow (only 1 image output)
    """
    print("=" * 70)
    print("🎨 FULL GENERATION TEST - End to End (API Format)")
    print("=" * 70)

    service = ComfyUIService()

    # Test character data (matching Milan)
    test_character = {
        "id": "milan",
        "name": "Milan",
        "trigger_word": "milan",
        "lora_file": "milan_000002000.safetensors",
        "lora_strength": 0.8,
        "character_constraints": {
            "constants": [
                {"key": "hair", "value": "blonde hair", "type": "physical"},
                {"key": "eyes", "value": "blue eyes", "type": "physical"}
            ]
        }
    }

    print(f"\n📋 Configuration:")
    print(f"   Character: {test_character['name']}")
    print(f"   LoRA: {test_character['lora_file']}")
    print(f"   Trigger: {test_character['trigger_word']}")
    print(f"   ComfyUI: {service.api_url}")

    try:
        # Settings from known good output: /workspaces/ai/outputs/milan/20251113_141359/metadata.json
        sampler_overrides = {
            "steps": 30,           # From known good output
            "cfg": 4.0,            # From known good output
            "denoise": 0.85,       # From known good output (strength parameter)
            "seed": 123456         # Reproducible
        }

        # Exact prompt from known good output
        known_good_prompt = "woman with long straight brunette hair, tan skin, fully nude, standing and leaning forward with her upper body resting on a light-colored cushioned chair, back arched, buttocks prominently displayed, left hand resting on the back of the chair, right hand not visible, tongue sticking out playfully, bright and colorful lighting with blue and white tones from the background"

        print(f"\n🚀 Starting generation with KNOWN GOOD settings...")
        print(f"   Using settings from: /workspaces/ai/outputs/milan/20251113_141359/metadata.json")
        print(f"   Workflow: API format (single output)")
        print(f"   Prompt: {known_good_prompt[:80]}...")
        print(f"   Overrides: {sampler_overrides}")

        result = await service.generate(
            character=test_character,
            workflow_path="workflows/qwen/instagram_api_prompt.json",  # New API format workflow
            input_image_filename="22.jpg",  # Uploaded test image
            prompt_additions=known_good_prompt,
            sampler_overrides=sampler_overrides,
            lora_strength_override=0.8  # From known good output
        )

        print("\n" + "=" * 70)
        print("RESULT:")
        print("=" * 70)

        if result["success"]:
            print(f"✅ SUCCESS!")
            print(f"\n📊 Generation Details:")
            print(f"   Prompt ID: {result.get('prompt_id')}")
            print(f"   Processing Time: {result.get('processing_time', 0):.1f}s")
            print(f"   Output Images: {len(result.get('output_images', []))}")

            if result.get("output_url"):
                print(f"\n🖼️  Output URL:")
                print(f"   {result['output_url']}")

            if result.get("output_urls"):
                print(f"\n📸 All Output URLs:")
                for i, url in enumerate(result['output_urls'], 1):
                    print(f"   {i}. {url}")

            print("\n🎉 Image generation completed successfully!")
            return True

        else:
            print(f"❌ FAILED!")
            print(f"   Error: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_with_simple_prompt():
    """
    Test with simpler prompt (no long description)
    """
    print("\n" + "=" * 70)
    print("🔄 SIMPLE PROMPT TEST - Quick Generation")
    print("=" * 70)

    service = ComfyUIService()

    # Minimal test character
    test_character = {
        "id": "milan",
        "name": "Milan",
        "trigger_word": "milan",
        "lora_file": "milan_000002000.safetensors",
        "lora_strength": 0.8,
        "character_constraints": {
            "constants": [
                {"key": "hair", "value": "blonde hair", "type": "physical"},
                {"key": "eyes", "value": "blue eyes", "type": "physical"}
            ]
        }
    }

    try:
        # Simpler settings for faster test
        sampler_overrides = {
            "steps": 20,           # Fewer steps for speed
            "cfg": 4.0,
            "denoise": 0.85,
            "seed": 789
        }

        print("\n🚀 Starting simple generation...")
        result = await service.generate(
            character=test_character,
            workflow_path="workflows/qwen/instagram_api_prompt.json",
            input_image_filename="22.jpg",
            prompt_additions="professional photo, elegant pose, soft lighting",
            sampler_overrides=sampler_overrides,
            lora_strength_override=0.8
        )

        if result["success"]:
            print(f"\n✅ Completed!")
            print(f"   Processing Time: {result.get('processing_time', 0):.1f}s")
            print(f"   Output Images: {len(result.get('output_images', []))}")
            print(f"   Primary URL: {result.get('output_url')}")
            return True
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run end-to-end tests"""
    print("\n" + "=" * 70)
    print("🧪 ComfyUI End-to-End Generation Test")
    print("=" * 70)

    print("\n⚠️  This will actually generate an image on ComfyUI!")
    print("    Make sure:")
    print("    1. ComfyUI is running at the configured URL")
    print("    2. The LoRA file (milan_000002000.safetensors) exists in ComfyUI's loras/ folder")
    print("    3. The Qwen models are loaded in ComfyUI")

    # Test 1: Full generation with known good settings
    test1_result = await test_full_generation()

    # Test 2: Simple prompt test
    test2_result = await test_with_simple_prompt()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    results = [test1_result, test2_result]
    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All generation tests passed!")
        print("✅ ComfyUI integration is fully working!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        print("Check ComfyUI logs for details")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
