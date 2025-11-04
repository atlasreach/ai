# Milan LoRA Training Guide

## 🎯 Summary: Sara 2.0 vs Milan Training

### Sara 2.0 (Your Previous Training)
- **Images**: 24 total (mixed categories)
- **Captions**: Short, simple format
- **Quality**: "Pretty good" results
- **Training**: Ostris AI Toolkit on Wan 2.2
- **Steps**: 1500 (best checkpoint)
- **Result**: `sara_000001500.safetensors`

### Milan v1.0 (Recommended Approach)
- **Images**: 54 selected (from 137 total)
- **Captions**: MUCH more detailed (3-4x longer)
- **Expected Quality**: Significantly better than Sara!
- **Training**: Same setup (Ostris AI Toolkit + Wan 2.2)
- **Steps**: 1500 (proven sweet spot)

---

## 📊 Key Improvements Over Sara Training

### 1. **Better Caption Quality** ✨
**Sara captions were basic:**
```
Sara, fair skin, brown ponytail, gray sweatshirt, lying on couch, smiling, living room, sfw
```

**Milan captions are super detailed:**
```
Milan, tan skin, long straight brown hair, full lips, light blue lingerie,
ass visible, on all fours, ass facing camera, head turned looking back over shoulder,
playful, side view, bedroom with wooden furniture, soft natural lighting, sfw
```

**Impact**:
- Better body orientation understanding (ass vs head direction)
- More facial expression detail (playful, seductive, naughty)
- Explicit position details for NSFW content

### 2. **Optimized Dataset Size**
- Sara: 24 images (might have been too small)
- Milan: 54 images (2.25x more data)
- Why 54? Sweet spot between variety and training time
- All images scored 88+ (top quality only!)

### 3. **Perfect Category Balance**
```
Bikini/SFW:  18 images (33%) - Instagram/TikTok style
Nude:        18 images (33%) - Artistic nudes
Explicit:    18 images (33%) - Adult content
```

This gives Milan versatility across all use cases!

---

## 📁 What's Ready for You

### 1. **Training Dataset** ✅
- **Location**: `/workspaces/ai/models_2.0/milan/training_dataset/`
- **Files**: 54 images + 54 captions
- **Zip file**: `milan_training_dataset.zip` (9.2MB)
- **Format**: `milan_selected_1.jpg` + `milan_selected_1.txt` (etc.)

### 2. **Training Script** ✅
- **File**: `runpod_train_milan.sh`
- **Pre-configured** for Ostris AI Toolkit + Wan 2.2
- **Settings**: Same as Sara (proven to work!)

### 3. **Quality Rankings** ✅
All 137 images ranked and saved:
- `bikini_ranking.json` (45 images)
- `nude_ranking.json` (42 images)
- `explicit_ranking.json` (50 images)

---

## 🚀 How to Train Milan on RunPod

### Step 1: Upload Dataset to RunPod
```bash
# Option A: SCP (if you have SSH access)
scp /workspaces/ai/models_2.0/milan/milan_training_dataset.zip runpod:/workspace/

# Option B: Upload via RunPod web interface
# Go to RunPod → Files → Upload → milan_training_dataset.zip
```

### Step 2: Extract on RunPod
```bash
cd /workspace
unzip milan_training_dataset.zip
mv training_dataset lora_training/10_milan

# Verify
ls lora_training/10_milan/*.jpg | wc -l  # Should show 54
ls lora_training/10_milan/*.txt | wc -l  # Should show 54
```

### Step 3: Upload Training Script
```bash
# Upload runpod_train_milan.sh to /workspace/
scp /workspaces/ai/runpod_train_milan.sh runpod:/workspace/
```

### Step 4: Run Training
```bash
cd /workspace
chmod +x runpod_train_milan.sh
bash runpod_train_milan.sh

# Then follow the prompts to start training:
cd /workspace/ai-toolkit
python run.py config/milan_lora.yaml
```

### Step 5: Monitor Training
Training will save checkpoints every 250 steps:
- `milan_lora_v1_000000250.safetensors`
- `milan_lora_v1_000000500.safetensors`
- `milan_lora_v1_000000750.safetensors`
- `milan_lora_v1_000001000.safetensors`
- `milan_lora_v1_000001250.safetensors`
- `milan_lora_v1_000001500.safetensors` ⭐ **Best checkpoint**

**Expected time**: 60-90 minutes on RTX 4090

---

## 🎨 Testing Your Trained Model

### In ComfyUI:
1. Copy `milan_lora_v1_000001500.safetensors` to ComfyUI/models/loras/
2. Use your existing `comfyui_workflow_sara.json` as template
3. Replace Sara LoRA with Milan LoRA
4. Change trigger word from "Sara" to "Milan"

### Test Prompts:
```
SFW Test:
"Milan, woman, bikini, beach, smiling, full body, natural lighting"

Nude Test:
"Milan, woman, nude, sitting, bedroom, soft lighting, artistic"

Explicit Test:
"Milan, woman, nude, giving blowjob, POV, bedroom lighting"
```

---

## 📈 Expected Results

Based on Sara 2.0 performance + improvements:

**Sara 2.0**: "Pretty good" with 24 images + basic captions

**Milan v1.0 Expected**: **Much better!**
- 2.25x more training data
- 3-4x more detailed captions
- Better body orientation understanding
- More facial expression variety
- Better explicit content understanding

**Why Milan should be better:**
1. More images = more variety to learn from
2. Detailed captions = better prompt understanding
3. Balanced categories = versatile for all use cases
4. Higher quality images (all 88+ score)

---

## 🔧 Training Settings (Same as Sara)

```yaml
Steps: 1500
Learning Rate: 1e-4
Batch Size: 1
LoRA Rank: 16
Optimizer: AdamW 8bit
Scheduler: Constant with warmup (100 steps)
Resolution: 1024x1024
Save Every: 250 steps
```

These settings worked for Sara, so we're keeping them!

---

## 🎯 Top 10 Images in Training Set

| # | Score | Category | Original File | Caption Preview |
|---|-------|----------|---------------|-----------------|
| 1 | 92/100 | bikini | milan_bikini_18.jpg | ass visible, on all fours, ass facing camera... |
| 2 | 92/100 | bikini | milan_bikini_23.jpg | red bikini, back view, looking over shoulder... |
| 3 | 92/100 | bikini | milan_bikini_29.jpg | floral swimsuit, confident pose... |
| 4 | 92/100 | bikini | milan_bikini_30.jpg | black bikini, beach setting... |
| 5 | 92/100 | bikini | milan_bikini_33.jpg | red bikini, full body shot... |
| 19 | 92/100 | nude | milan_nude_26.jpg | pussy visible, seductive look... |
| 20 | 92/100 | nude | milan_nude_27.jpg | sitting pose, bedroom eyes... |
| 37 | 92/100 | explicit | milan_explicit_1.jpg | giving blowjob, cock in mouth, eyes up at camera... |
| 38 | 92/100 | explicit | milan_explicit_18.jpg | having sex, missionary, face of pleasure... |
| 39 | 92/100 | explicit | milan_explicit_19.jpg | riding cock, bouncing, moaning... |

Average score: **90.2/100** (all images are 88-92!)

---

## ❓ FAQ

**Q: Why 54 images instead of all 137?**
A: Quality over quantity! Sara had 24 and was "pretty good" - 54 top-quality images should be significantly better without overfitting.

**Q: Can I add more images later?**
A: Yes! Train v1.0 with 54, then try v1.1 with 70-80 if you want more variety.

**Q: Should I change any training settings?**
A: No! The Sara settings worked well. Only change if v1.0 doesn't meet expectations.

**Q: What if checkpoint 1500 isn't the best?**
A: Test checkpoints 1000, 1250, and 1500. Pick whichever looks best!

**Q: Can I train on a different base model?**
A: Yes, but Wan 2.2 worked for Sara. Flux.1-dev is also popular.

---

## 📌 Quick Reference

**Files Ready:**
- ✅ Training dataset: `milan_training_dataset.zip` (9.2MB)
- ✅ Training script: `runpod_train_milan.sh`
- ✅ 54 images selected (all 88+ score)
- ✅ Detailed captions for all images

**Next Steps:**
1. Upload zip to RunPod
2. Run setup script
3. Start training
4. Wait 60-90 minutes
5. Test checkpoint 1500
6. Enjoy your Milan LoRA! 🎉

---

**Good luck with training! This should give you much better results than Sara 2.0!** 🚀
