"""
Direct Diffusers generation on RunPod GPU
Run this ON RUNPOD, not Codespaces
"""
from diffusers import DiffusionPipeline, FlowMatchEulerDiscreteScheduler
import torch
import math
import sys

def generate_with_milan():
    """Generate image using Qwen + Milan LoRA"""

    print("🚀 Starting Diffusers generation...")
    print(f"   CUDA available: {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("   ❌ No GPU found!")
        return False

    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    print("\n📦 Loading Qwen-Image model...")

    try:
        # Configure scheduler
        scheduler_config = {
            "base_image_seq_len": 256,
            "base_shift": math.log(3),
            "num_train_timesteps": 1000,
            "shift": 1.0,
            "use_dynamic_shifting": True,
        }

        scheduler = FlowMatchEulerDiscreteScheduler.from_config(scheduler_config)

        # Load Qwen-Image pipeline
        pipe = DiffusionPipeline.from_pretrained(
            "Qwen/Qwen-Image",
            scheduler=scheduler,
            torch_dtype=torch.bfloat16
        )
        pipe = pipe.to("cuda")

        print("   ✅ Base model loaded")

        # Load Milan LoRA
        print("\n📦 Loading Milan LoRA...")
        milan_lora_path = "/workspace/ComfyUI/models/loras/milan_000002000.safetensors"

        pipe.load_lora_weights(milan_lora_path)
        pipe.fuse_lora(lora_scale=0.8)  # Strength 0.8

        print("   ✅ Milan LoRA loaded (strength: 0.8)")

        # Generate image
        print("\n🎨 Generating image...")
        prompt = "Milan, woman, professional photo, studio lighting, high quality"
        negative_prompt = "blurry, low quality, distorted"

        image = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=1024,
            height=768,
            num_inference_steps=30,
            guidance_scale=4.0,
            generator=torch.manual_seed(12345),
        ).images[0]

        # Save image
        output_path = "/workspace/test_milan_output.png"
        image.save(output_path)

        print(f"\n✅ SUCCESS!")
        print(f"   Image saved to: {output_path}")
        print(f"   Prompt: {prompt}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = generate_with_milan()
    sys.exit(0 if success else 1)
