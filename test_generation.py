"""
Quick test script to verify end-to-end generation works
Uses a simple pre-made workflow
"""
import httpx
import json
import asyncio
import time

async def test_generation():
    """Test basic generation"""

    # Working workflow for Qwen with Milan LoRA
    workflow = {
        "37": {
            "inputs": {"unet_name": "qwen_image_fp8_e4m3fn.safetensors", "weight_dtype": "default"},
            "class_type": "UNETLoader"
        },
        "74": {
            "inputs": {"lora_name": "milan_000002000.safetensors", "strength_model": 0.8, "model": ["37", 0]},
            "class_type": "LoraLoaderModelOnly"
        },
        "38": {
            "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image"},
            "class_type": "CLIPLoader"
        },
        "39": {
            "inputs": {"vae_name": "qwen_image_vae.safetensors"},
            "class_type": "VAELoader"
        },
        "6": {
            "inputs": {"text": "Milan, woman, professional photo, studio lighting", "clip": ["38", 0]},
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {"text": "", "clip": ["38", 0]},
            "class_type": "CLIPTextEncode"
        },
        "58": {
            "inputs": {"width": 1024, "height": 768, "batch_size": 1},
            "class_type": "EmptySD3LatentImage"
        },
        "3": {
            "inputs": {
                "seed": 12345,
                "steps": 30,
                "cfg": 4.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["74", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["58", 0]
            },
            "class_type": "KSampler"
        },
        "8": {
            "inputs": {"samples": ["3", 0], "vae": ["39", 0]},
            "class_type": "VAEDecode"
        },
        "60": {
            "inputs": {"filename_prefix": "test", "images": ["8", 0]},
            "class_type": "SaveImage"
        }
    }

    print("🚀 Testing generation...")
    print(f"   Sending workflow to ComfyUI...")

    try:
        async with httpx.AsyncClient(timeout=240.0) as client:
            # Queue the prompt
            response = await client.post(
                "https://1314jk61pzkjdb-3001.proxy.runpod.net/prompt",
                json={"prompt": workflow, "client_id": "test123"}
            )

            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id")
                print(f"   ✅ Queued! Prompt ID: {prompt_id}")
                print(f"   ⏳ Waiting for generation (first time takes 2-3 min to load models)...")

                # Wait for completion
                for i in range(90):  # 3 minutes max
                    await asyncio.sleep(2)

                    history_response = await client.get(
                        f"https://1314jk61pzkjdb-3001.proxy.runpod.net/history/{prompt_id}"
                    )

                    if history_response.status_code == 200:
                        history = history_response.json()
                        if prompt_id in history and "outputs" in history[prompt_id]:
                            print(f"   ✅ GENERATION COMPLETE!")
                            print(f"   Time: {(i+1) * 2} seconds")
                            print(f"   Result: {json.dumps(history[prompt_id]['outputs'], indent=2)}")
                            return True

                    if i % 5 == 0:
                        print(f"   ... still generating ({i*2}s)")

                print(f"   ⏱️ Timeout")
                return False
            else:
                print(f"   ❌ Error: {response.text}")
                return False

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_generation())

    if success:
        print("\n🎉 SUCCESS! ComfyUI is working!")
        print("   The full backend should work once we fix the workflow format.")
    else:
        print("\n❌ Test failed. Check RunPod ComfyUI setup.")
