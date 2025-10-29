#!/bin/bash
# RunPod LoRA Training Script
# This script starts the actual training process

set -e

echo "=========================================="
echo "  Starting LoRA Training"
echo "=========================================="

# Verify setup
if [ ! -f "/workspace/jade_config.toml" ]; then
    echo "✗ Setup not complete. Run: bash runpod_setup.sh"
    exit 1
fi

if [ ! -d "/workspace/kohya_ss" ]; then
    echo "✗ Kohya_ss not found. Run: bash runpod_setup.sh"
    exit 1
fi

# Create output directory
mkdir -p /workspace/jade_lora_output

echo ""
echo "Training will start in 5 seconds..."
echo "This will take 45-75 minutes."
echo ""
echo "Press Ctrl+C to cancel"
sleep 5

# Start training
cd /workspace/kohya_ss

echo ""
echo "=========================================="
echo "  Training Started: $(date)"
echo "=========================================="
echo ""

python train_network.py \
    --config_file /workspace/jade_config.toml \
    --dataset_config /workspace/jade_config.toml

# Training complete
echo ""
echo "=========================================="
echo "  Training Complete!"
echo "=========================================="
echo ""
echo "Model saved to: /workspace/jade_lora_output/jade-v1.safetensors"
echo ""
echo "Download the model:"
echo ""
echo "Option A - Web Terminal:"
echo "  1. Navigate to /workspace/jade_lora_output/"
echo "  2. Right-click jade-v1.safetensors"
echo "  3. Click 'Download'"
echo ""
echo "Option B - SCP from local machine:"
echo "  scp -i ~/.ssh/id_ed25519 w76u042vchb6p3-64411d6d@ssh.runpod.io:/workspace/jade_lora_output/jade-v1.safetensors /workspaces/ai/models/jade/"
echo ""
echo "⚠ IMPORTANT: Stop your pod to avoid charges!"
echo "  Go to RunPod dashboard → Stop/Terminate pod"
echo ""
