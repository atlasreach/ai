# RunPod + Ostris AI Toolkit Setup for Milan Training

## 🚀 Quick Start Guide

This is the EXACT setup that worked for Sara 2.0!

---

## Step 1: Start RunPod Instance

1. Go to https://runpod.io
2. Select **"Secure Cloud"** or **"Community Cloud"**
3. Choose GPU: **RTX 4090** or **RTX A6000** (recommended)
4. Select template: **"PyTorch 2.0"** or **"RunPod Pytorch"**
5. Start instance

**Cost**: ~$0.40-0.70/hour depending on GPU

---

## Step 2: Upload Your Training Dataset

### Option A: Web Upload (Easiest)
1. In RunPod, click **"Files"** tab
2. Click **"Upload"**
3. Upload: `/workspaces/ai/models_2.0/milan/milan_training_dataset.zip`
4. Wait for upload to complete

### Option B: SCP/SFTP
```bash
# From your local machine:
scp models_2.0/milan/milan_training_dataset.zip your-runpod-ssh:/workspace/
```

---

## Step 3: Connect to Terminal

Click **"Connect"** → **"Start Web Terminal"** or use SSH

---

## Step 4: Extract Dataset

```bash
cd /workspace
unzip milan_training_dataset.zip
ls training_dataset/  # Should show 54 images + 54 txt files
```

---

## Step 5: Install Ostris AI Toolkit

```bash
cd /workspace

# Clone the toolkit
git clone https://github.com/ostris/ai-toolkit.git
cd ai-toolkit

# Install dependencies
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Initialize submodules
git submodule update --init --recursive
```

---

## Step 6: Create Training Config

```bash
# Create config directory if it doesn't exist
mkdir -p config

# Create Milan config file
nano config/milan_lora.yaml
```

**Paste this config** (press Ctrl+O to save, Ctrl+X to exit):

```yaml
job: extension
config:
  name: milan_lora_v1
  process:
    - type: sd_trainer
      training_folder: /workspace/output

      device: cuda:0

      # Model settings
      network:
        type: lora
        linear: 16
        linear_alpha: 16

      # Save settings
      save:
        dtype: float16
        save_every: 250
        max_step_saves_to_keep: 10

      # Dataset configuration
      datasets:
        - folder_path: /workspace/training_dataset
          caption_ext: txt
          caption_dropout_rate: 0.05
          shuffle_tokens: false
          cache_latents_to_disk: true
          resolution: [1024, 1024]

      # Training parameters (SAME AS SARA 2.0)
      train:
        batch_size: 1
        steps: 1500
        gradient_accumulation_steps: 1
        train_unet: true
        train_text_encoder: false

        learning_rate: 1e-4
        lr_scheduler: constant

        optimizer: adamw8bit
        gradient_checkpointing: true
        noise_scheduler: flowmatch

      # Base model (Flux.1-dev - same as Sara)
      model:
        name_or_path: black-forest-labs/FLUX.1-dev
        is_flux: true
        quantize: true

      # Sample images during training
      sample:
        sampler: flowmatch
        sample_every: 250
        width: 1024
        height: 1024
        prompts:
          - "Milan, woman, portrait, professional photo"
          - "Milan, woman, bikini, beach, full body"
          - "Milan, woman, nude, bedroom, soft lighting"
        neg: "blurry, low quality"
        seed: 42
        guidance_scale: 4
        sample_steps: 20

meta:
  name: milan_lora_v1
  version: 1.0
```

---

## Step 7: Verify Setup

```bash
# Check dataset
ls /workspace/training_dataset/*.jpg | wc -l  # Should show 54
ls /workspace/training_dataset/*.txt | wc -l  # Should show 54

# Check config
cat config/milan_lora.yaml
```

---

## Step 8: Start Training! 🚀

```bash
cd /workspace/ai-toolkit
python run.py config/milan_lora.yaml
```

**Expected output:**
```
Loading FLUX.1-dev model...
Found 54 training images
Starting training for 1500 steps...
Step 1/1500 | Loss: 0.xxx
Step 2/1500 | Loss: 0.xxx
...
```

---

## Step 9: Monitor Training

Training will:
- **Save checkpoints** every 250 steps → `/workspace/output/milan_lora_v1/`
- **Generate sample images** every 250 steps to see progress
- **Take 60-90 minutes** on RTX 4090

**Checkpoints saved:**
- `milan_lora_v1_000000250.safetensors`
- `milan_lora_v1_000000500.safetensors`
- `milan_lora_v1_000000750.safetensors`
- `milan_lora_v1_000001000.safetensors`
- `milan_lora_v1_000001250.safetensors`
- `milan_lora_v1_000001500.safetensors` ⭐ **BEST ONE** (based on Sara 2.0)

---

## Step 10: Download Your LoRA

After training completes:

```bash
cd /workspace/output/milan_lora_v1/
ls -lh *.safetensors
```

### Download via Web Interface:
1. Click **"Files"** tab in RunPod
2. Navigate to `/workspace/output/milan_lora_v1/`
3. Download `milan_lora_v1_000001500.safetensors`

### Download via SCP:
```bash
# From your local machine:
scp your-runpod-ssh:/workspace/output/milan_lora_v1/milan_lora_v1_000001500.safetensors ~/Downloads/
```

---

## 🎨 Testing Your LoRA

### In ComfyUI:

1. Copy `milan_lora_v1_000001500.safetensors` to `ComfyUI/models/loras/`

2. Use your existing Sara workflow (`comfyui_workflow_sara.json`) as template

3. **Changes needed:**
   - Replace Sara LoRA → Milan LoRA
   - Change trigger word: "Sara" → "Milan"
   - Test with different prompts!

### Test Prompts:

**SFW Test:**
```
Milan, woman, bikini, beach, smiling, full body, natural lighting, professional photo
```

**Artistic Nude:**
```
Milan, woman, nude, sitting on bed, bedroom, soft lighting, artistic, high quality
```

**Explicit:**
```
Milan, woman, nude, giving blowjob, POV, bedroom lighting, detailed
```

---

## 💡 Troubleshooting

### "CUDA out of memory"
```bash
# Reduce batch size in config
batch_size: 1  # Already set to minimum
gradient_accumulation_steps: 2  # Try this
```

### "Module not found"
```bash
cd /workspace/ai-toolkit
pip install -r requirements.txt --upgrade
```

### "Can't find training images"
```bash
# Check paths
ls /workspace/training_dataset/milan_selected_1.jpg
cat /workspace/training_dataset/milan_selected_1.txt
```

### Training stuck at 0%
- Wait 2-3 minutes (loading model takes time)
- Check GPU usage: `nvidia-smi`

---

## 📊 Expected Results

**Based on Sara 2.0 training:**
- Sara: 24 images, 1500 steps, "pretty good" results
- **Milan: 54 images, 1500 steps, MUCH BETTER expected!**

**Why Milan should be better:**
- 2.25x more training data
- 3-4x more detailed captions
- Better body orientation understanding
- More facial expression variety
- Balanced across all use cases

---

## ⏱️ Training Timeline

| Step | Time | What's Happening |
|------|------|------------------|
| 0-250 | 10-15 min | Learning basic features |
| 250-500 | 10-15 min | Refining face/body |
| 500-750 | 10-15 min | Learning poses |
| 750-1000 | 10-15 min | Improving details |
| 1000-1250 | 10-15 min | Fine-tuning |
| 1250-1500 | 10-15 min | Final polish ✨ |
| **Total** | **60-90 min** | **Complete!** |

---

## 🎯 Which Checkpoint to Use?

**Test all checkpoints** starting from 1000:
1. Test 1000, 1250, and 1500
2. Generate same prompt with each
3. Pick the one that looks best!

**Sara 2.0's best was 1500** - Milan will probably be similar!

---

## 💰 Cost Estimate

- **RTX 4090**: ~$0.50/hour × 1.5 hours = **$0.75**
- **RTX A6000**: ~$0.70/hour × 1.5 hours = **$1.05**

Total cost: **Less than $2!**

---

## 🚀 Quick Command Summary

```bash
# 1. Upload dataset to RunPod
# 2. Extract
cd /workspace && unzip milan_training_dataset.zip

# 3. Install toolkit
git clone https://github.com/ostris/ai-toolkit.git
cd ai-toolkit
pip install -r requirements.txt
git submodule update --init --recursive

# 4. Create config (copy from above)
nano config/milan_lora.yaml

# 5. START TRAINING!
python run.py config/milan_lora.yaml

# 6. Wait 60-90 minutes ☕

# 7. Download best checkpoint
# /workspace/output/milan_lora_v1/milan_lora_v1_000001500.safetensors
```

---

**That's it! You're ready to train Milan!** 🎉

Good luck - this should give you amazing results! 🚀
