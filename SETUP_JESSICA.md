# Setting Up Anna Model

## Step 1: Drop Source Image

**Put this file in `models/anna/source/`:**
```
openart-image_gZO5XpAT_1761681801445_raw.jpg
```

## Step 2: Drop NSFW Target Images

**Put these files in `models/anna/targets/nsfw/`:**
```
12480761.jpg
0004-18_1200.jpg
0004-14_1200.jpg
0004-15_1200.jpg
0012-14_1800.jpg
0012-02_1200.jpg
0012-03_w400.jpg
0011-10_1200.jpg
12196808.jpg
0009-15_1800.jpg
12196815.jpg
12196794 (1).jpg
12196794.jpg
12196803.jpg
21.BadoinkVR_Tongue_In_Cheek.jpg
20.BadoinkVR_Tongue_In_Cheek.jpg
```

## Step 3: Run the Workflow

```bash
python3 master.py
```

1. Choose **[2] Work with Existing Model**
2. Choose **[1] anna** (will be auto-detected)
3. Choose **[1] Process NSFW targets**

The CLI will:
- Auto-create S3 bucket: `anna-workflow-{timestamp}`
- Auto-create config.json
- Process all face swaps
- Enhance all images
- Upload everything to S3

## Step 4: Generate Captions

```bash
python3 scripts/07_generate_captions.py
```

1. Choose **anna**
2. All enhanced images will get Grok-4 captions
3. Captions saved as .txt files + uploaded to S3

## Ready for LoRA Training!

All images + captions will be in:
```
models/anna/results/nsfw/source_1/enhanced/
├── anna-s1-t1-nsfw-enhanced.jpg
├── anna-s1-t1-nsfw-enhanced.txt  ← Caption
├── anna-s1-t2-nsfw-enhanced.jpg
├── anna-s1-t2-nsfw-enhanced.txt
└── ...
```
