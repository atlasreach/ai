"""
Ultra simple test - just load models, no generation
"""
import httpx
import json
import asyncio

async def test_simple():
    """Test just loading models"""

    # Minimal workflow - just load UNET
    workflow = {
        "37": {
            "inputs": {"unet_name": "qwen_image_fp8_e4m3fn.safetensors", "weight_dtype": "default"},
            "class_type": "UNETLoader"
        }
    }

    print("🧪 Testing simple model load...")
    print(f"   Workflow: {json.dumps(workflow, indent=2)}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://1314jk61pzkjdb-3001.proxy.runpod.net/prompt",
                json={"prompt": workflow, "client_id": "test_simple"}
            )

            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")

            if response.status_code == 200:
                print("   ✅ Success!")
                return True
            else:
                print(f"   ❌ Failed: {response.text}")
                return False

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple())
    if success:
        print("\n✅ ComfyUI accepts the workflow format!")
    else:
        print("\n❌ ComfyUI rejected the workflow")
