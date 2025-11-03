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

**Option 1: Quick Setup (one-time credentials)**
```bash
cd /workspace
git clone https://github.com/atlasreach/ai.git
cd ai

# Get these from /workspaces/ai/.env file (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
export AWS_ACCESS_KEY_ID='paste-from-env-file'
export AWS_SECRET_ACCESS_KEY='paste-from-env-file'

bash runpod_train_sar_aitoolkit.sh
```

**Option 2: Persistent Setup (saves credentials - recommended)**
```bash
cd /workspace
git clone https://github.com/atlasreach/ai.git

# Create credentials file (get values from /workspaces/ai/.env)
cat > /workspace/.runpod_env << 'EOF'
export AWS_ACCESS_KEY_ID='paste-from-env-file'
export AWS_SECRET_ACCESS_KEY='paste-from-env-file'
EOF

# Now run training (will auto-load credentials!)
cd ai
bash runpod_train_sar_aitoolkit.sh
```

**✨ NEW:** The script now auto-loads credentials from `/workspace/.runpod_env` if it exists!

**Where to get credentials:** Check your local `/workspaces/ai/.env` file for `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

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

The script will show you helpful error messages. Get your credentials from `/workspaces/ai/.env` and either:

**Quick fix:**
```bash
export AWS_ACCESS_KEY_ID='your-key-from-env'
export AWS_SECRET_ACCESS_KEY='your-secret-from-env'
bash runpod_train_sar_aitoolkit.sh
```

**Or create credentials file (persists across sessions):**
```bash
cat > /workspace/.runpod_env << 'EOF'
export AWS_ACCESS_KEY_ID='your-key-from-env'
export AWS_SECRET_ACCESS_KEY='your-secret-from-env'
EOF
bash runpod_train_sar_aitoolkit.sh
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
