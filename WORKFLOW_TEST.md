# Dataset Creator Workflow Test

## 🔍 Complete Workflow Analysis

### Step 1: Create/Select Character ✅
**Frontend:** DatasetCreator.tsx line 136-182
**Database:** Direct Supabase insert to `characters` table
**Test:**
```
1. Click "Create New Character"
2. Enter name: "TestChar"
3. Enter trigger: "testchar"
4. Click "Create Character"
```
**Expected:** Character created in Supabase, navigate to step 2
**Potential Issues:** None - Fixed lora_file requirement

---

### Step 2: Define Traits ✅
**Frontend:** DatasetCreator.tsx line 601-702
**Database:** Direct Supabase update on `characters` table
**Operations:**
- Add preset constraint (hair color, skin tone, etc.)
- Add custom constraint
- Remove constraint

**Test:**
```
1. Select "Hair Color" → "blonde"
2. Select "Eye Color" → "blue eyes"
3. Add custom: "expression" = "smiling"
4. Remove "expression"
5. Click "Continue to Dataset Creation"
```
**Expected:** Constraints saved to character_constraints JSONB column
**Potential Issues:** None

---

### Step 3: Create Dataset ✅
**Frontend:** DatasetCreator.tsx line 708-773
**Database:** Direct Supabase insert to `training_datasets` table
**Test:**
```
1. Enter dataset name: "testchar_sfw_v1"
2. Select type: SFW
3. Enter description: "Test dataset"
4. Click "Create Dataset & Continue"
```
**Expected:** Dataset created, caption format generated locally, navigate to step 4
**Potential Issues:** None

---

### Step 4: Upload Images ⚠️
**Frontend:** DatasetCreator.tsx line 778-831
**Storage:** Supabase Storage bucket `training-images`
**Database:** Insert to `training_images` table

**Implementation (line 319-370):**
```javascript
- Upload to: supabase.storage.from('training-images').upload()
- Path: ${dataset_id}/${timestamp}_${index}.${ext}
- Insert record to training_images table
- Update dataset.image_count
```

**Test:**
```
1. Click upload area
2. Select 5-10 images
3. Preview appears
4. Click "Upload X Images & Continue"
```

**Expected:**
- Files uploaded to Supabase Storage
- Records created in training_images table
- Navigate to step 5

**Potential Issues:**
1. ❌ Storage bucket 'training-images' might not have proper policies
2. ❌ Public URL generation might fail if bucket not public
3. ⚠️  Large images might timeout
4. ⚠️  No progress bar for multi-image upload

---

### Step 5: Generate Captions ⚠️
**Frontend:** DatasetCreator.tsx line 833-906
**Backend API:** `POST /api/datasets/{id}/generate-captions-batch`
**Database:** Update training_images captions

**Flow:**
```
Frontend → POST localhost:8002/api/datasets/{id}/generate-captions-batch
         → Backend: dataset_service.build_grok_prompt()
         → Backend: grok_service.generate_caption_from_url()
         → Backend: Save to training_images table
         → Frontend: Load images with captions
         → User can edit captions
```

**Test:**
```
1. Click "Generate Captions with AI"
2. Wait for Grok to process all images
3. Review captions
4. Click "Edit Caption" on one image
5. Modify text
6. Click "Save"
```

**Expected:**
- Captions generated for all images
- Captions follow format: "trigger, constraints, [scene description]"
- Edits save to database

**Potential Issues:**
1. ⚠️  Backend API must be running on localhost:8002
2. ⚠️  GROK_API_KEY must be set in .env
3. ⚠️  Batch generation might be slow (no progress indicator)
4. ❌ No error handling if Grok API fails
5. ⚠️  Images must be publicly accessible for Grok vision

---

## 🚨 Critical Issues Found

### Issue 1: Backend API Not Running
**Problem:** User disabled backend API, but caption generation requires it
**Solution:** Either:
- A) Start backend API: `./scripts/start_api.sh`
- B) Move Grok caption generation to Supabase Edge Function
- C) Call Grok directly from frontend (insecure - exposes API key)

**Recommended:** Keep minimal backend for Grok calls

### Issue 2: Storage Bucket Policies
**Problem:** Bucket created but might not have proper access policies
**Test:** Try uploading an image
**Solution:** Already ran add_rls_policies.py

### Issue 3: No Delete Operations
**Problem:** User cannot delete:
- Characters
- Datasets
- Individual images
- Constraints (can remove, but this works)

**Missing Features:**
```javascript
// Need to add:
const deleteCharacter = async (characterId) => { ... }
const deleteDataset = async (datasetId) => { ... }
const deleteImage = async (imageId) => { ... }
```

### Issue 4: No Edit Existing Dataset
**Problem:** Can only create new datasets, cannot:
- View existing datasets
- Edit dataset info
- Continue incomplete datasets
- Re-generate captions

**Missing UI:**
- "My Datasets" page showing all datasets
- "Continue Editing" option
- Dataset overview/dashboard

### Issue 5: No Export Functionality
**Problem:** After captions are done, no way to:
- Download ZIP file
- Export to Dropbox
- Export caption txt files
- Prepare for training

**Missing:**
```javascript
const exportDataset = async (datasetId) => {
  // Download images + captions as ZIP
}
```

### Issue 6: Backend API Dependency
**Problem:** Caption generation requires localhost:8002 running
**Impact:** If API not running, step 5 fails silently

**Solution:** Add connection check before caption generation

---

## ✅ Working Features

1. ✅ Create characters
2. ✅ Add/remove constraints (presets + custom)
3. ✅ Create datasets
4. ✅ Upload images (should work with proper bucket setup)
5. ✅ Generate captions (if backend running)
6. ✅ Edit individual captions
7. ✅ Professional UI with progress indicator
8. ✅ Back navigation
9. ✅ Form validation

---

## 🛠️ Quick Fixes Needed

### 1. Start Backend API for Caption Generation
```bash
cd /workspaces/ai
./scripts/start_api.sh
```

### 2. Add Delete Operations
Add these functions to DatasetCreator.tsx:
- Delete character (with confirmation)
- Delete dataset (cascade delete images)
- Delete individual image

### 3. Add Dataset Management Page
Create new page: `/datasets` showing:
- List all datasets
- Edit/Delete actions
- Continue incomplete datasets

### 4. Add Export Feature
Button in step 5: "Export Dataset as ZIP"
- Download all images
- Create caption.txt files
- Bundle as ZIP

### 5. Add Error Handling
- Try/catch with user-friendly alerts
- Connection check before API calls
- Retry logic for failed uploads

### 6. Add Progress Indicators
- Upload progress bar
- Caption generation progress (X of Y images)
- Loading states

---

## 🧪 Test Checklist

### Minimal Viable Test:
- [ ] Create character → works
- [ ] Add 2 constraints → works
- [ ] Create dataset → works
- [ ] Upload 3 images → check console for errors
- [ ] Generate captions → requires backend API running

### Full Test:
- [ ] Create 2 characters
- [ ] Add different constraints to each
- [ ] Create SFW dataset for char 1
- [ ] Create NSFW dataset for char 2
- [ ] Upload 10 images to each
- [ ] Generate captions for both
- [ ] Edit 2 captions manually
- [ ] Verify captions saved
- [ ] Check Supabase tables populated correctly

---

## 📊 Database Schema Status

### Characters Table ✅
- id (TEXT, PK)
- name (TEXT)
- trigger_word (TEXT)
- character_constraints (JSONB)
- lora_file (TEXT)
- is_active (BOOLEAN)

### Training_Datasets Table ✅
- id (UUID, PK)
- character_id (TEXT, FK)
- name (TEXT)
- dataset_type (TEXT)
- description (TEXT)
- dataset_constraints (JSONB)
- image_count (INTEGER)
- storage_url (TEXT)
- lora_file (TEXT)
- created_at, updated_at

### Training_Images Table ✅
- id (UUID, PK)
- dataset_id (UUID, FK)
- image_url (TEXT)
- caption (TEXT)
- metadata (JSONB)
- display_order (INTEGER)
- created_at

### Storage Bucket ✅
- Name: `training-images`
- Public: true
- RLS: Enabled

---

## 🎯 Priority Fixes

**P0 (Blocking):**
1. Ensure backend API running for caption generation
2. Verify storage upload works

**P1 (High):**
1. Add delete operations
2. Add export ZIP functionality
3. Error handling

**P2 (Medium):**
1. Dataset management page
2. Progress indicators
3. Edit existing datasets

**P3 (Low):**
1. Batch operations
2. Face swap preprocessing
3. Dropbox integration
