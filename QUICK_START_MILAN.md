# 🚀 MILAN TRAINING - QUICK START

## What You Need to Upload to RunPod:

1. **`milan_training_dataset.zip`** (9.2MB)
   - Location: `/workspaces/ai/models_2.0/milan/milan_training_dataset.zip`

2. **`milan_lora_config.yaml`** (training config)
   - Location: `/workspaces/ai/milan_lora_config.yaml`

---

## 📋 Step-by-Step Commands (Copy & Paste)

### 1️⃣ Setup (5 minutes)
```bash
# Extract dataset
cd /workspace
unzip milan_training_dataset.zip

# Install Ostris AI Toolkit
git clone https://github.com/ostris/ai-toolkit.git
cd ai-toolkit
pip install -r requirements.txt
git submodule update --init --recursive

# Copy your config
cp /workspace/milan_lora_config.yaml config/milan_lora.yaml
```

### 2️⃣ Start Training (90 minutes)
```bash
cd /workspace/ai-toolkit
python run.py config/milan_lora.yaml
```

### 3️⃣ Download Results
```bash
# Checkpoints saved to:
/workspace/output/milan_lora_v1/

# Best checkpoint (based on Sara 2.0):
milan_lora_v1_000001500.safetensors
```

---

## ⚙️ Training Settings (Same as Sara 2.0)

```
Steps: 1500
Learning Rate: 1e-4
Batch Size: 1
LoRA Rank: 16
Model: FLUX.1-dev
Dataset: 54 images (18 bikini + 18 nude + 18 explicit)
```

---

## ⏱️ Timeline

- **Setup**: 5-10 minutes
- **Training**: 60-90 minutes
- **Download**: 2-5 minutes
- **Total**: ~2 hours

---

## 💾 Checkpoints Saved

Every 250 steps:
- ✅ 250 steps
- ✅ 500 steps
- ✅ 750 steps
- ✅ 1000 steps
- ✅ 1250 steps
- ⭐ **1500 steps** (BEST - use this one!)

---

## 🧪 Test Prompts

After downloading your LoRA, test with:

**SFW:**
```
Milan, woman, bikini, beach, smiling, full body
```

**Nude:**
```
Milan, woman, nude, bedroom, soft lighting
```

**Explicit:**
```
Milan, woman, nude, giving blowjob, POV
```

---

## 💰 Cost

- RTX 4090: ~$0.75
- RTX A6000: ~$1.05

---

## ❓ Help

**Training stuck?**
- Wait 2-3 minutes (loading model)
- Check: `nvidia-smi`

**Out of memory?**
- Already at minimum settings
- Try smaller GPU or contact support

**Need the full guide?**
- Read: `RUNPOD_OSTRIS_SETUP.md`

---

## ✅ Checklist

- [ ] Upload `milan_training_dataset.zip` to RunPod
- [ ] Upload `milan_lora_config.yaml` to RunPod
- [ ] Extract dataset
- [ ] Install Ostris AI Toolkit
- [ ] Copy config file
- [ ] Run training command
- [ ] Wait 90 minutes ☕
- [ ] Download checkpoint 1500
- [ ] Test in ComfyUI
- [ ] Enjoy! 🎉

---

**That's it! Simple as that!** 🚀
