"""
Test ComfyUI Integration
Tests the ComfyUI service and API connectivity
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.comfyui_service import ComfyUIService

async def test_connectivity():
    """Test if ComfyUI API is accessible"""
    print("=" * 60)
    print("TEST 1: ComfyUI API Connectivity")
    print("=" * 60)

    service = ComfyUIService()
    print(f"ComfyUI URL: {service.api_url}")

    # Try to access the root endpoint
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{service.api_url}/", timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"✅ ComfyUI is accessible! Status: {response.status}")
                return True
    except Exception as e:
        print(f"❌ ComfyUI is NOT accessible: {e}")
        return False

async def test_workflow_loading():
    """Test workflow loading and inspection"""
    print("\n" + "=" * 60)
    print("TEST 2: Workflow Loading")
    print("=" * 60)

    service = ComfyUIService()

    try:
        workflow = service.load_workflow("workflows/qwen/instagram_single.json")
        print(f"✅ Workflow loaded successfully")
        print(f"   Nodes count: {len(workflow.get('nodes', []))}")
        print(f"   Links count: {len(workflow.get('links', []))}")

        # Find key nodes
        for node in workflow.get("nodes", []):
            node_type = node.get("type")
            if node_type == "LoraLoaderModelOnly":
                print(f"\n   Found LoRA loader (node {node.get('id')})")
                print(f"      Current values: {node.get('widgets_values')}")
            elif node_type == "CLIPTextEncode":
                title = node.get("title", "")
                print(f"\n   Found {title} (node {node.get('id')})")
                print(f"      Current prompt: {node.get('widgets_values', [''])[0][:50]}...")
            elif node_type == "LoadImage":
                print(f"\n   Found LoadImage (node {node.get('id')})")
                print(f"      Current image: {node.get('widgets_values')}")

        return True
    except Exception as e:
        print(f"❌ Failed to load workflow: {e}")
        return False

async def test_injection():
    """Test parameter injection"""
    print("\n" + "=" * 60)
    print("TEST 3: Parameter Injection")
    print("=" * 60)

    service = ComfyUIService()

    try:
        # Load workflow
        workflow = service.load_workflow("workflows/qwen/instagram_single.json")

        # Test character data
        test_character = {
            "id": "milan",
            "name": "Milan",
            "trigger_word": "milan",
            "lora_file": "milan_000002000.safetensors",
            "lora_strength": 0.8,
            "character_constraints": {
                "constants": [
                    {"key": "hair_color", "value": "blonde hair", "type": "physical"},
                    {"key": "skin", "value": "fair skin", "type": "physical"}
                ]
            }
        }

        # Inject LoRA
        print("\n   Injecting LoRA...")
        workflow = service.inject_lora(workflow, test_character["lora_file"], test_character["lora_strength"])

        # Build and inject prompt
        print("\n   Building prompt from character...")
        prompt = service.build_prompt_from_character(test_character, "wearing red dress, smiling")
        print(f"      Built prompt: {prompt}")

        workflow = service.inject_prompt(workflow, prompt, "")

        # Verify injections
        print("\n   Verifying injections...")
        for node in workflow.get("nodes", []):
            node_type = node.get("type")
            if node_type == "LoraLoaderModelOnly":
                values = node.get('widgets_values', [])
                print(f"      ✅ LoRA node updated: {values}")
            elif node_type == "CLIPTextEncode" and "positive" in node.get("title", "").lower():
                values = node.get('widgets_values', [])
                print(f"      ✅ Positive prompt updated: {values[0][:60]}...")

        print("\n✅ Injection test passed!")
        return True

    except Exception as e:
        print(f"❌ Injection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_format_conversion():
    """Test workflow conversion to API format"""
    print("\n" + "=" * 60)
    print("TEST 4: API Format Conversion")
    print("=" * 60)

    service = ComfyUIService()

    try:
        workflow = service.load_workflow("workflows/qwen/instagram_single.json")

        # Inject test data
        workflow = service.inject_lora(workflow, "milan_000002000.safetensors", 0.8)
        workflow = service.inject_prompt(workflow, "milan, blonde hair, fair skin, smiling", "")

        # Convert to API format
        api_workflow = service.convert_workflow_to_api_format(workflow)

        print(f"   Converted {len(workflow.get('nodes', []))} nodes to API format")
        print(f"   API workflow keys: {len(api_workflow)} nodes")

        # Show a sample node
        if "74" in api_workflow:  # LoRA loader node
            print(f"\n   Sample node (74 - LoRA Loader):")
            print(f"      class_type: {api_workflow['74'].get('class_type')}")
            print(f"      inputs: {api_workflow['74'].get('inputs')}")

        print("\n✅ API format conversion passed!")
        return True

    except Exception as e:
        print(f"❌ API format conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("\n🧪 ComfyUI Integration Test Suite")
    print("=" * 60)

    results = []

    # Test 1: Connectivity
    results.append(await test_connectivity())

    # Test 2: Workflow loading
    results.append(await test_workflow_loading())

    # Test 3: Injection
    results.append(await test_injection())

    # Test 4: API format conversion
    results.append(await test_api_format_conversion())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✅ All tests passed!")
    else:
        print(f"❌ {total - passed} test(s) failed")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
