#!/bin/bash
# Prepare LoRA training dataset from git repo files
# This recreates jade_lora_dataset.zip from the repo

set -e

echo "=========================================="
echo "  Preparing Dataset from Repo"
echo "=========================================="

cd /workspace/ai

# Create training directory
mkdir -p /workspace/lora_training/images

echo -e "\nCopying enhanced images + captions..."

# Copy all enhanced images and captions
cp models/jade/results/nsfw/source_*/enhanced/*.jpg /workspace/lora_training/images/ 2>/dev/null || true
cp models/jade/results/nsfw/source_*/enhanced/*.txt /workspace/lora_training/images/ 2>/dev/null || true

# Count what we got
IMAGE_COUNT=$(ls -1 /workspace/lora_training/images/*.jpg 2>/dev/null | wc -l)
CAPTION_COUNT=$(ls -1 /workspace/lora_training/images/*.txt 2>/dev/null | wc -l)

echo "✓ Copied $IMAGE_COUNT images"
echo "✓ Copied $CAPTION_COUNT captions"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "✗ No images found!"
    exit 1
fi

# Create config
cat > /workspace/lora_training/dataset_config.json << 'EOF'
{
  "model_name": "jade",
  "trigger_word": "jade woman",
  "num_images": 31,
  "image_size": 1024,
  "recommended_settings": {
    "epochs": 10,
    "batch_size": 1,
    "learning_rate": 1e-4,
    "network_dim": 32,
    "network_alpha": 16
  },
  "base_model": "stabilityai/stable-diffusion-xl-base-1.0",
  "notes": "Dataset prepared from git repo"
}
EOF

echo "✓ Config created"

echo ""
echo "=========================================="
echo "  Dataset Ready!"
echo "=========================================="
echo ""
echo "Images: $IMAGE_COUNT"
echo "Captions: $CAPTION_COUNT"
echo "Location: /workspace/lora_training/"
echo ""
echo "Next: bash runpod_setup.sh"
echo ""
