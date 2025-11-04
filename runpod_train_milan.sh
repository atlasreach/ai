#!/bin/bash
# Milan LoRA Training for Wan 2.2
# Based on successful Sara 2.0 training

set -e

echo "=========================================="
echo "  Milan LoRA Training"
echo "  Using Ostris AI Toolkit + Wan 2.2"
echo "=========================================="

# Configuration
DATASET_NAME="milan_v1"
TRIGGER_WORD="Milan"
TRAINING_STEPS=1500  # Sara's sweet spot was 1500
LEARNING_RATE="1e-4"
SAVE_EVERY=250  # Save checkpoints more frequently

echo "Configuration:"
echo "  • Trigger word: $TRIGGER_WORD"
echo "  • Training steps: $TRAINING_STEPS"
echo "  • Learning rate: $LEARNING_RATE"
echo ""

# Step 1: Prepare dataset directory
echo "Step 1: Preparing training dataset..."
mkdir -p /workspace/lora_training/10_milan

# You'll upload your selected ~50-60 images here
# Structure:
#   milan_selected_1.jpg + milan_selected_1.txt
#   milan_selected_2.jpg + milan_selected_2.txt
#   etc.

IMAGE_COUNT=$(ls -1 /workspace/lora_training/10_milan/*.jpg 2>/dev/null | wc -l)
CAPTION_COUNT=$(ls -1 /workspace/lora_training/10_milan/*.txt 2>/dev/null | wc -l)

echo "✓ Found $IMAGE_COUNT images"
echo "✓ Found $CAPTION_COUNT captions"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "✗ No images found!"
    echo ""
    echo "Upload your training images to:"
    echo "  /workspace/lora_training/10_milan/"
    echo ""
    echo "Format: milan_selected_N.jpg + milan_selected_N.txt"
    exit 1
fi

if [ "$IMAGE_COUNT" -ne "$CAPTION_COUNT" ]; then
    echo "⚠️  Warning: Image count ($IMAGE_COUNT) != Caption count ($CAPTION_COUNT)"
    echo "   Make sure every .jpg has a matching .txt file!"
    exit 1
fi

# Step 2: Install Ostris AI Toolkit
echo ""
echo "Step 2: Installing Ostris AI Toolkit..."
cd /workspace

if [ ! -d "/workspace/ai-toolkit" ]; then
    echo "Cloning AI Toolkit..."
    git clone https://github.com/ostris/ai-toolkit.git
    cd ai-toolkit
    git submodule update --init --recursive
    pip install -r requirements.txt
    echo "✓ AI Toolkit installed"
else
    echo "✓ AI Toolkit already installed"
    cd ai-toolkit
fi

# Step 3: Create training config
echo ""
echo "Step 3: Creating training config..."

cat > /workspace/ai-toolkit/config/milan_lora.yaml << EOF
job: extension
config:
  name: milan_lora_v1
  process:
    - type: sd_trainer
      training_folder: /workspace/lora_training

      device: cuda:0

      # Model configuration (Wan 2.2)
      network:
        type: lora
        linear: 16
        linear_alpha: 16

      save:
        dtype: float16
        save_every: $SAVE_EVERY
        max_step_saves_to_keep: 10

      datasets:
        - folder_path: /workspace/lora_training/10_milan
          caption_ext: txt
          caption_dropout_rate: 0.05
          shuffle_tokens: false
          cache_latents_to_disk: true
          resolution: [1024, 1024]

      train:
        batch_size: 1
        steps: $TRAINING_STEPS
        gradient_accumulation_steps: 1
        train_unet: true
        train_text_encoder: false

        learning_rate: $LEARNING_RATE
        lr_scheduler: constant_with_warmup
        warmup_steps: 100

        optimizer: adamw8bit
        gradient_checkpointing: true
        noise_scheduler: flowmatch

      model:
        name_or_path: black-forest-labs/FLUX.1-dev
        is_flux: true
        quantize: true

      sample:
        sampler: flowmatch
        sample_every: 250
        width: 1024
        height: 1024
        prompts:
          - "$TRIGGER_WORD, woman, portrait, studio lighting, professional photo"
          - "$TRIGGER_WORD, woman, bikini, beach, smiling, full body"
          - "$TRIGGER_WORD, woman, nude, artistic, soft lighting"
        neg: "blurry, low quality, distorted"
        seed: 42
        walk_seed: true
        guidance_scale: 4
        sample_steps: 20

meta:
  name: milan_lora_v1
  version: 1.0
  description: Milan LoRA trained on 50-60 high quality images
EOF

echo "✓ Config created: /workspace/ai-toolkit/config/milan_lora.yaml"

# Step 4: Ready to train
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Dataset:"
echo "  • Images: $IMAGE_COUNT"
echo "  • Captions: $CAPTION_COUNT"
echo "  • Trigger word: '$TRIGGER_WORD'"
echo ""
echo "Training settings:"
echo "  • Steps: $TRAINING_STEPS"
echo "  • Learning rate: $LEARNING_RATE"
echo "  • Save every: $SAVE_EVERY steps"
echo "  • Expected checkpoints: $(($TRAINING_STEPS / $SAVE_EVERY))"
echo ""
echo "To start training:"
echo "  cd /workspace/ai-toolkit"
echo "  python run.py config/milan_lora.yaml"
echo ""
echo "Expected time: 60-90 minutes on RTX 4090"
echo "Output: /workspace/lora_training/milan_lora_v1/"
echo ""
