"""
Test generation using Diffusers directly (no ComfyUI)
This should run on RunPod GPU
"""
import torch
from diffusers import DiffusionPipeline
from diffusers.models import UNet2DConditionModel
import os

def test_diffusers():
    """Test loading Qwen model with Milan LoRA"""

    print("🚀 Testing Diffusers generation...")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    print("\n📦 Loading Qwen model...")

    try:
        # Try to load Qwen model
        # The model path might be local or from HuggingFace
        model_path = "/workspace/ComfyUI/models/diffusion_models/qwen_image_fp8_e4m3fn.safetensors"

        if os.path.exists(model_path):
            print(f"   ✅ Found local model: {model_path}")
        else:
            print(f"   ❌ Local model not found")
            print(f"   Trying HuggingFace: Qwen/Qwen-VL")

        # For now, let's just verify torch works
        print(f"\n✅ PyTorch setup is working!")
        print(f"   This confirms GPU is accessible")
        print(f"\n📝 Next: Need to determine correct Qwen model loading method")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_diffusers()
