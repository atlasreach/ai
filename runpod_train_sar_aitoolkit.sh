#!/bin/bash
# SAR LoRA Training using ai-toolkit (RELIABLE!)
# This actually works on RunPod without dependency hell

set -e

echo "=========================================="
echo "  SAR LoRA Training (ai-toolkit)"
echo "  Flux.1-dev | 7 images"
echo "=========================================="

# SET YOUR AWS CREDENTIALS BEFORE RUNNING:
# export AWS_ACCESS_KEY_ID='your-key-here'
# export AWS_SECRET_ACCESS_KEY='your-secret-here'
export AWS_REGION='us-east-2'
export BUCKET_NAME='destinty-workflow-1761724503'

# Check credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✗ AWS credentials not set!"
    echo ""
    echo "Run these commands first:"
    echo "  export AWS_ACCESS_KEY_ID='your-key'"
    echo "  export AWS_SECRET_ACCESS_KEY='your-secret'"
    echo ""
    exit 1
fi

echo "✓ Credentials verified"

#############################################
# STEP 1: Install ai-toolkit (clean install)
#############################################

cd /workspace

if [ ! -d "ai-toolkit" ]; then
    echo ""
    echo "Step 1: Installing ai-toolkit..."

    # Clone repo
    git clone https://github.com/ostris/ai-toolkit.git
    cd ai-toolkit
    git submodule update --init --recursive

    # Create clean virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install specific PyTorch version (no conflicts!)
    echo "  • Installing PyTorch 2.6.0 + CUDA 12.6..."
    pip3 install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126

    # Install ai-toolkit requirements
    echo "  • Installing ai-toolkit dependencies..."
    pip3 install -r requirements.txt

    echo "✓ ai-toolkit installed (5-10 min)"
else
    echo ""
    echo "✓ ai-toolkit already installed"
    cd /workspace/ai-toolkit
    source venv/bin/activate
fi

#############################################
# STEP 2: Download dataset from S3
#############################################

echo ""
echo "Step 2: Downloading SAR images from S3..."

# Install awscli in venv if needed
if ! command -v aws &> /dev/null; then
    pip3 install -q awscli
fi

mkdir -p /workspace/sar_dataset

# Download source_1 enhanced images + captions
aws s3 sync "s3://$BUCKET_NAME/results/nsfw/source_1/enhanced/" /workspace/sar_dataset/ \
    --exclude "*" \
    --include "sar-s1-*-enhanced.jpg" \
    --include "sar-s1-*-enhanced.txt" \
    --region us-east-2

IMAGE_COUNT=$(ls -1 /workspace/sar_dataset/*.jpg 2>/dev/null | wc -l)
CAPTION_COUNT=$(ls -1 /workspace/sar_dataset/*.txt 2>/dev/null | wc -l)

echo "✓ Downloaded $IMAGE_COUNT images"
echo "✓ Downloaded $CAPTION_COUNT captions"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "✗ No images found!"
    exit 1
fi

#############################################
# STEP 3: Create training config (YAML)
#############################################

echo ""
echo "Step 3: Creating training config..."

cat > /workspace/ai-toolkit/config/sar_flux_lora.yaml << 'EOF'
job: extension
config:
  name: sar_flux_lora
  process:
    - type: sd_trainer
      training_folder: /workspace/ai-toolkit
      device: cuda:0

      # Trigger word
      trigger_word: "sar"

      # Model settings
      network:
        type: lora
        linear: 16
        linear_alpha: 16

      save:
        dtype: float16
        save_every: 200
        max_step_saves_to_keep: 3

      datasets:
        - folder_path: /workspace/sar_dataset
          caption_ext: txt
          caption_dropout_rate: 0.05
          shuffle_tokens: false
          cache_latents_to_disk: true
          resolution:
            - 512
            - 768
            - 1024

      train:
        batch_size: 1
        steps: 1000
        gradient_accumulation_steps: 1
        train_unet: true
        train_text_encoder: false
        gradient_checkpointing: true
        noise_scheduler: flowmatch
        optimizer: adamw8bit
        lr: 4e-4

        # For LoRA
        linear_timesteps: true

        # Flux.1-dev settings
        ema_config:
          use_ema: true
          ema_decay: 0.99

        dtype: bf16

      model:
        name_or_path: black-forest-labs/FLUX.1-dev
        is_flux: true
        quantize: true

      sample:
        sampler: flowmatch
        sample_every: 200
        width: 1024
        height: 1024
        prompts:
          - "sar woman, portrait, soft lighting, high detail"
          - "sar woman, full body, studio photography, 8k"
        neg: ""
        seed: 42
        walk_seed: true
        guidance_scale: 3.5
        sample_steps: 20
EOF

echo "✓ Config created: config/sar_flux_lora.yaml"

#############################################
# STEP 4: Start training
#############################################

echo ""
echo "=========================================="
echo "  Starting Training"
echo "=========================================="
echo ""
echo "Dataset: $IMAGE_COUNT images"
echo "Steps: 1000 (saves every 200)"
echo "Time: ~30-60 minutes"
echo "Output: /workspace/ai-toolkit/output/sar_flux_lora/"
echo ""
echo "Training will start in 5 seconds..."
echo "Press Ctrl+C to cancel"
sleep 5

cd /workspace/ai-toolkit

python run.py config/sar_flux_lora.yaml

#############################################
# STEP 5: Training complete
#############################################

echo ""
echo "=========================================="
echo "  ✓ Training Complete!"
echo "=========================================="
echo ""
echo "LoRA saved to:"
echo "  /workspace/ai-toolkit/output/sar_flux_lora/"
echo ""
echo "Files:"
ls -lh /workspace/ai-toolkit/output/sar_flux_lora/*.safetensors 2>/dev/null || echo "  (check output directory)"
echo ""
echo "To test your LoRA:"
echo "  1. Download the .safetensors file"
echo "  2. Use in ComfyUI/Automatic1111/Forge"
echo "  3. Trigger word: 'sar'"
echo ""
echo "Example prompt:"
echo "  'sar woman, portrait, soft lighting, photorealistic'"
echo ""
