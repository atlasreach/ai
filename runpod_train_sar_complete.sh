#!/bin/bash
# COMPLETE RunPod training script - runs EVERYTHING
# Just run: bash runpod_train_sar_complete.sh

set -e

echo "=========================================="
echo "  SAR LoRA Training - Complete Pipeline"
echo "=========================================="

# Set credentials (GET FROM YOUR .env FILE)
export AWS_ACCESS_KEY_ID='YOUR_AWS_KEY_HERE'
export AWS_SECRET_ACCESS_KEY='YOUR_AWS_SECRET_HERE'
export AWS_REGION='us-east-2'

# IMPORTANT: Edit the lines above with your actual AWS credentials before running!

echo "✓ Credentials set"

# Fix torch/torchvision compatibility
echo ""
echo "Checking PyTorch compatibility..."
if ! python -c "import torchvision" 2>/dev/null; then
    echo "  • Fixing torch/torchvision versions..."
    pip install -q --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu118
    echo "  ✓ PyTorch fixed"
else
    echo "  ✓ PyTorch OK"
fi

# Download dataset if needed
if [ ! -d "/workspace/lora_training/10_sar woman" ]; then
    echo ""
    echo "Step 1: Downloading dataset from S3..."
    bash /workspace/ai/runpod_prepare_sar_from_s3.sh
else
    echo ""
    echo "✓ Dataset already exists (14 images)"
fi

# Setup training
echo ""
echo "Step 2: Setting up training environment..."
bash /workspace/ai/runpod_setup_sar.sh

# Start training
echo ""
echo "Step 3: Starting training..."
echo "This will take 50-100 minutes. DO NOT CLOSE THIS WINDOW."
echo ""
sleep 3

bash /workspace/train_sar.sh

echo ""
echo "=========================================="
echo "  ✓ TRAINING COMPLETE!"
echo "=========================================="
echo ""
echo "Download your LoRA from:"
echo "  /workspace/sar_lora_output/sar-v1.safetensors"
echo ""
