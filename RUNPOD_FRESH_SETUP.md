# 🚀 Fresh RunPod Setup - SAR LoRA Training

## Step 1: Create RunPod Instance

1. Go to https://runpod.io/console/pods
2. Click **"Deploy"**
3. Select: **RunPod Pytorch** template
4. GPU: **RTX 4090** (24GB VRAM) - $0.34/hour
5. Container Disk: **50GB**
6. Click **"Deploy On-Demand"**
7. Wait ~30 seconds for pod to start
8. Click **"Connect"** → **"Start Web Terminal"**

---

## Step 2: Copy-Paste This Into Terminal

```bash
# Create credentials file (get values from your local .env file!)
cat > /workspace/.runpod_env << 'EOF'
export AWS_ACCESS_KEY_ID='your-key-from-local-env'
export AWS_SECRET_ACCESS_KEY='your-secret-from-local-env'
EOF

# Clone repo and start training
cd /workspace
git clone https://github.com/atlasreach/ai.git
cd ai
bash runpod_train_sar_aitoolkit.sh
```

**Where to get credentials:** Check `/workspaces/ai/.env` on your local machine

**That's it!** Training will start automatically.

---

## What Happens Next

The script will:
1. ✅ Install ai-toolkit (~5-10 min)
2. ✅ Download 7 SAR images from S3 (~1 min)
3. ✅ Configure training (~30 sec)
4. ✅ Train LoRA for 1000 steps (~30-60 min)

**Progress:**
```
Step 1: Installing ai-toolkit...
  • Installing PyTorch 2.6.0 + CUDA 12.6...
  • Installing ai-toolkit dependencies...
✓ ai-toolkit installed

Step 2: Downloading SAR images from S3...
✓ Downloaded 7 images
✓ Downloaded 7 captions

Step 3: Creating training config...
✓ Config created

Starting Training
Steps: 1000 (saves every 200)
Time: ~30-60 minutes

sar_flux_lora:  20%|████▌              | 200/1000 [03:15<12:54,  1.03it/s]
```

---

## Step 3: Download Your LoRA

When training finishes:

```bash
# Check output
ls -lh /workspace/ai-toolkit/sar_flux_lora/

# You should see:
# sar_flux_lora_000000200.safetensors
# sar_flux_lora_000000400.safetensors
# sar_flux_lora_000000600.safetensors
# sar_flux_lora_000000800.safetensors
# sar_flux_lora_000001000.safetensors  ← Use this one!
```

**To download:**
1. In RunPod terminal, navigate to `/workspace/ai-toolkit/sar_flux_lora/`
2. Right-click on `sar_flux_lora_000001000.safetensors`
3. Click **Download**

---

## 💰 Cost Estimate

- Setup + Training: **45-60 minutes**
- Cost: **$0.25-0.35** (RTX 4090 @ $0.34/hour)

**⚠️ IMPORTANT:** Stop your pod when done to avoid charges!

---

## 🐛 Troubleshooting

### Training Failed or Interrupted?

Just run the script again - it will **resume automatically**:
```bash
cd /workspace/ai
bash runpod_train_sar_aitoolkit.sh
```

The script detects existing checkpoints and continues from where it left off.

### Need to Start Completely Fresh?

```bash
cd /workspace
rm -rf ai-toolkit ai sar_dataset
git clone https://github.com/atlasreach/ai.git
cd ai
bash runpod_train_sar_aitoolkit.sh
```

### Check Training Progress

If training is running in background:
```bash
# See latest checkpoint
ls -lh /workspace/ai-toolkit/sar_flux_lora/*.safetensors

# Monitor GPU usage
nvidia-smi
```

---

## 🎯 Using Your LoRA

**Trigger word:** `sar`

**Example prompts:**
```
sar woman, portrait, soft lighting, photorealistic, 8k
sar woman, full body, red dress, professional photography
sar woman, outdoor, natural lighting, smiling, high detail
```

**Compatible with:**
- ComfyUI
- Automatic1111 WebUI
- Forge
- Any Flux.1-dev workflow

---

## ✅ Quick Reference

**One-command setup:**
```bash
cat > /workspace/.runpod_env << 'EOF'
export AWS_ACCESS_KEY_ID='your-key-from-local-env'
export AWS_SECRET_ACCESS_KEY='your-secret-from-local-env'
EOF
cd /workspace && git clone https://github.com/atlasreach/ai.git && cd ai && bash runpod_train_sar_aitoolkit.sh
```

**Remember:** Replace `your-key-from-local-env` and `your-secret-from-local-env` with actual values from `/workspaces/ai/.env`

**Resume training:**
```bash
cd /workspace/ai && bash runpod_train_sar_aitoolkit.sh
```

**Update script and resume:**
```bash
cd /workspace/ai && git pull && bash runpod_train_sar_aitoolkit.sh
```

---

That's it! Simple, reliable, and works from scratch every time. 🎉
