# RunPod Training Instructions

## Quick Start

### On RunPod (Web Terminal):

```bash
# 1. Clone the repo
cd /workspace
git clone <your-repo-url> ai
cd ai

# 2. Upload dataset
# Use "Upload" button to upload: models/jade/jade_lora_dataset.zip
# Upload to: /workspace/

# 3. Run setup
bash runpod_setup.sh

# 4. Start training
bash runpod_train.sh
```

---

## Detailed Steps

### Step 1: Connect to RunPod

1. Open RunPod dashboard
2. Click your pod
3. Click "Connect" → "Start Web Terminal"

### Step 2: Clone This Repo

```bash
cd /workspace
git clone https://github.com/<your-username>/ai.git
cd ai
```

### Step 3: Upload Dataset

**Option A - Web Terminal Upload:**
1. Click "Upload" button (usually top right)
2. Navigate to your local: `/workspaces/ai/models/jade/jade_lora_dataset.zip`
3. Upload to: `/workspace/` (not `/workspace/ai/`)

**Option B - SCP from Local Machine:**

On your LOCAL computer (different terminal):
```bash
scp -i ~/.ssh/id_ed25519 \
  /workspaces/ai/models/jade/jade_lora_dataset.zip \
  w76u042vchb6p3-64411d6d@ssh.runpod.io:/workspace/
```

### Step 4: Run Setup Script

```bash
bash runpod_setup.sh
```

This will:
- Verify GPU
- Install Kohya_ss
- Extract dataset
- Create training config
- Verify everything is ready

### Step 5: Start Training

```bash
bash runpod_train.sh
```

This takes **45-75 minutes**.

You can close the browser - training will continue.

To check progress, reconnect and run:
```bash
tail -f /workspace/kohya_ss/training.log
```

### Step 6: Download Model

Once training completes, download the model:

**Option A - Web Terminal:**
1. Navigate to `/workspace/jade_lora_output/`
2. Right-click `jade-v1.safetensors`
3. Click "Download"
4. Save to `/workspaces/ai/models/jade/` on your local machine

**Option B - SCP:**

On your LOCAL machine:
```bash
scp -i ~/.ssh/id_ed25519 \
  w76u042vchb6p3-64411d6d@ssh.runpod.io:/workspace/jade_lora_output/jade-v1.safetensors \
  /workspaces/ai/models/jade/
```

### Step 7: Stop Pod ⚠ IMPORTANT

**Don't forget to stop your pod!**

Go to RunPod dashboard → Click "Stop" or "Terminate"

Otherwise you'll keep paying $0.34/hour!

---

## Troubleshooting

### "Dataset not found"
- Make sure you uploaded `jade_lora_dataset.zip` to `/workspace/` (not `/workspace/ai/`)
- Run `ls /workspace/` to verify

### "Kohya_ss installation failed"
- Try manually: `cd /workspace && git clone https://github.com/bmaltais/kohya_ss.git`
- Then: `cd kohya_ss && pip install -r requirements.txt`

### "Out of memory"
- You need RTX 4090 or A100
- Check GPU: `nvidia-smi`
- If using smaller GPU, reduce batch_size in config

### Training stuck at 0%
- This is normal for first 5-10 minutes
- Model is downloading (SDXL base is 6GB)
- Wait patiently

---

## Training Details

- **Base Model:** Stable Diffusion XL 1.0
- **Training Method:** LoRA (Low-Rank Adaptation)
- **Epochs:** 10
- **Learning Rate:** 1e-4
- **LoRA Rank:** 32
- **Dataset:** 31 images + captions
- **Trigger Word:** "jade woman"

---

## After Training

Your LoRA model will be saved as:
```
/workspace/jade_lora_output/jade-v1.safetensors
```

You can use it with:
- ComfyUI
- Automatic1111 WebUI
- Fooocus
- Any SDXL-compatible interface

Example prompt:
```
jade woman, red dress, beach sunset, professional photography
```

---

## Cost Estimate

- **Training:** 45-75 minutes on RTX 4090
- **Cost:** $0.34-0.50 total
- **Per hour:** $0.34/hour

**Make sure to stop your pod after downloading the model!**
