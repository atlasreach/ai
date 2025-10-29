#!/bin/bash
# WORKING Flux LoRA Training for SAR (Source 1 Only)
# Tested and simplified - no million errors!

set -e

echo "=========================================="
echo "  SAR LoRA Training (Source 1 Only)"
echo "  Using Flux.1-dev"
echo "=========================================="

# SET YOUR AWS CREDENTIALS BEFORE RUNNING:
# export AWS_ACCESS_KEY_ID='your-key-here'
# export AWS_SECRET_ACCESS_KEY='your-secret-here'
export AWS_REGION='us-east-2'
export BUCKET_NAME='destinty-workflow-1761724503'

# Check credentials are set
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✗ AWS credentials not set!"
    echo ""
    echo "Run these commands first (get from your .env file):"
    echo "  export AWS_ACCESS_KEY_ID='your-key'"
    echo "  export AWS_SECRET_ACCESS_KEY='your-secret'"
    echo ""
    exit 1
fi

echo "✓ Credentials verified"

# Fix PyTorch first (common error source)
echo ""
echo "Fixing PyTorch compatibility..."
pip install -q --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
echo "✓ PyTorch fixed"

# Install AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    pip install -q awscli
fi

# Download ONLY source_1 images from S3
echo ""
echo "Step 1: Downloading SAR source_1 images from S3..."
mkdir -p /workspace/lora_training/10_sar

# Download only source_1 enhanced images + captions
aws s3 sync "s3://$BUCKET_NAME/results/nsfw/source_1/enhanced/" /workspace/lora_training/10_sar/ \
    --exclude "*" \
    --include "sar-s1-*-enhanced.jpg" \
    --include "sar-s1-*-enhanced.txt" \
    --region us-east-2

IMAGE_COUNT=$(ls -1 /workspace/lora_training/10_sar/*.jpg 2>/dev/null | wc -l)
CAPTION_COUNT=$(ls -1 /workspace/lora_training/10_sar/*.txt 2>/dev/null | wc -l)

echo "✓ Downloaded $IMAGE_COUNT images (source 1 only)"
echo "✓ Downloaded $CAPTION_COUNT captions"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "✗ No images downloaded!"
    echo "Check S3 bucket: $BUCKET_NAME"
    exit 1
fi

# Install SimpleTuner (easier than Kohya for Flux)
echo ""
echo "Step 2: Installing SimpleTuner (Flux-compatible)..."
cd /workspace

if [ ! -d "SimpleTuner" ]; then
    git clone https://github.com/bghira/SimpleTuner.git
    cd SimpleTuner
    pip install -q -e .  # Install in editable mode from source
    echo "✓ SimpleTuner installed"
    cd /workspace
else
    echo "✓ SimpleTuner already exists"
fi

# Create training config
echo ""
echo "Step 3: Creating training config..."

cat > /workspace/train_config.json << 'EOF'
{
  "model_type": "flux",
  "pretrained_model_name_or_path": "black-forest-labs/FLUX.1-dev",
  "instance_data_dir": "/workspace/lora_training/10_sar",
  "output_dir": "/workspace/sar_lora_output",
  "instance_prompt": "sar",
  "resolution": 1024,
  "train_batch_size": 1,
  "gradient_accumulation_steps": 1,
  "learning_rate": 1e-4,
  "lr_scheduler": "constant",
  "lr_warmup_steps": 0,
  "max_train_steps": 1000,
  "save_steps": 200,
  "mixed_precision": "bf16",
  "use_8bit_adam": true,
  "gradient_checkpointing": true,
  "seed": 42,
  "logging_dir": "/workspace/logs"
}
EOF

echo "✓ Config created"

# Create simplified training script
echo ""
echo "Step 4: Creating training script..."

cat > /workspace/train_sar_flux.sh << 'TRAINSCRIPT'
#!/bin/bash
set -e

cd /workspace/SimpleTuner

echo "=========================================="
echo "  Starting Flux LoRA Training"
echo "  Images: $(ls /workspace/lora_training/10_sar/*.jpg | wc -l)"
echo "  Trigger: 'sar'"
echo "=========================================="

python train.py \
  --pretrained_model_name_or_path="black-forest-labs/FLUX.1-dev" \
  --instance_data_dir="/workspace/lora_training/10_sar" \
  --output_dir="/workspace/sar_lora_output" \
  --instance_prompt="sar" \
  --resolution=1024 \
  --train_batch_size=1 \
  --learning_rate=1e-4 \
  --max_train_steps=1000 \
  --save_steps=200 \
  --mixed_precision="bf16" \
  --use_8bit_adam \
  --gradient_checkpointing \
  --caption_column="text"

echo ""
echo "=========================================="
echo "  Training Complete!"
echo "=========================================="
echo "LoRA: /workspace/sar_lora_output/"
TRAINSCRIPT

chmod +x /workspace/train_sar_flux.sh
echo "✓ Training script ready"

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Dataset:"
echo "  • Images: $IMAGE_COUNT (source 1 only)"
echo "  • Captions: $CAPTION_COUNT"
echo "  • Trigger word: 'sar'"
echo ""
echo "To start training:"
echo "  bash /workspace/train_sar_flux.sh"
echo ""
echo "Estimated time: ~30-60 minutes on RTX 4090"
echo ""
