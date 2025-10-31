# RunPod LoRA Training - Simple Instructions

## 🎯 COPY-PASTE COMMANDS (Actually Works!)

### Step 1: Create RunPod Pod

1. Go to https://runpod.io/console/pods
2. Click "Deploy"
3. Select: **RunPod Pytorch** template
4. GPU: **RTX 4090** (24GB VRAM) - $0.34/hour
5. Container Disk: **50GB**
6. Click **Deploy On-Demand**
7. Wait 30 seconds for pod to start
8. Click **Connect** → **Start Web Terminal**

---

### Step 2: Run These Commands in Web Terminal

**Copy-paste this entire block:**

```bash
# Clone repo
cd /workspace
git clone https://github.com/atlasreach/ai.git
cd ai

# Set AWS credentials (GET FROM YOUR .env FILE!)
export AWS_ACCESS_KEY_ID='YOUR_KEY_HERE'
export AWS_SECRET_ACCESS_KEY='YOUR_SECRET_HERE'

# Run training
bash runpod_train_sar_aitoolkit.sh
```

**IMPORTANT:** Replace `YOUR_KEY_HERE` with your actual AWS credentials from `.env`

---

### Step 3: Wait 30-60 Minutes

The script will:
1. ✅ Install ai-toolkit (5-10 min)
2. ✅ Download 7 SAR images from S3 (1 min)
3. ✅ Configure Flux training (30 sec)
4. ✅ Train LoRA (30-60 min)

**You'll see:**
```
Step 1: Installing ai-toolkit...
✓ ai-toolkit installed

Step 2: Downloading SAR images from S3...
✓ Downloaded 7 images
✓ Downloaded 7 captions

Step 3: Creating training config...
✓ Config created

Starting Training
Steps: 1000 (saves every 200)
Time: ~30-60 minutes
```

---

### Step 4: Download Your LoRA

When training finishes:

```bash
# Check output
ls -lh /workspace/ai-toolkit/output/sar_flux_lora/

# You should see:
# sar_flux_lora_000000200.safetensors  (checkpoint at 200 steps)
# sar_flux_lora_000000400.safetensors  (checkpoint at 400 steps)
# ...
# sar_flux_lora_000001000.safetensors  (FINAL - use this one!)
```

**Download via Web Terminal:**
1. Navigate to `/workspace/ai-toolkit/output/sar_flux_lora/`
2. Right-click `sar_flux_lora_000001000.safetensors`
3. Click **Download**

---

## 🐛 Troubleshooting

### "AWS credentials not set"
```bash
# Make sure you ran:
export AWS_ACCESS_KEY_ID='your-actual-key'
export AWS_SECRET_ACCESS_KEY='your-actual-secret'

# Test with:
aws s3 ls s3://destinty-workflow-1761724503/
```

### "No images downloaded"
```bash
# Check S3 bucket:
aws s3 ls s3://destinty-workflow-1761724503/results/nsfw/source_1/enhanced/

# Should show: sar-s1-t001-nsfw-enhanced.jpg, etc.
```

### "CUDA out of memory"
- You need 24GB VRAM minimum
- Make sure you selected RTX 4090 or A40

### "Package installation fails"
```bash
# Start fresh:
cd /workspace
rm -rf ai-toolkit ai
git clone https://github.com/atlasreach/ai.git
cd ai
bash runpod_train_sar_aitoolkit.sh
```

---

## 💰 Cost

**Total:** ~$0.35-0.60
- Setup: 10 min × $0.34/hr = $0.06
- Training: 45 min × $0.34/hr = $0.26
- Download: 5 min × $0.34/hr = $0.03

**⚠️ REMEMBER: Stop your pod when done to avoid charges!**

---

## 📝 What You Get

**Output:** `sar_flux_lora_000001000.safetensors` (~50-100MB)

**Use in:**
- ComfyUI
- Automatic1111
- Forge
- Any Flux.1-dev workflow

**Trigger word:** `sar`

**Example prompts:**
```
sar woman, portrait, soft lighting, photorealistic
sar woman, full body, studio photography, 8k
sar woman, red dress, beach sunset, professional photo
```

---

## ✅ That's It!

Three steps:
1. Create RunPod pod
2. Copy-paste commands
3. Download LoRA

No complex setup, no dependency hell, just works.
