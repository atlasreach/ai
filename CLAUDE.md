# AI Model Studio - Project Overview

## 🚨 CURRENT STATUS (Oct 29, 2025 - 4:45 PM EST)

**Model**: SAR (Source 1 only - 7 images)
**Phase**: Phase 2 - LoRA Training Setup
**Location**: RunPod terminal at `/workspace`

### ✅ Completed Today:
1. ✅ Generated captions for all SAR enhanced images using BLIP
2. ✅ Uploaded 7 enhanced images + captions to S3: `s3://destinty-workflow-1761724503/results/nsfw/source_1/enhanced/`
3. ✅ Created `runpod_train_sar_source1_only.sh` script for automated training
4. ✅ Fixed SimpleTuner installation bug (was using `requirements.txt`, now uses `pip install simpletuner[cuda]`)
5. ✅ Committed fix to GitHub (commit: `16ef9dd`)
6. ✅ Pulled updated script to RunPod
7. ✅ Downloaded training data from S3 to `/workspace/lora_training/10_sar/`

### 🔄 IN PROGRESS RIGHT NOW:
**SimpleTuner is installing** (process 6823, running 15+ seconds, using 10.6% CPU)
- Command: `pip install -q simpletuner[cuda]`
- Expected time: 10-15 minutes
- Status: ✅ Working correctly (verified with `ps aux | grep pip`)

### ⏭️ NEXT STEPS (When you come back online):

1. **Check if SimpleTuner finished installing:**
   ```bash
   # In RunPod terminal, check if still running:
   ps aux | grep pip

   # If nothing shows, it's done! You should see:
   # "✓ SimpleTuner installed"
   # "Step 3: Creating training config..."
   ```

2. **If installation completed, training should auto-start:**
   ```bash
   # The script will create:
   # - /workspace/train_config.json
   # - /workspace/train_sar_flux.sh
   # - Then run: bash /workspace/train_sar_flux.sh
   ```

3. **Monitor training progress:**
   ```bash
   # Training takes ~30-60 minutes
   # Watch for: "Training Complete!"
   # Output will be in: /workspace/sar_lora_output/
   ```

4. **If installation failed or stuck:**
   ```bash
   # Kill and restart:
   pkill -9 pip
   cd /workspace
   pip install simpletuner[cuda]  # Without -q to see progress

   # Then run:
   bash /workspace/ai/runpod_train_sar_source1_only.sh
   ```

### 🐛 Known Issues & Fixes:
- ❌ **SimpleTuner git clone + requirements.txt** → ✅ Fixed: Now uses `pip install simpletuner[cuda]`
- ⏳ **Installation seems frozen** → Normal! Takes 10-15 min, use `ps aux | grep pip` to verify

### 📁 Important File Locations:

**In RunPod (`/workspace`):**
- Training images: `/workspace/lora_training/10_sar/` (7 images + 7 captions)
- Setup script: `/workspace/ai/runpod_train_sar_source1_only.sh`
- Training script: `/workspace/train_sar_flux.sh` (created by setup)
- Output: `/workspace/sar_lora_output/` (will contain trained LoRA)

**In GitHub Codespaces (`/workspaces/ai`):**
- Main script: `runpod_train_sar_source1_only.sh`
- Master workflow: `master_v2.py`
- Caption scripts: `generate_captions.py`, `caption_one_folder.py`

**In S3 (`destinty-workflow-1761724503`):**
- Images: `results/nsfw/source_1/enhanced/sar-s1-t*.jpg`
- Captions: `results/nsfw/source_1/enhanced/sar-s1-t*.txt`

---

## 🎯 PROJECT VISION

Build a **professional SaaS platform** for creating personalized AI models through face swapping, enhancement, and LoRA training. Think "MaxStudio meets Stable Diffusion" - a complete pipeline from photos to trained models.

---

## 📋 DEVELOPMENT PHASES

### **PHASE 1: Core Workflow & Multi-Model System** ⏳ IN PROGRESS

**Goal**: Production-ready CLI tool for managing multiple AI models with face swap + enhancement

**Features**:
- ✅ Multi-model support (organize by person: andie, blondie, etc.)
- ✅ Multiple source photos per model
- ✅ NSFW/SFW content separation
- ✅ MaxStudio API integration (face swap + enhance)
- ✅ AWS S3 storage with smart organization
- ✅ Progress tracking + resume capability
- ✅ Cost tracking per model
- ✅ Quality validation (face detection, size checks)
- ✅ Smart file naming: `{model}-s{source#}-t{target#}-{type}-{stage}.jpg`
- ✅ Error handling + automatic retry
- ✅ Configuration per model

**Tech Stack**:
- Python 3.12
- MaxStudio API (face swap, enhancement)
- AWS S3 (boto3)
- OpenCV (face detection)

**Structure**:
```
ai/
├── models/
│   ├── andie/
│   │   ├── source/              # Source face photos
│   │   ├── targets/nsfw/        # Target bodies (NSFW)
│   │   ├── targets/sfw/         # Target bodies (SFW)
│   │   ├── results/
│   │   │   ├── nsfw/
│   │   │   │   ├── source_1/    # Results from source 1
│   │   │   │   │   ├── swapped/
│   │   │   │   │   └── enhanced/
│   │   │   │   └── source_2/
│   │   │   └── sfw/
│   │   ├── config.json          # Model settings
│   │   ├── progress.json        # Processing state
│   │   └── costs.json           # Credit tracking
├── scripts/
│   ├── master.py                # Main CLI tool
│   └── lib/                     # Helper modules
├── models.json                  # Global model registry
└── .env                         # API keys
```

**CLI Interface**:
```bash
python master.py

AI Model Studio
===============
[1] Create New Model
[2] Work with Existing Model
[3] View All Models
[4] Exit

→ You select: 1

Enter model name: andie
✓ Model created: models/andie/

Upload source photos (comma-separated paths or drag folder):
→ /path/to/face1.jpg, /path/to/face2.jpg

✓ Validated: 2 photos
✓ Renamed: face1.jpg → andie-source-1.jpg
✓ Renamed: face2.jpg → andie-source-2.jpg

Which folder to process?
[1] NSFW
[2] SFW
[3] Both

→ You select: 1

Upload target photos to models/andie/targets/nsfw/:
→ [Paste folder path or files]

✓ 5 targets uploaded
✓ Face detected in 5/5 targets

Estimated cost: 120 credits (10 swaps × 10, 10 enhance × 2)
Continue? [Y/n]

Processing:
  [████████░░] 80% | andie-s2-t004-nsfw-enhanced.jpg

✓ Complete! 10/10 successful
✓ Saved to: models/andie/results/nsfw/
✓ Uploaded to S3: andie-workflow-1730249876
✓ Cost: 118 credits

Process SFW folder too? [Y/n]
```

---

### **PHASE 2: Caption Generation & LoRA Training** 🔜 PLANNED

**Goal**: Automatically generate captions for images and train LoRA models for Stable Diffusion

**Features**:
- 🔜 Image captioning using BLIP/CLIP models
- 🔜 Generate training captions: `"a photo of {trigger_word}, {description}"`
- 🔜 LoRA training pipeline (Stable Diffusion)
- 🔜 Automated dataset preparation
- 🔜 Model versioning & comparison
- 🔜 Quality scoring for training images

**Tech Stack** (TBD):
- BLIP-2 or CLIP Interrogator (captioning)
- Kohya_ss or SimpleTuner (LoRA training)
- Stable Diffusion WebUI (testing)
- Possible: Hugging Face Diffusers

**Workflow**:
```
Enhanced Images
    ↓
BLIP/CLIP Caption Generation
    ↓
Manual Caption Review/Edit
    ↓
Dataset Preparation (pairs: image + text)
    ↓
LoRA Training (Kohya/SimpleTuner)
    ↓
Model Testing & Comparison
    ↓
Export Final LoRA
```

**Example Captions**:
```
andie-s1-t001-nsfw-enhanced.jpg
→ "a photo of andie, woman, full body, studio lighting, professional photography"

andie-s1-t002-sfw-enhanced.jpg
→ "a photo of andie, woman, portrait, outdoor, natural lighting, smiling"
```

---

### **PHASE 3: REST API & Background Jobs** 🔮 FUTURE

**Goal**: Expose workflow via REST API with async processing

**Features**:
- FastAPI server with auto-generated docs
- WebSocket for live progress updates
- Background job queue (Celery/RQ)
- Multi-user support
- Authentication & API keys
- S3 presigned URLs for downloads

---

### **PHASE 4: React Web UI** 🔮 FUTURE

**Goal**: Professional SaaS interface for managing models

**Features**:
- React 18 + Tailwind CSS
- Dashboard with model cards
- Before/after image comparison slider
- Drag & drop file uploads
- Live progress tracking
- Cost calculator
- Export & download

---

## 🔑 CURRENT STACK (Phase 1)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.12 | Core logic |
| Face Swap | MaxStudio API | Face replacement |
| Enhancement | MaxStudio API | Image upscaling (2x) |
| Storage | AWS S3 (boto3) | Cloud storage |
| Face Detection | OpenCV + Haar Cascade | Quality validation |
| Config | JSON files | Model settings |
| CLI | Python input() | User interaction |

---

## 📊 CURRENT PROGRESS

### ✅ Completed (Phase 0 - Prototype)
- [x] Basic face swap script (single image)
- [x] Enhancement script
- [x] S3 upload with presigned URLs
- [x] Quality checking (BRISQUE + CLIP-IQA)
- [x] Successfully processed 5 NSFW images for "andie" model
- [x] Validated MaxStudio API integration
- [x] Cost: ~118 credits for 10 images (5 swap + 5 enhance)

### 🏗️ In Progress (Phase 1)
- [ ] Restructure into `models/` directory
- [ ] Create `master.py` CLI tool
- [ ] Multi-model support
- [ ] Progress tracking + resume
- [ ] Cost tracking per model
- [ ] Smart file naming
- [ ] Configuration system
- [ ] Error handling + retry logic

---

## 💰 COST ANALYSIS

Based on MaxStudio API pricing:

| Operation | Credits/Image | 10 Images | 100 Images |
|-----------|---------------|-----------|------------|
| Face Swap | ~10 | 100 | 1,000 |
| Enhance (2x) | ~2 | 20 | 200 |
| **Total** | **~12** | **120** | **1,200** |

**For LoRA Training**: Recommended 20-50 high-quality images per model
- Cost: 240-600 credits per model
- Processing time: ~5-10 minutes

---

## 🎯 SUCCESS METRICS

**Phase 1 Goals**:
1. ✅ Process 10+ images in one run without errors
2. ✅ Resume if interrupted
3. ✅ Track costs accurately
4. ✅ Validate quality automatically (reject bad images)
5. ✅ Smart organization (easy to find results)

**Phase 2 Goals**:
1. Generate accurate captions for 90%+ of images
2. Successfully train LoRA model
3. Generate consistent outputs using trained model
4. Model file < 100MB

---

## 🚀 QUICK START (Phase 1)

Once master.py is complete:

```bash
# Install dependencies
pip install boto3 python-dotenv requests opencv-python-headless

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run CLI tool
python master.py
```

---

## 📝 NOTES

### MaxStudio API Learnings
- ✅ Use `/swap-image` endpoint (not `/faceswap`)
- ✅ Response uses `detectedFaces` key
- ✅ Payload format: `newFace: url` (not nested object)
- ✅ Use regional S3 URLs (not generic amazonaws.com)
- ✅ Presigned URLs work (7-day expiry recommended)
- ✅ Enhancement improves quality significantly (+29% beauty score avg)

### File Naming Convention
```
{model}-s{source#}-t{target#}-{type}-{stage}.jpg

Examples:
- andie-s1-t001-nsfw-swapped.jpg
- andie-s2-t003-sfw-enhanced.jpg
- blondie-s1-t010-nsfw-enhanced.jpg
```

### Quality Thresholds
- Face detection: Must detect at least 1 face
- File size: < 5MB (API limit)
- Resolution: Minimum 800px on shortest side
- CLIP Beauty Score: > 0.6 for training (enhanced images)

---

## 🤝 CONTRIBUTING

This is currently a solo project but built with production standards for potential future contributors.

---

**Last Updated**: October 29, 2025
**Current Phase**: Phase 1 - Core Workflow
**Status**: 🏗️ Building CLI tool with multi-model support
