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
    """
    print("=" * 70)
    print("🎨 FULL GENERATION TEST - End to End")
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
        print(f"\n🚀 Starting generation...")
        print(f"   Prompt additions: 'professional photo, smiling, elegant pose'")

        result = await service.generate(
            character=test_character,
            workflow_path="workflows/qwen/instagram_single.json",
            input_image_filename="22.jpg",  # Uploaded test image
            prompt_additions="professional photo, smiling, elegant pose"
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

async def test_with_status_polling():
    """
    Test job submission and manual status polling
    """
    print("\n" + "=" * 70)
    print("🔄 STATUS POLLING TEST - Submit and Check Status Manually")
    print("=" * 70)

    service = ComfyUIService()

    # Minimal test
    test_character = {
        "trigger_word": "milan",
        "lora_file": "milan_000002000.safetensors",
        "lora_strength": 0.8,
        "character_constraints": {"constants": []}
    }

    try:
        # Load and prepare workflow
        print("\n1️⃣  Loading workflow...")
        workflow = service.load_workflow("workflows/qwen/instagram_single.json")

        print("2️⃣  Injecting parameters...")
        workflow = service.inject_lora(workflow, test_character["lora_file"], test_character["lora_strength"])
        workflow = service.inject_input_image(workflow, "22.jpg")

        prompt = "milan, woman with blonde hair, professional photo"
        workflow = service.inject_prompt(workflow, prompt)

        print("3️⃣  Submitting to ComfyUI...")
        submit_result = await service.submit_prompt(workflow)

        if not submit_result["success"]:
            print(f"❌ Submit failed: {submit_result.get('error')}")
            return False

        prompt_id = submit_result["prompt_id"]
        print(f"✅ Submitted! Prompt ID: {prompt_id}")

        print("\n4️⃣  Polling for completion...")
        poll_result = await service.poll_for_completion(prompt_id, timeout=300)

        if poll_result["success"]:
            print(f"\n✅ Completed!")
            print(f"   Status: {poll_result['status']}")
            print(f"   Processing Time: {poll_result.get('processing_time', 0):.1f}s")
            print(f"   Output Images: {len(poll_result.get('output_images', []))}")

            for img_info in poll_result.get('output_images', []):
                url = service.get_image_url(img_info)
                print(f"   Image URL: {url}")

            return True
        else:
            print(f"\n❌ Failed: {poll_result.get('error')}")
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

    # Test 1: Full generation
    test1_result = await test_full_generation()

    # Test 2: Manual status polling
    test2_result = await test_with_status_polling()

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
