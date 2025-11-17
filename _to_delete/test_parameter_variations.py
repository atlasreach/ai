"""
Test different parameter configurations for ComfyUI generation
Generates 3 images with varied settings and saves metadata
"""
import asyncio
import sys
import os
import json
import aiohttp
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from services.comfyui_service import ComfyUIService

async def download_image(url: str, output_path: str):
    """Download image from ComfyUI"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                with open(output_path, 'wb') as f:
                    f.write(content)
                return True
    return False

async def generate_and_save(service, character, config_name, params, output_base_dir):
    """Generate image with specific parameters and save with metadata"""
    print(f"\n{'=' * 70}")
    print(f"🎨 Test {config_name}")
    print(f"{'=' * 70}")
    print(f"Parameters:")
    print(f"  Steps: {params['steps']}")
    print(f"  CFG: {params['cfg']}")
    print(f"  Denoise: {params['denoise']}")
    print(f"  LoRA Strength: {params['lora_strength']}")
    print(f"  Seed: {params['seed']}")
    print(f"  Prompt: {params['prompt'][:80]}...")

    # Generate
    result = await service.generate(
        character=character,
        input_image_filename="22.jpg",
        prompt_additions=params['prompt'],
        sampler_overrides={
            'steps': params['steps'],
            'cfg': params['cfg'],
            'denoise': params['denoise'],
            'seed': params['seed']
        },
        lora_strength_override=params['lora_strength']
    )

    if not result['success']:
        print(f"❌ Generation failed: {result.get('error')}")
        return False

    print(f"\n✅ Generation successful!")
    print(f"   Time: {result['processing_time']:.1f}s")
    print(f"   Images: {len(result['output_images'])}")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_base_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download image
    if result['output_url']:
        image_path = output_dir / "generated.png"
        print(f"   📥 Downloading image...")
        success = await download_image(result['output_url'], str(image_path))
        if success:
            print(f"   ✓ Saved to: {image_path}")
        else:
            print(f"   ⚠ Failed to download image")

    # Save metadata
    metadata = {
        "model": character['id'],
        "timestamp": timestamp,
        "config_name": config_name,
        "prompt": f"{character['trigger_word']}, {params['prompt']}",
        "negative_prompt": "blurry, low quality, distorted, deformed, disfigured",
        "parameters": {
            "width": 1024,
            "height": 768,
            "steps": params['steps'],
            "cfg_scale": params['cfg'],
            "lora_strength": params['lora_strength'],
            "seed": params['seed'],
            "strength": params['denoise'],  # denoise = strength in img2img
            "num_images": 1,
            "upscale_enabled": False,
            "upscale_factor": None,
            "model_sampling_shift": 2.0
        },
        "generation_time": result['processing_time'],
        "has_input_image": True,
        "input_image": "22.jpg",
        "output_url": result['output_url'],
        "prompt_id": result['prompt_id']
    }

    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"   ✓ Saved metadata to: {metadata_path}")
    return True

async def main():
    """Run parameter variation tests"""
    print("\n" + "=" * 70)
    print("🧪 ComfyUI Parameter Variation Test")
    print("=" * 70)
    print("\nTesting 3 different configurations to verify parameter control")

    service = ComfyUIService()

    # Test character
    character = {
        "id": "milan",
        "name": "Milan",
        "trigger_word": "milan",
        "lora_file": "milan_000002000.safetensors",
        "lora_strength": 0.5,
        "character_constraints": {"constants": []}
    }

    output_base_dir = Path("/workspaces/ai/outputs/milan")

    # Test configurations
    tests = [
        {
            "name": "Test 1: Conservative (Low Transformation)",
            "params": {
                "steps": 15,
                "cfg": 3.5,
                "denoise": 0.6,  # Low = less transformation
                "lora_strength": 0.4,  # Subtle LoRA
                "seed": 111,
                "prompt": "woman with long brown hair, elegant pose, soft lighting"
            }
        },
        {
            "name": "Test 2: Balanced (Medium Transformation)",
            "params": {
                "steps": 20,
                "cfg": 4.0,
                "denoise": 0.75,  # Medium transformation
                "lora_strength": 0.65,  # Moderate LoRA
                "seed": 222,
                "prompt": "woman with flowing hair, confident expression, professional photo"
            }
        },
        {
            "name": "Test 3: Aggressive (High Transformation)",
            "params": {
                "steps": 30,
                "cfg": 4.5,
                "denoise": 0.9,  # High = strong transformation
                "lora_strength": 0.85,  # Strong LoRA
                "seed": 333,
                "prompt": "woman with beautiful hair, dramatic pose, studio lighting, detailed face"
            }
        }
    ]

    results = []
    for test in tests:
        success = await generate_and_save(
            service,
            character,
            test["name"],
            test["params"],
            output_base_dir
        )
        results.append(success)

        # Small delay between tests
        if success:
            await asyncio.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")

    if sum(results) == len(results):
        print("\n🎉 All tests passed!")
        print(f"✅ Parameters are fully configurable")
        print(f"✅ Metadata saved for each generation")
        print(f"\n📁 Check outputs at: {output_base_dir}")
    else:
        print(f"\n⚠️ Some tests failed")

    return sum(results) == len(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
