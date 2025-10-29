#!/bin/bash
# RunPod LoRA Training Setup Script
# This script automates the entire training setup on RunPod

set -e  # Exit on any error

echo "=========================================="
echo "  RunPod LoRA Training Setup"
echo "=========================================="

# Step 1: Verify GPU
echo -e "\n[1/6] Verifying GPU..."
nvidia-smi | head -n 15

# Step 2: Install dependencies
echo -e "\n[2/6] Installing dependencies..."
cd /workspace

if [ ! -d "kohya_ss" ]; then
    echo "  • Cloning Kohya_ss..."
    git clone https://github.com/bmaltais/kohya_ss.git
    cd kohya_ss
    echo "  • Installing requirements..."
    pip install -q -r requirements.txt
    cd /workspace
else
    echo "  ✓ Kohya_ss already installed"
fi

# Step 3: Upload dataset instructions
echo -e "\n[3/6] Checking for dataset..."
if [ ! -f "/workspace/jade_lora_dataset.zip" ]; then
    echo ""
    echo "⚠ Dataset not found!"
    echo ""
    echo "Please upload jade_lora_dataset.zip to RunPod:"
    echo ""
    echo "Option A - Using Web Terminal:"
    echo "  1. Click 'Upload' button (top right)"
    echo "  2. Select: /workspaces/ai/models/jade/jade_lora_dataset.zip"
    echo "  3. Upload to: /workspace/"
    echo ""
    echo "Option B - Using SCP from local machine:"
    echo "  scp -i ~/.ssh/id_ed25519 /workspaces/ai/models/jade/jade_lora_dataset.zip w76u042vchb6p3-64411d6d@ssh.runpod.io:/workspace/"
    echo ""
    echo "After uploading, run this script again:"
    echo "  bash runpod_setup.sh"
    echo ""
    exit 1
fi

echo "  ✓ Dataset found"

# Step 4: Extract dataset
echo -e "\n[4/6] Extracting dataset..."
if [ ! -d "/workspace/lora_training" ]; then
    unzip -q jade_lora_dataset.zip
    echo "  ✓ Extracted to /workspace/lora_training/"
else
    echo "  ✓ Already extracted"
fi

# Verify images
IMAGE_COUNT=$(ls -1 /workspace/lora_training/images/*.jpg 2>/dev/null | wc -l)
CAPTION_COUNT=$(ls -1 /workspace/lora_training/images/*.txt 2>/dev/null | wc -l)

echo "  • Found $IMAGE_COUNT images"
echo "  • Found $CAPTION_COUNT captions"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "  ✗ No images found in dataset!"
    exit 1
fi

# Step 5: Create training config
echo -e "\n[5/6] Creating training configuration..."

cat > /workspace/jade_config.toml << 'EOF'
[model_arguments]
pretrained_model_name_or_path = "stabilityai/stable-diffusion-xl-base-1.0"
v2 = false
v_parameterization = false

[dataset_arguments]
resolution = 1024
batch_size = 1
enable_bucket = true
min_bucket_reso = 256
max_bucket_reso = 1024
bucket_reso_steps = 64

[training_arguments]
output_dir = "/workspace/jade_lora_output"
output_name = "jade-v1"
save_model_as = "safetensors"
max_train_epochs = 10
learning_rate = 1e-4
lr_scheduler = "cosine"
optimizer_type = "AdamW8bit"
mixed_precision = "fp16"
save_precision = "fp16"
seed = 42
gradient_checkpointing = true
gradient_accumulation_steps = 1
clip_skip = 2

[network_arguments]
network_module = "networks.lora"
network_dim = 32
network_alpha = 16

[[datasets]]
[[datasets.subsets]]
image_dir = "/workspace/lora_training/images"
caption_extension = ".txt"
num_repeats = 10
shuffle_caption = false
keep_tokens = 2
EOF

echo "  ✓ Config saved to /workspace/jade_config.toml"

# Step 6: Ready to train
echo -e "\n[6/6] Setup Complete!"
echo ""
echo "=========================================="
echo "  Ready to Train!"
echo "=========================================="
echo ""
echo "Training Configuration:"
echo "  • Base Model: SDXL 1.0"
echo "  • Images: $IMAGE_COUNT"
echo "  • Captions: $CAPTION_COUNT"
echo "  • Epochs: 10"
echo "  • LoRA Rank: 32"
echo "  • Learning Rate: 1e-4"
echo "  • Trigger Word: 'jade woman'"
echo ""
echo "Estimated Time: 45-75 minutes"
echo "Estimated Cost: \$0.34-0.50"
echo ""
echo "To start training, run:"
echo "  bash /workspace/runpod_train.sh"
echo ""
