"""
Test Single vs Batch Image Generation
Same prompt, different modes
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent))

from services.comfyui_service import ComfyUIService

async def test_single_image():
    """Test 1: Single image generation"""
    print("\n" + "=" * 70)
    print("🎨 TEST 1: SINGLE IMAGE GENERATION")
    print("=" * 70)

    service = ComfyUIService()
    character = {
        "id": "milan",
        "name": "Milan",
        "trigger_word": "milan",
        "lora_file": "milan_000002000.safetensors",
        "lora_strength": 0.5,
        "character_constraints": {"constants": []}
    }

    # Same prompt for all tests
    prompt = "woman with long brown hair, professional photo, elegant pose"

    params = {
        "steps": 20,
        "cfg": 4.0,
        "denoise": 0.75,
        "lora_strength": 0.5,
        "seed": 12345
    }

    print(f"\nPrompt: {prompt}")
    print(f"Parameters: {params}")
    print(f"Input: 22.jpg (single image)")

    start_time = asyncio.get_event_loop().time()

    result = await service.generate(
        character=character,
        input_image_filename="22.jpg",
        prompt_additions=prompt,
        sampler_overrides=params,
        lora_strength_override=params["lora_strength"]
    )

    elapsed = asyncio.get_event_loop().time() - start_time

    if result["success"]:
        print(f"\n✅ SUCCESS")
        print(f"   Time: {elapsed:.1f}s")
        print(f"   Images: {len(result['output_images'])}")
        print(f"   Output: {result['output_url']}")
        return {
            "success": True,
            "time": elapsed,
            "images": len(result['output_images']),
            "url": result['output_url']
        }
    else:
        print(f"\n❌ FAILED: {result.get('error')}")
        return {"success": False}

async def test_batch_images():
    """Test 2: Batch processing (run 3 times)"""
    print("\n" + "=" * 70)
    print("🎨 TEST 2: BATCH PROCESSING (3 images)")
    print("=" * 70)

    service = ComfyUIService()
    character = {
        "id": "milan",
        "name": "Milan",
        "trigger_word": "milan",
        "lora_file": "milan_000002000.safetensors",
        "lora_strength": 0.5,
        "character_constraints": {"constants": []}
    }

    # Same prompt as single test
    prompt = "woman with long brown hair, professional photo, elegant pose"

    params = {
        "steps": 20,
        "cfg": 4.0,
        "denoise": 0.75,
        "lora_strength": 0.5
    }

    # Process 3 images (simulating batch)
    input_images = ["22.jpg", "22.jpg", "22.jpg"]  # Using same image 3x for demo
    seeds = [12345, 12346, 12347]  # Different seeds for variety

    print(f"\nPrompt: {prompt}")
    print(f"Parameters: {params}")
    print(f"Inputs: {len(input_images)} images")
    print(f"Seeds: {seeds}")

    results = []
    start_time = asyncio.get_event_loop().time()

    for idx, (input_img, seed) in enumerate(zip(input_images, seeds), 1):
        print(f"\n  [{idx}/3] Generating image {idx}...")

        params["seed"] = seed

        result = await service.generate(
            character=character,
            input_image_filename=input_img,
            prompt_additions=prompt,
            sampler_overrides=params,
            lora_strength_override=params["lora_strength"]
        )

        if result["success"]:
            print(f"       ✓ Done in {result['processing_time']:.1f}s")
            results.append({
                "image_num": idx,
                "success": True,
                "time": result['processing_time'],
                "url": result['output_url']
            })
        else:
            print(f"       ✗ Failed: {result.get('error')}")
            results.append({"image_num": idx, "success": False})

    total_time = asyncio.get_event_loop().time() - start_time

    # Summary
    successful = sum(1 for r in results if r.get("success"))
    print(f"\n✅ BATCH COMPLETE")
    print(f"   Total time: {total_time:.1f}s")
    print(f"   Successful: {successful}/{len(results)}")
    print(f"   Avg per image: {total_time/len(results):.1f}s")

    if successful > 0:
        print(f"\n   Output URLs:")
        for r in results:
            if r.get("success"):
                print(f"     {r['image_num']}. {r['url']}")

    return {
        "success": successful == len(results),
        "total_time": total_time,
        "per_image_time": total_time / len(results),
        "results": results
    }

async def main():
    """Run comparison test"""
    print("\n" + "=" * 70)
    print("🧪 SINGLE vs BATCH COMPARISON TEST")
    print("=" * 70)
    print("\nComparing single image generation vs batch processing")
    print("Using SAME prompt for both tests")

    # Test 1: Single
    single_result = await test_single_image()

    # Small delay
    await asyncio.sleep(2)

    # Test 2: Batch
    batch_result = await test_batch_images()

    # Comparison
    print("\n" + "=" * 70)
    print("📊 COMPARISON RESULTS")
    print("=" * 70)

    if single_result.get("success"):
        print(f"\nSingle Image:")
        print(f"  Time: {single_result['time']:.1f}s")
        print(f"  Images: 1")
        print(f"  Per image: {single_result['time']:.1f}s")

    if batch_result.get("success"):
        print(f"\nBatch (3 images):")
        print(f"  Total time: {batch_result['total_time']:.1f}s")
        print(f"  Images: 3")
        print(f"  Per image: {batch_result['per_image_time']:.1f}s")

    if single_result.get("success") and batch_result.get("success"):
        efficiency = (3 * single_result['time']) / batch_result['total_time']
        print(f"\n💡 Batch Processing:")
        if efficiency > 1:
            print(f"  {efficiency:.1f}x FASTER than running single 3 times")
        else:
            print(f"  {1/efficiency:.1f}x SLOWER (overhead from sequential processing)")

    return single_result.get("success") and batch_result.get("success")

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
