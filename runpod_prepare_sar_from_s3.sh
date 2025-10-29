#!/bin/bash
# Download sar LoRA training dataset from S3
# Run this on RunPod after setting AWS credentials

set -e

echo "=========================================="
echo "  Downloading SAR Dataset from S3"
echo "=========================================="

# Check for AWS credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✗ AWS credentials not set!"
    echo ""
    echo "Run these commands first:"
    echo "  export AWS_ACCESS_KEY_ID='your-key'"
    echo "  export AWS_SECRET_ACCESS_KEY='your-secret'"
    echo "  export AWS_REGION='us-east-2'"
    exit 1
fi

# Configuration
BUCKET_NAME="destinty-workflow-1761724503"
MODEL_NAME="sar"
TRAINING_DIR="/workspace/lora_training"

echo ""
echo "Configuration:"
echo "  • Bucket: $BUCKET_NAME"
echo "  • Model: $MODEL_NAME"
echo "  • Region: ${AWS_REGION:-us-east-2}"
echo ""

# Install AWS CLI if needed
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    pip install -q awscli
fi

# Create training directory with Kohya-required structure
# Format: <repeats>_<trigger_word>/
mkdir -p "$TRAINING_DIR/10_sar woman"

# Download enhanced images and captions from S3
echo "Downloading enhanced images + captions..."

# Download all enhanced images for sar from both source_1 and source_2
aws s3 sync "s3://$BUCKET_NAME/results/nsfw/source_1/enhanced/" "$TRAINING_DIR/10_sar woman/" \
    --exclude "*" \
    --include "sar-*-enhanced.jpg" \
    --include "sar-*-enhanced.txt" \
    --region "${AWS_REGION:-us-east-2}"

aws s3 sync "s3://$BUCKET_NAME/results/nsfw/source_2/enhanced/" "$TRAINING_DIR/10_sar woman/" \
    --exclude "*" \
    --include "sar-*-enhanced.jpg" \
    --include "sar-*-enhanced.txt" \
    --region "${AWS_REGION:-us-east-2}"

# Count what we got
IMAGE_COUNT=$(ls -1 "$TRAINING_DIR/10_sar woman/"*.jpg 2>/dev/null | wc -l)
CAPTION_COUNT=$(ls -1 "$TRAINING_DIR/10_sar woman/"*.txt 2>/dev/null | wc -l)

echo "✓ Downloaded $IMAGE_COUNT images"
echo "✓ Downloaded $CAPTION_COUNT captions"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo ""
    echo "✗ No images downloaded!"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check AWS credentials are correct"
    echo "  2. Verify bucket name: $BUCKET_NAME"
    echo "  3. Check if enhanced images exist in S3:"
    echo "     aws s3 ls s3://$BUCKET_NAME/results/nsfw/ --recursive | grep sar-.*-enhanced.jpg"
    exit 1
fi

# Verify images have matching captions
echo ""
echo "Verifying dataset..."
MISSING_CAPTIONS=0
for img in "$TRAINING_DIR/10_sar woman/"*.jpg; do
    caption="${img%.jpg}.txt"
    if [ ! -f "$caption" ]; then
        echo "  ⚠ Missing caption: $(basename $caption)"
        MISSING_CAPTIONS=$((MISSING_CAPTIONS + 1))
    fi
done

if [ "$MISSING_CAPTIONS" -gt 0 ]; then
    echo "  ⚠ $MISSING_CAPTIONS images missing captions"
else
    echo "  ✓ All images have captions"
fi

# Create dataset config
cat > "$TRAINING_DIR/dataset_config.json" << EOF
{
  "model_name": "sar",
  "trigger_word": "sar woman",
  "num_images": $IMAGE_COUNT,
  "image_size": 1024,
  "recommended_settings": {
    "epochs": 10,
    "batch_size": 1,
    "learning_rate": 1e-4,
    "network_dim": 32,
    "network_alpha": 16
  },
  "base_model": "stabilityai/stable-diffusion-xl-base-1.0",
  "notes": "Dataset downloaded from S3: $BUCKET_NAME"
}
EOF

echo "✓ Config created"

# Show sample caption
echo ""
echo "Sample caption:"
FIRST_CAPTION=$(ls "$TRAINING_DIR/10_sar woman/"*.txt 2>/dev/null | head -1)
if [ -f "$FIRST_CAPTION" ]; then
    echo "---"
    head -n 3 "$FIRST_CAPTION"
    echo "---"
fi

echo ""
echo "=========================================="
echo "  Dataset Ready!"
echo "=========================================="
echo ""
echo "Images: $IMAGE_COUNT"
echo "Captions: $CAPTION_COUNT"
echo "Location: $TRAINING_DIR/"
echo ""
echo "Next: bash /workspace/ai/runpod_setup_sar.sh"
echo ""
