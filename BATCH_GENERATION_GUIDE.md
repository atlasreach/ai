# Batch Image Generation Guide

## 🚀 Quick Start

Generate multiple images super fast using batch processing!

### Command Line Usage

```bash
# Generate 8 images (2 prompts × 4 per batch)
python3 batch_generate.py \
  --prompts "milan, professional headshot" "milan, beach sunset" \
  --batch-size 4 \
  --lora milan \
  --steps 20

# Generate 24 images (3 prompts × 8 per batch)
python3 batch_generate.py \
  --prompts "skyler, city street" "skyler, cafe interior" "skyler, park bench" \
  --batch-size 8 \
  --lora skyler \
  --strength 0.85 \
  --steps 15

# Generate 100 images (10 prompts × 10 per batch)
python3 batch_generate.py \
  --prompts \
    "milan, pose 1" "milan, pose 2" "milan, pose 3" \
    "milan, pose 4" "milan, pose 5" "milan, pose 6" \
    "milan, pose 7" "milan, pose 8" "milan, pose 9" \
    "milan, pose 10" \
  --batch-size 10 \
  --lora milan \
  --output ./outputs/milan_100
```

---

## 📊 Speed Reference (RTX 5090)

| Total Images | Batch Size | Prompts | Est. Time | Images/Min |
|--------------|------------|---------|-----------|------------|
| 4 | 4 | 1 | 15s | 16 |
| 8 | 4 | 2 | 30s | 16 |
| 16 | 8 | 2 | 40s | 24 |
| 32 | 8 | 4 | 80s | 24 |
| 64 | 8 | 8 | 160s | 24 |
| 100 | 10 | 10 | 240s | 25 |

---

## 🎨 Python API Usage

```python
from batch_generate import generate_batch

# Simple usage
images = generate_batch(
    prompts=["milan, studio photo", "milan, outdoor"],
    lora="milan",
    batch_size=4
)

# Advanced usage
images = generate_batch(
    prompts=[
        "milan, professional headshot, studio lighting",
        "milan, casual beach photo, golden hour",
        "milan, city street, fashion photography",
        "milan, restaurant interior, ambient lighting"
    ],
    lora="milan",
    lora_strength=0.85,
    batch_size=8,
    steps=18,
    output_dir="./outputs/milan_photoshoot"
)

print(f"Generated {len(images)} images!")
```

---

## ⚙️ Parameters

### `--prompts` (required)
List of prompts to generate. Each prompt generates `batch_size` images.

**Examples:**
```bash
--prompts "milan, headshot" "milan, full body" "milan, closeup"
```

### `--lora` (default: milan)
Which LoRa to use.

**Options:**
- `milan` - milan_000002000.safetensors
- `skyler` - skyler_000002000.safetensors
- `1girl` - 1girlqwen.safetensors

### `--batch-size` (default: 4)
How many images to generate per prompt.

**Recommended:**
- `4` - Fast, good for testing
- `8` - Best speed/quality balance
- `16` - Maximum throughput (may use more VRAM)

### `--steps` (default: 20)
Sampling steps.

**Recommended:**
- `15` - Fast, good quality
- `20` - Balanced (default)
- `25-30` - Best quality, slower

### `--strength` (default: 0.8)
LoRa strength (0.0-1.0).

**Recommended:**
- `0.7` - Subtle effect
- `0.8` - Balanced (default)
- `0.9` - Strong effect

### `--output` (default: ./outputs/batch)
Where to save generated images.

---

## 💡 Pro Tips

### Generate 100 Images in 4 Minutes

```bash
python3 batch_generate.py \
  --prompts \
    "milan, pose 1" "milan, pose 2" "milan, pose 3" "milan, pose 4" "milan, pose 5" \
    "milan, pose 6" "milan, pose 7" "milan, pose 8" "milan, pose 9" "milan, pose 10" \
  --batch-size 10 \
  --steps 15 \
  --lora milan
```

### Speed Optimization

**For maximum speed:**
- Use `--batch-size 8` or higher
- Use `--steps 15`
- Queue multiple scripts in parallel

**For quality:**
- Use `--batch-size 4`
- Use `--steps 25`
- Use `--strength 0.85-0.9`

### Parallel Processing

Run multiple scripts at once:

```bash
# Terminal 1
python3 batch_generate.py --prompts "milan, set 1" "milan, set 2" --batch-size 8 &

# Terminal 2
python3 batch_generate.py --prompts "milan, set 3" "milan, set 4" --batch-size 8 &

# Terminal 3
python3 batch_generate.py --prompts "milan, set 5" "milan, set 6" --batch-size 8 &

# This generates 48 images in ~40 seconds!
```

---

## 📝 Example Use Cases

### 1. Character Photoshoot (50 images)

```bash
python3 batch_generate.py \
  --prompts \
    "milan, studio headshot, professional lighting" \
    "milan, outdoor portrait, natural light" \
    "milan, fashion photography, urban background" \
    "milan, lifestyle photo, cafe setting" \
    "milan, editorial style, minimalist background" \
  --batch-size 10 \
  --lora milan \
  --output ./outputs/milan_photoshoot
```

### 2. Content Library (200 images)

```bash
# Run 20 prompts × 10 images each
python3 batch_generate.py \
  --prompts \
    "milan, professional headshot" "milan, casual portrait" \
    "milan, beach photo" "milan, city street" \
    "milan, restaurant" "milan, gym workout" \
    "milan, coffee shop" "milan, outdoor nature" \
    "milan, office setting" "milan, evening wear" \
    "milan, casual wear" "milan, sports attire" \
    "milan, winter fashion" "milan, summer fashion" \
    "milan, formal event" "milan, party scene" \
    "milan, travel photo" "milan, home interior" \
    "milan, car photo" "milan, artistic portrait" \
  --batch-size 10 \
  --lora milan \
  --output ./outputs/milan_library
```

### 3. Social Media Content (Daily Posts)

```bash
# Generate 28 images for a week (4 per day)
python3 batch_generate.py \
  --prompts \
    "milan, monday motivation quote" \
    "milan, tuesday tips" \
    "milan, wednesday wisdom" \
    "milan, thursday thoughts" \
    "milan, friday feeling" \
    "milan, weekend vibes" \
    "milan, sunday chill" \
  --batch-size 4 \
  --lora milan \
  --output ./outputs/weekly_content
```

---

## 🔧 Troubleshooting

**Script fails immediately:**
- Check ComfyUI is running on RunPod (port 3001)
- Verify SSH connection: `ssh root@38.80.152.249 -p 30206 -i ~/.ssh/id_ed25519`

**Out of memory:**
- Reduce `--batch-size` to 4
- Reduce `--steps` to 15

**Images not what you expect:**
- Adjust `--strength` (try 0.7-0.9)
- Improve your prompts (be specific!)
- Try different seeds (automatic per batch)

**Too slow:**
- Increase `--batch-size` to 8-16
- Decrease `--steps` to 15
- Run multiple scripts in parallel

---

## 📁 Output Structure

Images are saved to the output directory:

```
outputs/batch/
├── batch_txt2img_00001_.png
├── batch_txt2img_00002_.png
├── batch_txt2img_00003_.png
└── ...
```

Each filename contains a unique ID to prevent overwrites.

---

## 🎯 Next Steps

1. **Test with small batch:** Generate 4 images to verify setup
2. **Scale up:** Generate 50-100 images for your content library
3. **Automate:** Schedule regular batches with cron/systemd
4. **Integrate:** Use the Python API in your own scripts

---

## 💰 Cost Comparison

**Your Setup (RunPod + Qwen):**
- 100 images: ~$0.50 (4 min of GPU time)
- **Speed:** 25 images/minute

**Alternatives:**
- Replicate API: 100 images = $5-10
- MidJourney: 100 images = $30+ subscription
- Manual Photoshoot: $$$$$

**Your setup is 10-60x cheaper!**

---

## 🚀 Happy Generating!

Questions? Check the code in `/workspaces/ai/batch_generate.py`
