# LoRA Training Guide - RunPod Setup

## 📋 Overview

Train a LoRA model of your character using the enhanced images + Grok captions you've already generated.

**What you'll need:**
- Enhanced images (1024x1024) ✓ Already have!
- Captions (.txt files) ✓ Already have!
- RunPod account (~$3 for training)
- 1-2 hours

---

## 🚀 Step 1: Prepare Training Dataset

### A. Create Dataset Folder

```bash
python scripts/prepare_lora_dataset.py jade
```

This will:
1. Copy all enhanced images to `models/jade/lora_training/`
2. Copy matching captions
3. Create config files
4. Package as `jade_dataset.zip`

**Output:**
```
models/jade/lora_training/
├── images/
│   ├── jade-s1-t1-nsfw-enhanced.jpg
│   ├── jade-s1-t2-nsfw-enhanced.jpg
│   └── ... (32 images, all 1024x1024)
├── captions/
│   ├── jade-s1-t1-nsfw-enhanced.txt
│   ├── jade-s1-t2-nsfw-enhanced.txt
│   └── ... (32 captions)
└── dataset_config.json
```

### B. Verify Dataset Quality

```bash
python scripts/verify_dataset.py models/jade/lora_training/
```

Checks:
- ✓ All images are 1024x1024
- ✓ Every image has a matching caption
- ✓ Captions mention trigger word "jade woman"
- ✓ Minimum 20 images (you have 32!)

---

## 🖥️ Step 2: Set Up RunPod

### A. Create RunPod Account

1. Go to: https://runpod.io
2. Sign up (free account)
3. Add credit ($10 minimum, gets you 10+ training runs)

### B. Choose GPU Template

**Recommended:** `RunPod Pytorch 2.4` with **RTX 4090** ($0.34/hour)

**Options:**
- RTX 4090: $0.34/hr (fastest, best value)
- RTX 3090: $0.24/hr (slower but cheaper)
- A6000: $0.79/hr (overkill for LoRA)

**For your dataset (32 images):**
- Training time: ~1 hour
- **Cost: ~$0.34-0.50**

### C. Deploy Pod

```
1. Template: RunPod Pytorch 2.4
2. GPU: RTX 4090 (1x)
3. Container Disk: 50GB
4. Volume: Not needed
5. Click "Deploy On-Demand"
```

Wait 30-60 seconds for pod to start.

---

## 🎨 Step 3: Upload Dataset & Train

### A. Connect to Pod

```bash
# Get SSH command from RunPod dashboard
ssh root@<pod-ip> -p <port> -i ~/.ssh/runpod_key
```

Or use **JupyterLab** (easier):
- Click "Connect" → "JupyterLab"
- Opens in browser

### B. Install Kohya Training Scripts

```bash
cd /workspace
git clone https://github.com/bmaltais/kohya_ss.git
cd kohya_ss
pip install -r requirements.txt
```

### C. Upload Your Dataset

**Option 1: SCP (from your machine)**
```bash
scp jade_dataset.zip root@<pod-ip>:/workspace/
```

**Option 2: Direct from S3**
```bash
# On RunPod
aws s3 cp s3://jade-workflow-xxx/lora_training/jade_dataset.zip .
unzip jade_dataset.zip -d /workspace/jade_training
```

### D. Configure Training

Create `jade_config.toml`:

```toml
[model_arguments]
pretrained_model_name_or_path = "stabilityai/stable-diffusion-xl-base-1.0"
v2 = false
v_parameterization = false

[dataset_arguments]
resolution = 1024
batch_size = 1
enable_bucket = true

[training_arguments]
output_dir = "/workspace/jade_lora"
output_name = "jade-v1"
save_model_as = "safetensors"

max_train_epochs = 10
learning_rate = 1e-4
lr_scheduler = "cosine"
optimizer_type = "AdamW8bit"

[dataset_config]
datasets = [
    { image_dir = "/workspace/jade_training/images",
      caption_extension = ".txt",
      num_repeats = 10 }
]

[lora_arguments]
network_dim = 32
network_alpha = 16
```

### E. Start Training

```bash
python train_network.py \
    --config_file jade_config.toml \
    --trigger_word "jade woman"
```

**Watch progress:**
```
Epoch 1/10 ... Loss: 0.15
Epoch 2/10 ... Loss: 0.12
Epoch 3/10 ... Loss: 0.09
...
Epoch 10/10 ... Loss: 0.04
✓ Training complete!
```

**Time: ~45-75 minutes**

### F. Download Trained Model

```bash
# From your machine
scp root@<pod-ip>:/workspace/jade_lora/jade-v1.safetensors ./models/jade/
```

---

## 🎯 Step 4: Test Your LoRA

### A. Install ComfyUI (Local)

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt
```

### B. Load Your LoRA

```bash
# Copy to ComfyUI
cp models/jade/jade-v1.safetensors ComfyUI/models/loras/
```

### C. Generate Test Images

**Prompt examples:**
```
"jade woman, red dress, beach at sunset, professional photography"
"jade woman, lying on white bed, soft morning light, intimate pose"
"jade woman, black lingerie, standing pose, studio lighting"
```

**Settings:**
- Model: SDXL 1.0
- LoRA: jade-v1.safetensors (strength: 0.8-1.0)
- Steps: 25-30
- CFG: 7

---

## 💰 Cost Breakdown

| Item | Cost |
|------|------|
| RunPod GPU (1 hour) | $0.34 |
| Training dataset prep | Free |
| Testing locally | Free |
| **Total** | **~$0.34-0.50** |

**Compare to:**
- Replicate Flux Redux: $0.24 for 6 images (ongoing)
- Your LoRA: $0.34 once, infinite generations!

---

## 🔄 Step 5: Integrate into Workflow

### Option A: Add to Master.py (Phase 2)

```python
# After Step 4 (Captions)

# Step 5: Prepare LoRA Dataset
print("\n--- STEP 5: Preparing LoRA Training Dataset ---")
prepare_lora_dataset(model_name)
print("✓ Dataset ready for training")
print(f"📦 Upload to RunPod: models/{model_name}/lora_dataset.zip")
```

### Option B: Separate Script

```bash
python train_lora.py jade
# Automatically:
# 1. Prepares dataset
# 2. Uploads to RunPod
# 3. Starts training
# 4. Downloads model when done
```

---

## 📊 What's Next: Website Integration

Once trained, use your LoRA in a web app:

```
User Input: "jade woman, red dress, beach sunset"
    ↓
Backend (FastAPI + ComfyUI)
    ↓
Generate with jade-v1.safetensors LoRA
    ↓
Return 4-6 variations
    ↓
User picks favorites → Download
```

**See:** `WEBSITE_INTEGRATION_GUIDE.md`

---

## 🎯 Summary

**You already have everything needed!**
- ✅ Enhanced images (1024x1024, resized automatically now)
- ✅ Detailed Grok captions
- ✅ 32 training pairs (perfect amount)

**Next steps:**
1. Run `python scripts/prepare_lora_dataset.py jade`
2. Create RunPod account
3. Train (~1 hour, $0.34)
4. Download model
5. Generate unlimited variations!
