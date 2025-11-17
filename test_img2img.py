#!/usr/bin/env python3
"""
Test img2img workflow with Milan LoRa on RunPod ComfyUI
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.comfyui_service import ComfyUIService

async def test_img2img():
    """Test image-to-image generation with Milan LoRa"""

    # Initialize service with RunPod URL
    service = ComfyUIService(api_url="https://c79vcd863ntrtq-3001.proxy.runpod.net")

    # Create a Milan character config
    milan_character = {
        "id": "milan",
        "name": "Milan",
        "trigger_word": "milan",
        "lora_file": "milan_000002000.safetensors",
        "lora_strength": 0.8,
        "character_constraints": {
            "constants": [
                {"type": "physical", "key": "hair", "value": "blonde hair"},
                {"type": "physical", "key": "eyes", "value": "blue eyes"},
            ]
        }
    }

    print("=" * 60)
    print("Testing Image-to-Image Generation")
    print("=" * 60)
    print(f"Character: {milan_character['name']}")
    print(f"LoRa: {milan_character['lora_file']}")
    print(f"Input Image: test_input.jpg")
    print(f"ComfyUI URL: https://c79vcd863ntrtq-3001.proxy.runpod.net")
    print("=" * 60)

    # Test with the uploaded image
    result = await service.generate(
        character=milan_character,
        workflow_path="workflows/qwen/instagram_api_fast.json",
        input_image_filename="test_input.jpg",
        prompt_additions="wearing elegant dress, professional photo",
        sampler_overrides={
            "steps": 20,
            "cfg": 3.5,
            "denoise": 0.75
        }
    )

    print("\n" + "=" * 60)
    if result["success"]:
        print("✅ SUCCESS!")
        print(f"Processing time: {result['processing_time']:.1f}s")
        print(f"Output URL: {result['output_url']}")
        print("\nYou can view the generated image at:")
        print(result['output_url'])
    else:
        print("❌ FAILED!")
        print(f"Error: {result.get('error', 'Unknown error')}")
    print("=" * 60)

    return result

if __name__ == "__main__":
    result = asyncio.run(test_img2img())
    sys.exit(0 if result["success"] else 1)
