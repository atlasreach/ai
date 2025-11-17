# Workflow Guide: Models → Instagram → Datasets

## ✅ WHAT'S DONE

**Database is now clean and working:**
- ✓ Skylar Mae model linked to @officialskylarmaexo (135 posts)
- ✓ Ivy Ireland model linked to @ivyirelandx (14 posts)
- ✓ All Instagram posts imported and accessible

---

## 📋 RECOMMENDED WORKFLOW

### **Option A: Instagram-First (Best for real models)**
Use this when you want to train a model based on a real Instagram account.

```
1. Scrape Instagram with Apify
   → Use Apify web interface
   → Input: Instagram username(s)
   → Download the dataset URL

2. Import to Database
   → Run: python scripts/import_apify_scrape.py <dataset_url>
   → This creates: instagram_account + instagram_posts

3. Create Model
   → Go to "Model Manager" page
   → Click "Create Model"
   → Select the Instagram account from dropdown
   → Model auto-links to Instagram account

4. Create Dataset from Instagram Posts
   → Go to "Datasets" page
   → Click "Create Dataset"
   → Select model
   → Select images from Instagram posts
   → Dataset is created with Instagram images
```

### **Option B: Model-First (For custom/synthetic models)**
Use this when you want to upload training images directly.

```
1. Create Model
   → Go to "Model Manager"
   → Name: e.g., "Custom Character"
   → No Instagram account needed

2. Create Dataset
   → Go to "Datasets"
   → Select your model
   → Upload images directly (drag & drop)
   → Or upload ZIP file

3. Train Model (manual)
   → Download dataset as ZIP
   → Train with AI Toolkit locally
   → Upload trained LoRA back to model
```

---

## 🗂️ SIMPLIFIED DATABASE SCHEMA

### **models**
Core table - one row per model/character
```
✓ Keep:
  - id, name                     (required)
  - instagram_username           (optional)
  - instagram_account_id         (optional - links to instagram_accounts)
  - description, thumbnail_url   (optional)
  - trained_lora_name            (set after training)
  - trained_lora_path            (HuggingFace repo or local path)

❌ Remove:
  - first_name, last_name        (not needed - just use "name")
  - tiktok_username              (not using)
  - onlyfans_username            (not using)
  - huggingface_repo             (duplicate of trained_lora_path)
```

### **instagram_accounts**
One row per Instagram account scraped
```
✓ Keep all current fields
- Links back to model via model_id
```

### **instagram_posts**
Individual posts from Instagram accounts
```
✓ Keep all current fields
- Links to instagram_accounts via account_id
```

### **datasets**
Collections of images for training or content generation
```
✓ Keep:
  - id, name, model_id
  - type ('training' or 'content_generation')
  - image_count
  - description
```

### **dataset_images**
Individual images in datasets
```
✓ Keep:
  - id, dataset_id
  - image_url, caption
  - source ('instagram' or 'upload')
  - instagram_post_id (if source='instagram')
```

---

## 🔄 HOW IT ALL CONNECTS

```
models
  ├─→ instagram_account_id → instagram_accounts
  │                             └─→ instagram_posts
  │
  └─→ datasets
        └─→ dataset_images
              └─→ instagram_post_id → instagram_posts
```

**Flow:**
1. Model can have ONE Instagram account
2. Instagram account has MANY posts
3. Model can have MANY datasets
4. Dataset images can reference Instagram posts

---

## 🎯 NEXT STEPS TO FIX THE UI

### 1. Update Models Table
Remove unnecessary columns:
```sql
ALTER TABLE models
  DROP COLUMN first_name,
  DROP COLUMN last_name,
  DROP COLUMN tiktok_username,
  DROP COLUMN onlyfans_username,
  DROP COLUMN huggingface_repo;
```

### 2. Fix Dataset Creation Flow
Update `DatasetsNew.tsx`:
- When user selects a model with `instagram_account_id`
- Load Instagram posts for that account
- Let user select which posts to add to dataset
- On save, link `dataset_images.instagram_post_id` to selected posts

### 3. Create Import Script
New file: `scripts/import_apify_scrape.py`
```python
# Takes Apify dataset URL
# Imports accounts + posts
# Auto-creates models if they don't exist
```

---

## 💡 RECOMMENDED FIXES

### Fix #1: Simplify Model Creation
Remove the first_name/last_name fields from the UI. Just use "name".

### Fix #2: Instagram Posts Selector
In Datasets page, when a model has Instagram:
```
[Datasets Page]
  → Select Model: "Skylar Mae"
  → Shows: "135 Instagram posts available"
  → [View Instagram Posts] button
  → Grid of posts with checkboxes
  → [Add Selected to Dataset]
```

### Fix #3: Scrape Import Button
Add to Instagram Library page:
```
[Import from Apify]
  → Paste Apify Dataset URL
  → Click Import
  → Automatically creates accounts + posts
```

---

## 🚀 CURRENT STATUS

**Working:**
- ✅ Instagram posts are scraped and stored
- ✅ Models link to Instagram accounts
- ✅ Database relationships are correct

**Needs Work:**
- ⚠️ UI doesn't show Instagram posts when creating datasets
- ⚠️ Dataset creation doesn't link to Instagram posts
- ⚠️ No easy way to import new Apify scrapes

**Quick Test:**
1. Start frontend: `cd react-app && npm run dev`
2. Go to Model Manager → See Skylar Mae and Ivy Ireland
3. Go to Datasets → Try creating dataset for Skylar Mae
4. Currently: Can't see her 135 Instagram posts (this is the bug!)

---

## 📝 PROPOSED UI CHANGES

### Model Manager Page
```
Current:
  Name: [text]
  First Name: [text]    ← REMOVE
  Last Name: [text]     ← REMOVE
  Instagram: [text]

Proposed:
  Name: [text]
  Instagram Username: [text]
  Description: [textarea]
```

### Dataset Creation Modal
```
Step 1: Basic Info
  - Name
  - Model (dropdown)
  - Type (training/content_generation)

Step 2: Add Images
  If model has Instagram:
    [Tab: Instagram Posts] [Tab: Upload Files]

    Instagram Posts tab:
      → Shows grid of all posts
      → Checkboxes to select
      → "Add 25 selected posts"

  If no Instagram:
    Upload files only
```

---

Want me to implement these UI fixes now?
