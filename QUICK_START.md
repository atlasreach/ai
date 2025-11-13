# Quick Start Guide

## 🚀 Start Using Your AI Generator

### Step 1: Start RunPod API Server

On RunPod terminal:
```bash
cd /workspace/ai
git pull origin website
pip install fastapi uvicorn  # One-time install
python3 runpod_api.py
```

You should see:
```
🚀 Starting RunPod Generation API...
   GPU: NVIDIA GeForce RTX 5090
   Server: http://0.0.0.0:8001
```

### Step 2: Get RunPod Public URL

In RunPod dashboard, find your pod's public IP or URL. It will look like:
- `http://xxx.xxx.xxx.xxx:8001` (direct IP)
- Or use RunPod's TCP port forwarding

### Step 3: Open Web UI

Open `frontend/index.html` in your browser (just double-click it).

Update the "RunPod API URL" field with your RunPod URL from Step 2.

### Step 4: Generate!

Adjust the sliders:
- **LoRA Strength**: 0.5-1.0 (how much Milan's face shows)
- **Steps**: 20-50 (more = better quality, slower)
- **Guidance Scale**: 1-10 (how closely to follow prompt)
- **Width/Height**: Image dimensions

Click "Generate Image" and wait 60-90 seconds!

---

## 🎨 Settings Guide

### LoRA Strength (0.5 - 1.0)
- **0.5**: Subtle character features
- **0.8**: Recommended - strong character likeness
- **1.0**: Maximum character resemblance

### Steps (10 - 50)
- **20**: Fast, decent quality
- **30**: Good balance (recommended)
- **50**: Best quality, slowest

### Guidance Scale (1 - 10)
- **1-3**: More creative, less accurate
- **4**: Recommended - balanced
- **7-10**: Very literal, follows prompt exactly

### Dimensions
- **1024x768**: Standard landscape (recommended)
- **768x1024**: Portrait
- **1536x1536**: High resolution (requires more VRAM)

---

## 📝 Prompt Tips

**Good prompts:**
- "Milan, woman, professional headshot, studio lighting, 4K"
- "Milan, woman in red dress, outdoor garden, natural light"
- "Milan, woman, business suit, office background, professional"

**Include:**
- Character name ("Milan")
- Subject ("woman")
- Clothing/style
- Location/background
- Lighting style
- Quality terms ("professional", "4K", "high quality")

**Negative prompt:**
- Keep default: "blurry, low quality, distorted"
- Add more if needed: "cartoon, anime, drawing"

---

## 🐛 Troubleshooting

**"Failed to connect to API"**
- Make sure RunPod API is running (`python3 runpod_api.py`)
- Check the URL is correct
- Verify port 8001 is exposed in RunPod

**Generation takes forever**
- Normal: First generation = 2-3 minutes (loading models)
- After that: 60-90 seconds per image
- Reduce steps to 20 for faster results

**Out of memory**
- Reduce image dimensions (try 512x512)
- Reduce steps to 20
- Restart RunPod API server

**Poor quality results**
- Increase steps to 40-50
- Adjust guidance scale (try 5-6)
- Increase LoRA strength to 0.9-1.0
- Improve your prompt

---

## 📊 Cost Per Image

- RTX 5090 on RunPod: ~$0.89/hour
- Generation time: ~90 seconds
- **Cost per image: ~$0.02**

---

## Next Steps

1. **Add more characters**: Train new LoRAs, add to `LORA_PATHS` in `runpod_api.py`
2. **Save to S3**: Modify API to upload images to your S3 bucket
3. **Build full web app**: Use React for better UI
4. **Mobile app**: Build native iOS/Android app

---

**Ready to generate!** Start the RunPod API and open the UI 🎨
