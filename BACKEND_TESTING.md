# Backend Testing Guide

## ✅ Backend is Ready!

All services have been built and configured:
- FastAPI server
- Grok AI integration
- ComfyUI client
- AWS S3 storage
- Character database

---

## 🚀 Start the Backend Server

```bash
# Option 1: Using startup script
./start_backend.sh

# Option 2: Direct Python
python3 -m backend.main

# Option 3: With uvicorn
uvicorn backend.main:app --reload --port 8000
```

Server will start at: **http://localhost:8000**

---

## 📡 Test Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "services": {
    "grok_api": true,
    "runpod_url": true,
    "aws_configured": true,
    "huggingface_token": true
  }
}
```

---

### 2. List Characters
```bash
curl http://localhost:8000/api/characters/
```

**Expected Response:**
```json
[
  {
    "id": "milan",
    "name": "Milan",
    "lora_model": "milan_000002000.safetensors",
    "lora_strength": 0.8,
    "trigger_word": "Milan",
    "description": "Professional female model trained on 2000 steps"
  }
]
```

---

### 3. Get Specific Character
```bash
curl http://localhost:8000/api/characters/milan
```

---

### 4. Generate Image (Full Test)

**Important:** You need a reference image file for this test.

```bash
curl -X POST http://localhost:8000/api/generate/ \
  -F "character_id=milan" \
  -F "prompt=woman playing tennis on outdoor court" \
  -F "reference_image=@/path/to/your/image.jpg" \
  -F "use_groq_enhancement=true" \
  -F "cfg_scale=4.0" \
  -F "steps=30" \
  -F "denoise=0.85" \
  -F "seed=-1" \
  -F "batch_size=1"
```

**Expected Response:**
```json
{
  "job_id": "uuid-here",
  "character_id": "milan",
  "prompt": "woman playing tennis on outdoor court",
  "enhanced_prompt": "Milan, woman, athletic build, playing tennis...",
  "image_urls": [
    "https://ai-character-generations.s3.us-east-2.amazonaws.com/generated/milan/..."
  ],
  "generation_time_seconds": 75.3,
  "parameters": {
    "lora_model": "milan_000002000.safetensors",
    "lora_strength": 0.8,
    "cfg_scale": 4.0,
    "steps": 30
  }
}
```

---

## 🧪 Test with Postman/Insomnia

1. Open Postman
2. Import collection from `/docs` endpoint
3. Set base URL: `http://localhost:8000`
4. Test `/api/generate/` with form-data:
   - `character_id`: milan
   - `prompt`: your text
   - `reference_image`: file upload
   - (other parameters)

---

## 📚 API Documentation

Once server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Interactive documentation with "Try it out" feature!

---

## ⚠️ Before First Generation Test

Make sure RunPod has the required models:

**Option A: Manual Setup (Recommended)**
```bash
# SSH into RunPod
ssh root@1314jk61pzkjdb.proxy.runpod.net

# Download models (one-time setup)
cd /workspace/ComfyUI/models

# Qwen base models
wget https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_fp8_e4m3fn.safetensors -O diffusion_models/qwen_image_fp8_e4m3fn.safetensors

# Milan LoRA
wget https://huggingface.co/nicksanford2341/businessmodels/resolve/main/milan_000002000.safetensors -O loras/milan_000002000.safetensors

exit
```

**Option B: Auto-Download**
- ComfyUI will download on first use
- Takes ~10-15 minutes first time

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
pkill -f "backend.main"

# Try different port
PORT=8001 python3 -m backend.main
```

### Generation fails
1. Check RunPod is running: `curl https://1314jk61pzkjdb-3001.proxy.runpod.net/system_stats`
2. Check models exist in RunPod
3. Check .env file has all credentials
4. Check logs for errors

### Grok API errors
- Check API key is valid
- Check quota/rate limits
- Fallback: Disable with `use_groq_enhancement=false`

---

## 📊 Expected Generation Time

- **With RunPod RTX 5090**: ~60-90 seconds per image
- **Batch (10 images)**: ~2-3 minutes
- **First generation**: +10-15 min (model download)

---

## ✅ Success Checklist

- [ ] Server starts without errors
- [ ] `/health` endpoint returns healthy status
- [ ] `/api/characters/` lists Milan
- [ ] Can upload reference image
- [ ] Generation completes successfully
- [ ] Images appear in S3 bucket
- [ ] Image URLs are publicly accessible

---

**Next Step:** Start the server and test with `/docs` endpoint!
