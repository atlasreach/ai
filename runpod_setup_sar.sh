#!/bin/bash
# RunPod LoRA Training Setup Script for SAR model
# This script automates the entire training setup on RunPod

set -e  # Exit on any error

echo "=========================================="
echo "  RunPod LoRA Training Setup (SAR)"
echo "=========================================="

# Step 1: Verify GPU
echo -e "\n[1/5] Verifying GPU..."
nvidia-smi | head -n 15

# Step 2: Install dependencies
echo -e "\n[2/5] Installing dependencies..."
cd /workspace

if [ ! -d "kohya_ss" ]; then
    echo "  • Cloning Kohya_ss..."
    git clone https://github.com/bmaltais/kohya_ss.git
    cd kohya_ss
    echo "  • Cloning sd-scripts submodule..."
    git submodule update --init --recursive
    echo "  • Installing requirements..."
    pip install -q -r requirements.txt
    cd /workspace
else
    echo "  ✓ Kohya_ss already installed"
fi

# Step 3: Verify dataset exists
echo -e "\n[3/5] Verifying dataset..."
if [ ! -d "/workspace/lora_training" ]; then
    echo "  ✗ Dataset not found!"
    echo "  Run: bash /workspace/ai/runpod_prepare_sar_from_s3.sh"
    exit 1
fi

IMAGE_COUNT=$(ls -1 /workspace/lora_training/images/*.jpg 2>/dev/null | wc -l)
CAPTION_COUNT=$(ls -1 /workspace/lora_training/images/*.txt 2>/dev/null | wc -l)

echo "  • Found $IMAGE_COUNT images"
echo "  • Found $CAPTION_COUNT captions"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "  ✗ No images found in dataset!"
    exit 1
fi

# Step 4: Create training config
echo -e "\n[4/5] Creating training configuration..."

cat > /workspace/sar_config.toml << 'EOF'
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
output_dir = "/workspace/sar_lora_output"
output_name = "sar-v1"
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

echo "  ✓ Config saved to /workspace/sar_config.toml"

# Step 5: Create training script
echo -e "\n[5/5] Creating training script..."

cat > /workspace/train_sar.sh << 'EOF'
#!/bin/bash
set -e

cd /workspace/kohya_ss

echo "=========================================="
echo "  Starting LoRA Training: SAR"
echo "=========================================="

python sdxl_train_network.py \
    --pretrained_model_name_or_path="stabilityai/stable-diffusion-xl-base-1.0" \
    --train_data_dir="/workspace/lora_training/images" \
    --output_dir="/workspace/sar_lora_output" \
    --output_name="sar-v1" \
    --save_model_as="safetensors" \
    --prior_loss_weight=1.0 \
    --max_train_epochs=10 \
    --learning_rate=1e-4 \
    --optimizer_type="AdamW8bit" \
    --xformers \
    --mixed_precision="fp16" \
    --cache_latents \
    --gradient_checkpointing \
    --save_every_n_epochs=2 \
    --network_module="networks.lora" \
    --network_dim=32 \
    --network_alpha=16 \
    --resolution=1024 \
    --train_batch_size=1 \
    --lr_scheduler="cosine" \
    --caption_extension=".txt" \
    --shuffle_caption \
    --keep_tokens=2 \
    --bucket_reso_steps=64 \
    --min_bucket_reso=256 \
    --max_bucket_reso=1024

echo ""
echo "=========================================="
echo "  Training Complete!"
echo "=========================================="
echo ""
echo "LoRA saved to: /workspace/sar_lora_output/sar-v1.safetensors"
echo ""
echo "Download with:"
echo "  scp or use RunPod web interface"
echo ""
EOF

chmod +x /workspace/train_sar.sh
echo "  ✓ Training script created: /workspace/train_sar.sh"

# Ready to train
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Training Configuration:"
echo "  • Base Model: SDXL 1.0"
echo "  • Images: $IMAGE_COUNT"
echo "  • Captions: $CAPTION_COUNT"
echo "  • Epochs: 10"
echo "  • LoRA Rank: 32"
echo "  • Learning Rate: 1e-4"
echo "  • Trigger Word: 'sar woman'"
echo ""
echo "Estimated Time: ~5-10 minutes per epoch"
echo "Total: 50-100 minutes for 10 epochs"
echo ""
echo "To start training, run:"
echo "  bash /workspace/train_sar.sh"
echo ""
