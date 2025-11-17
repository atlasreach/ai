# New AI Studio Pro - Setup Guide

## 🎨 What We Built

A completely redesigned professional website with:
- ✅ **Vertical sidebar navigation** - Modern, clean layout
- ✅ **Dark gradient theme** - Professional blue/purple color scheme
- ✅ **Model Manager** - Create and manage your AI character models
- ✅ **Dataset Creator** - Upload images, analyze features with Grok, generate captions
- ✅ **New database schema** - Flexible model → datasets → LoRA files structure

---

## 📁 New Files Created

### Frontend (React)
```
react-app/src/
├── AppNew.tsx                      # Main app with vertical navigation
├── pages/
│   ├── ModelManager.tsx            # Manage models and datasets
│   ├── DatasetCreatorNew.tsx       # Create training datasets
│   └── ContentProduction.tsx       # (Not active yet)
└── main.tsx                        # Updated to use AppNew
```

### Backend (Python)
```
api/
└── model_api.py                    # New API endpoints for models/datasets

scripts/
├── migrate_new_schema.sql          # Database migration SQL
└── run_migration.py                # Migration helper script
```

---

## 🚀 Setup Steps

### Step 1: Run Database Migration

Open Supabase SQL Editor:
```
https://yiriqesejsbzmzxdxiqt.supabase.co/project/_/sql
```

Copy and paste the contents of:
```
/workspaces/ai/scripts/migrate_new_schema.sql
```

Click **Run** to execute the migration.

This creates:
- `models` table (your AI characters)
- `datasets` table (training datasets for each model)
- `dataset_images` table (images with captions)

### Step 2: Start Backend API

```bash
cd /workspaces/ai
./scripts/start_api.sh
```

This starts the API on port **8002** with the new model_api endpoints mounted.

### Step 3: Start Frontend

```bash
cd /workspaces/ai/react-app
npm run dev
```

Open in browser: `http://localhost:3000`

---

## 🎯 Your Workflow

### **Step 1: Create a Model**

1. Go to **Model Manager** (first tab)
2. Click **"Create New Model"**
3. Enter:
   - **Name**: e.g., "Milan"
   - **Trigger Word**: e.g., "milan" (lowercase, no spaces)
   - **HuggingFace Repo**: e.g., "username/milan" (optional)
4. Click **"Create Model"**

The model is now created with an empty `defining_features` object.

---

### **Step 2: Create a Dataset**

1. Click on your model in Model Manager
2. Click **"Add Dataset"** or go to **Dataset Creator** tab
3. Select your model from the list
4. Enter dataset info:
   - **Name**: e.g., "milan_instagram_v1"
   - **Type**: SFW or NSFW
   - **Description**: Optional notes
5. Click **"Create & Continue"**

---

### **Step 3: Upload Images**

1. Drag & drop or click to upload 20-30 images
2. Recommended formats: JPG, PNG
3. Click **"Upload X Images"**
4. Images are uploaded to Supabase Storage: `training-images/{dataset_id}/`

---

### **Step 4: Generate Features (Optional for First Dataset)**

For the **first dataset** of a new model:
- System can analyze images with Grok
- Extracts defining features automatically
- You review and approve/edit features

For **additional datasets**:
- Uses existing model features
- Skip to caption generation

---

### **Step 5: Generate Captions**

1. Click **"Generate All Captions"**
2. Backend calls Grok for each image:
   - Uses model trigger word + defining features
   - Analyzes image content
   - Generates training caption
3. Format: `"trigger_word, defining features, [scene description]"`
4. Example: `"milan, woman with blonde hair, blue eyes, fair skin, wearing red dress in garden"`

---

### **Step 6: Review & Edit Captions**

1. Each image shows with its caption
2. Click **Edit** icon to modify any caption
3. Save changes to database
4. Captions are used for training

---

### **Step 7: Download Dataset**

1. Click **"Download Dataset"**
2. Gets ZIP file with:
   - All images
   - Caption files (.txt matching each image)
3. Ready for AI Toolkit training!

---

### **Step 8: Train Manually (External)**

1. Upload ZIP to your RunPod training instance
2. Run AI Toolkit Ostrich training
3. Training produces: `milan_instagram_v1.safetensors`
4. Upload to HuggingFace
5. Download to ComfyUI RunPod: `/workspace/ComfyUI/models/loras/`

---

### **Step 9: Register Trained Model**

Back in Model Manager:
1. Find your dataset
2. Click **Edit**
3. Fill in:
   - **LoRA Filename**: `milan_instagram_v1.safetensors`
   - **HuggingFace URL**: Direct file link (optional)
   - **Training Notes**: "2000 steps, rank 16" (optional)
4. Status changes to **"Trained"** ✅

---

## 🎨 UI Features

### Vertical Navigation
```
┌─────────────┬──────────────────────┐
│  AI Studio  │                      │
│  Pro        │                      │
│             │                      │
│ ◉ Model     │   Main Content Area  │
│   Manager   │                      │
│             │                      │
│ ○ Dataset   │                      │
│   Creator   │                      │
│             │                      │
│ ○ Content   │                      │
│   Prod      │                      │
│             │                      │
│ ○ Settings  │                      │
└─────────────┴──────────────────────┘
```

### Professional Design
- **Dark gradient background**: slate-950 → slate-900
- **Accent colors**: Blue (400) + Purple (500)
- **Card hover effects**: Glow shadows
- **Smooth transitions**: 200ms animations
- **Status badges**: Color-coded (green=trained, blue=ready, yellow=training)

---

## 🗄️ Database Schema

### Models Table
```sql
- id (UUID)
- name (TEXT) - "Milan", "Sara"
- trigger_word (TEXT) - "milan", "sara"
- defining_features (JSONB) - { "hair": "blonde", "eyes": "blue", ... }
- huggingface_repo (TEXT) - "username/milan"
- is_active (BOOLEAN)
- created_at, updated_at
```

### Datasets Table
```sql
- id (UUID)
- model_id (UUID) → models.id
- name (TEXT) - "milan_instagram_v1"
- dataset_type (TEXT) - "SFW" | "NSFW"
- description (TEXT)
- image_count (INTEGER)
- lora_filename (TEXT) - "milan_instagram_v1.safetensors" ⭐
- huggingface_url (TEXT)
- training_notes (TEXT)
- training_status (TEXT) - "preparing" | "ready_to_train" | "trained"
- created_at, updated_at
```

### Dataset_Images Table
```sql
- id (UUID)
- dataset_id (UUID) → datasets.id
- image_url (TEXT) - Supabase Storage URL
- caption (TEXT) - Full training caption
- metadata (JSONB)
- display_order (INTEGER)
- created_at
```

---

## 🔌 API Endpoints

### Model API (`/api`)

**Feature Analysis:**
```
POST /api/analyze-features
Body: { "image_urls": ["url1", "url2", ...] }
→ Returns: { "features": { "hair": "...", "eyes": "...", ... } }
```

**Batch Caption Generation:**
```
POST /api/datasets/{dataset_id}/generate-captions-batch
→ Generates captions for all images in dataset
```

**Update Training Status:**
```
POST /api/datasets/{dataset_id}/update-training-status
Body: {
  "lora_filename": "milan_v1.safetensors",
  "huggingface_url": "https://...",
  "training_notes": "..."
}
```

**Get Model Datasets:**
```
GET /api/models/{model_id}/datasets
→ Returns all datasets for a model
```

**Upload Temp File:**
```
POST /api/upload-temp
Body: FormData with file
→ Used for uploading images
```

---

## ⚠️ Known Limitations

1. **Download Dataset** - Not yet implemented
   - Need to create ZIP with images + caption files
   - Will add in next iteration

2. **Grok Feature Analysis** - Basic implementation
   - Currently analyzes first image only
   - Should analyze 3-5 images for better accuracy

3. **Content Production** - Placeholder only
   - Not active yet per your request
   - Will build after dataset workflow is solid

4. **Delete Operations** - Not implemented
   - Can't delete models/datasets/images yet
   - Add in next iteration

---

## 🧪 Testing Checklist

### Test 1: Create Model
- [ ] Click "Create New Model"
- [ ] Fill in name, trigger word
- [ ] Model appears in list
- [ ] Check Supabase: models table has new record

### Test 2: Create Dataset
- [ ] Select model
- [ ] Click "Add Dataset"
- [ ] Fill in dataset info
- [ ] Dataset created
- [ ] Check Supabase: datasets table has new record

### Test 3: Upload Images
- [ ] Upload 5-10 test images
- [ ] Images preview correctly
- [ ] Click "Upload Images"
- [ ] Check Supabase Storage: images in `training-images/{dataset_id}/`
- [ ] Check Supabase: dataset_images table has records

### Test 4: Generate Captions
- [ ] Backend API running on port 8002
- [ ] GROK_API_KEY set in .env
- [ ] Click "Generate All Captions"
- [ ] Captions appear for each image
- [ ] Check format: "trigger, features, description"
- [ ] Edit a caption and save
- [ ] Check Supabase: caption updated

### Test 5: Multiple Datasets
- [ ] Create second dataset for same model
- [ ] Uses same trigger word + features
- [ ] Upload different images
- [ ] Generate captions (should use same base template)

---

## 🚧 Next Steps

After testing the dataset workflow:

1. **Add ZIP Download** - Export dataset for training
2. **Add Edit/Delete** - Modify and remove items
3. **Content Production** - Batch image generation with ComfyUI
4. **Grok Review** - AI suggests parameter adjustments
5. **Instagram Integration** - Caption generation for posts

---

## 📝 Environment Variables Required

```bash
# Supabase
SUPABASE_URL=https://yiriqesejsbzmzxdxiqt.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...

# Grok
GROK_API_KEY=xai-...

# AWS S3 (for later)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=ai-character-generations
AWS_REGION=us-east-2
```

---

**🎉 You're all set! Run the migration, start the servers, and test the workflow!**
