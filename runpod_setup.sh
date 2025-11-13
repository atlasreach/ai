#!/bin/bash
# RunPod Setup Script - Run this if you restart the pod
# Installs required dependencies for Diffusers generation

set -e

echo "🔧 RunPod Setup - Installing dependencies..."

# Install Python packages
echo "📦 Installing Python packages..."
pip install diffusers transformers accelerate peft torch --quiet

# Verify installations
echo ""
echo "✅ Verifying installations..."
python3 -c "import diffusers; print(f'  Diffusers: {diffusers.__version__}')"
python3 -c "import transformers; print(f'  Transformers: {transformers.__version__}')"
python3 -c "import accelerate; print(f'  Accelerate: {accelerate.__version__}')"
python3 -c "import peft; print(f'  PEFT: {peft.__version__}')"
python3 -c "import torch; print(f'  PyTorch: {torch.__version__}')"

# Check GPU
echo ""
echo "🎮 GPU Status:"
python3 -c "import torch; print(f'  CUDA available: {torch.cuda.is_available()}'); print(f'  GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

# Check LoRA files
echo ""
echo "📂 Checking LoRA files..."
if [ -f "/workspace/ComfyUI/models/loras/milan_000002000.safetensors" ]; then
    echo "  ✅ Milan LoRA found"
else
    echo "  ❌ Milan LoRA missing!"
    echo "     Download from: https://huggingface.co/nicksanford2341/businessmodels"
fi

echo ""
echo "✅ Setup complete! Run: python3 /workspace/ai/runpod_generate.py"
