"""
Test Qwen Image Edit Workflow
Instruction-based image editing (e.g., "change bikini to red")
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from services.comfyui_service import ComfyUIService

async def test_qwen_edit():
    """Test Qwen Edit with instruction-based editing"""
    print("\n" + "=" * 70)
    print("🎨 QWEN IMAGE EDIT TEST")
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

    # Test with instruction-based editing
    # This is different from generation - you give an instruction to modify
    edit_instruction = "change her outfit to a red dress"

    params = {
        "steps": 20,
        "cfg": 4.0,
        "denoise": 0.8,  # High for editing
        "lora_strength": 0.5,
        "seed": 12345
    }

    print(f"\n📝 Edit Instruction: {edit_instruction}")
    print(f"Parameters: {params}")
    print(f"Input: 22.jpg")

    try:
        result = await service.generate(
            character=character,
            workflow_path="workflows/qwen/instagram_edit.json",  # Edit workflow
            input_image_filename="22.jpg",
            prompt_additions=edit_instruction,  # This becomes the edit instruction
            sampler_overrides=params,
            lora_strength_override=params["lora_strength"]
        )

        if result["success"]:
            print(f"\n✅ EDIT SUCCESSFUL")
            print(f"   Time: {result['processing_time']:.1f}s")
            print(f"   Images: {len(result['output_images'])}")
            print(f"   Output: {result['output_url']}")
            return True
        else:
            print(f"\n❌ EDIT FAILED: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run edit test"""
    print("\n" + "=" * 70)
    print("🧪 TESTING QWEN IMAGE EDITING")
    print("=" * 70)
    print("\nThis workflow allows text-based instructions like:")
    print("  - 'change her outfit to a red dress'")
    print("  - 'make the background a beach'")
    print("  - 'add sunglasses'")

    success = await test_qwen_edit()

    if success:
        print("\n🎉 Qwen Edit workflow is working!")
    else:
        print("\n⚠️ Qwen Edit needs debugging")

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
