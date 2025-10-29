# New Simplified Workflow

## ✅ Changes Made:

1. **Deleted anna model** - Clean slate
2. **S3 upload is now ALWAYS ON** - Everything backed up automatically
3. **Model detection improved** - Detects models by images, not just config.json

---

## New Workflow: Drop Files & Process

### Step 1: Create Model Directory Structure

```bash
mkdir -p models/mymodel/source
mkdir -p models/mymodel/targets/nsfw
mkdir -p models/mymodel/targets/sfw
```

### Step 2: Drop Your Images

**Just copy files into folders:**

```
models/mymodel/
├── source/              ← Drop face photos here
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── photo3.jpg
└── targets/
    ├── nsfw/            ← Drop NSFW body images here
    │   ├── body1.jpg
    │   ├── body2.jpg
    │   └── body3.jpg
    └── sfw/             ← Drop SFW body images here
        ├── outfit1.jpg
        └── outfit2.jpg
```

### Step 3: Run CLI - Auto-Detects Everything!

```bash
python3 master.py
# Choose [2] Work with Existing Model
# Choose model (CLI will see it!)
# Model detected automatically
```

---

## How Model Detection Works:

**Model exists if:**
- Directory `models/{name}/` exists AND
- Has images in `source/` OR `targets/nsfw/` OR `targets/sfw/`

**Auto-creates config** if missing:
- Detects you have images
- Creates bucket automatically
- Creates config.json
- Ready to process!

---

## Everything Goes to S3:

### What Gets Uploaded:

```
S3 Bucket: {model}-workflow-{timestamp}/
├── {model}/source/              ← Original source faces
├── {model}/targets/nsfw/        ← Original NSFW targets
├── {model}/results/nsfw/source_1/
│   ├── swapped/
│   │   ├── {model}-s1-t1-nsfw-swapped.jpg
│   │   └── ...
│   └── enhanced/
│       ├── {model}-s1-t1-nsfw-enhanced.jpg
│       ├── {model}-s1-t1-nsfw-enhanced.txt  ← Grok caption!
│       └── ...
```

**Everything is organized and backed up!**

---

## Caption Generation with Grok-4:

```bash
python3 scripts/07_generate_captions.py
```

**Automatically:**
1. Finds all enhanced images
2. Generates captions with Grok-4
3. Saves .txt files locally (required for LoRA)
4. Uploads .txt files to S3 (for backup/reference)

**Caption format:**
```
{model} woman, 20s, brunette, fair tan skin, long straight hair,
detailed face, high cheekbones, full lips, slender curvy body,
nude, bathtub setting, white tiles, soft even lighting, intimate pose,
professional photography, high resolution, realistic style
```

---

## Example: Creating "Andie" Model

```bash
# 1. Create directories
mkdir -p models/andie/source
mkdir -p models/andie/targets/nsfw

# 2. Copy your files
cp ~/Photos/andie_face.jpg models/andie/source/
cp ~/Downloads/body*.jpg models/andie/targets/nsfw/

# 3. Run master.py
python3 master.py
# [2] Work with Existing Model
# [1] andie  ← Auto-detected!
# [1] Process NSFW targets

# 4. Generate captions
python3 scripts/07_generate_captions.py
# Pick andie
# ✓ All captions saved + uploaded to S3

# 5. Ready for LoRA training!
```

---

## Key Benefits:

✅ **No more manual upload** - Just drop files in folders
✅ **Auto-detection** - CLI finds models automatically
✅ **Always backed up** - Everything goes to S3
✅ **Organized** - Smart naming + folder structure
✅ **LoRA-ready** - Captions saved correctly
✅ **Resumable** - Progress tracking built-in

---

## Next: LoRA Training (Phase 2 - Part 2)

Now that captions are done, we can set up LoRA training!
