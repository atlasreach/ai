# RunPod LoRA Training Setup for SAR Model

Quick guide to train a LoRA model on RunPod using images from S3.

## 🚀 Quick Start on RunPod

### 1. Launch RunPod Instance

- Go to https://runpod.io
- Select: **RunPod Pytorch** template
- GPU: RTX 4090 or A100 (recommended)
- Storage: 50GB minimum

### 2. Set AWS Credentials

**COPY THIS ONE COMMAND** (get keys from your local `.env` file):

```bash
export AWS_ACCESS_KEY_ID='your_key_here' AWS_SECRET_ACCESS_KEY='your_secret_here' AWS_REGION='us-east-2'
```

Replace `your_key_here` and `your_secret_here` with your actual AWS credentials.

### 3. Clone Repository

```bash
cd /workspace
git clone https://github.com/YOUR_USERNAME/ai.git
cd ai
```

### 4. Download Dataset from S3

```bash
bash runpod_prepare_sar_from_s3.sh
```

This downloads all enhanced images + captions for the "sar" model from S3.

### 5. Setup Training Environment

```bash
bash runpod_setup_sar.sh
```

This installs Kohya_ss and prepares everything for training.

### 6. Start Training

```bash
bash /workspace/train_sar.sh
```

Training takes 50-100 minutes for 10 epochs.

### 7. Download Your LoRA

Once complete, download:
```
/workspace/sar_lora_output/sar-v1.safetensors
```

---

## 📊 Training Details

- **Base Model**: Stable Diffusion XL 1.0
- **Trigger Word**: `sar woman`
- **Resolution**: 1024x1024
- **Epochs**: 10
- **LoRA Rank**: 32
- **Learning Rate**: 1e-4

---

## 💰 Estimated Costs

| GPU | $/hour | Time | Total Cost |
|-----|--------|------|------------|
| RTX 4090 | $0.44 | 60 min | ~$0.44 |
| A100 | $1.89 | 45 min | ~$1.42 |

---

## 🔧 Troubleshooting

### No images downloaded from S3

```bash
# Check if images exist in S3
aws s3 ls s3://destinty-workflow-1761724503/results/nsfw/ --recursive | grep sar

# Verify credentials
aws s3 ls
```

### Out of memory

Reduce batch size in `/workspace/sar_config.toml`:
```toml
batch_size = 1  # Already at minimum
```

Or use gradient accumulation:
```toml
gradient_accumulation_steps = 2
```

### Training too slow

- Use RTX 4090 or A100
- Enable xformers (already enabled)
- Reduce resolution to 768 (edit config)

---

## 📁 File Structure

```
/workspace/
├── ai/                              # Git repo
│   ├── runpod_prepare_sar_from_s3.sh  # Download from S3
│   ├── runpod_setup_sar.sh            # Setup environment
│   └── models/sar/                    # Model config
├── lora_training/
│   ├── images/                      # Training images + captions
│   └── dataset_config.json          # Dataset metadata
├── kohya_ss/                        # Training framework
├── sar_config.toml                  # Training config
├── train_sar.sh                     # Training script
└── sar_lora_output/
    └── sar-v1.safetensors          # Final LoRA model
```

---

## ✅ What Gets Downloaded

From S3 bucket: `destinty-workflow-1761724503`

- `results/nsfw/source_1/enhanced/sar-*.jpg` - Enhanced images
- `results/nsfw/source_1/enhanced/sar-*.txt` - Captions
- `results/nsfw/source_2/enhanced/sar-*.jpg` - Enhanced images
- `results/nsfw/source_2/enhanced/sar-*.txt` - Captions

Expected: ~14 images (2 sources × 7 targets)

---

## 🎯 Using Your Trained LoRA

After downloading `sar-v1.safetensors`:

1. Place in ComfyUI: `models/loras/`
2. Or Automatic1111: `models/Lora/`

**Prompt:**
```
sar woman, portrait, studio lighting, professional photography
```

**LoRA Weight:** 0.7-1.0

---

Last updated: 2025-10-29
