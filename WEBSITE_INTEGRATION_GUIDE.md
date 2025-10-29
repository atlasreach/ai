# Website Integration Guide - LoRA Generation Platform

## 🎯 Vision

**User flow:**
1. User visits website
2. Enters prompt: "jade woman, red dress, beach sunset"
3. Clicks "Generate"
4. Sees 4-6 high-quality variations
5. Picks favorites → Download

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                             │
│  (React/Next.js + Tailwind)                             │
│                                                          │
│  - Prompt input box                                      │
│  - Generation settings (quality, count, style)           │
│  - Image gallery with masonry layout                     │
│  - Download buttons                                      │
└─────────────────────────────────────────────────────────┘
                          ↓ API calls
┌─────────────────────────────────────────────────────────┐
│                     BACKEND API                          │
│  (FastAPI + Python)                                      │
│                                                          │
│  POST /generate                                          │
│    → Receives prompt + settings                          │
│    → Queues generation job                               │
│    → Returns job_id                                      │
│                                                          │
│  GET /status/{job_id}                                    │
│    → Returns progress/completion                         │
│                                                          │
│  GET /result/{job_id}                                    │
│    → Returns generated image URLs                        │
└─────────────────────────────────────────────────────────┘
                          ↓ Uses
┌─────────────────────────────────────────────────────────┐
│               COMFYUI / A1111 API                        │
│                                                          │
│  - Loads jade-v1.safetensors LoRA                        │
│  - SDXL base model                                       │
│  - Generates images                                      │
│  - Returns to API                                        │
└─────────────────────────────────────────────────────────┘
                          ↓ Stores
┌─────────────────────────────────────────────────────────┐
│                     AWS S3                               │
│  - Generated images                                      │
│  - Serves via CloudFront CDN                             │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 Tech Stack

### Frontend
- **Framework:** Next.js 14 (React 18)
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui
- **Image Gallery:** react-photo-album or masonry
- **API Client:** axios or fetch

### Backend
- **Framework:** FastAPI (Python)
- **Job Queue:** Redis + RQ or Celery
- **Image Generation:** ComfyUI API
- **Storage:** AWS S3
- **Database:** PostgreSQL (optional - for usage tracking)

### Infrastructure
- **Frontend Hosting:** Vercel or Netlify
- **Backend Hosting:** RunPod Serverless or Railway
- **GPU Server:** RunPod (ComfyUI)
- **Storage:** AWS S3 + CloudFront

---

## 🔨 Implementation Plan

### Phase 1: Backend API (Week 1)

#### File: `api/main.py`

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid

app = FastAPI()

class GenerationRequest(BaseModel):
    prompt: str
    model_name: str = "jade"
    num_images: int = 4
    quality: str = "high"  # low, medium, high

class GenerationResponse(BaseModel):
    job_id: str
    status: str
    estimated_time: int  # seconds

@app.post("/api/generate")
async def generate_images(
    request: GenerationRequest,
    background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())

    # Add to background queue
    background_tasks.add_task(
        process_generation,
        job_id=job_id,
        prompt=request.prompt,
        model_name=request.model_name,
        num_images=request.num_images
    )

    return GenerationResponse(
        job_id=job_id,
        status="queued",
        estimated_time=30  # 30 seconds per batch
    )

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    # Check job status in Redis/DB
    return {
        "job_id": job_id,
        "status": "processing",  # queued, processing, completed, failed
        "progress": 0.75,  # 0.0 to 1.0
        "images_completed": 3,
        "images_total": 4
    }

@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
    # Return S3 URLs
    return {
        "job_id": job_id,
        "status": "completed",
        "images": [
            "https://cdn.yoursite.com/jade/gen-001.jpg",
            "https://cdn.yoursite.com/jade/gen-002.jpg",
            "https://cdn.yoursite.com/jade/gen-003.jpg",
            "https://cdn.yoursite.com/jade/gen-004.jpg"
        ],
        "metadata": {
            "prompt": "jade woman, red dress, beach sunset",
            "model": "jade-v1",
            "seed": 123456
        }
    }
```

#### File: `api/generator.py`

```python
import requests
from lib import S3Manager

def process_generation(job_id, prompt, model_name, num_images):
    """Background task to generate images"""

    # Load LoRA model
    lora_path = f"models/{model_name}/{model_name}-v1.safetensors"

    images = []
    for i in range(num_images):
        # Call ComfyUI API
        result = generate_with_comfy(
            prompt=f"{model_name} woman, {prompt}",
            lora_path=lora_path,
            seed=random.randint(1000, 999999)
        )

        # Upload to S3
        s3 = S3Manager()
        filename = f"{job_id}-{i+1}.jpg"
        s3_url = s3.upload_file(result, f"generations/{job_id}/{filename}")

        images.append(s3_url)

        # Update progress
        update_job_progress(job_id, (i+1) / num_images)

    # Mark complete
    mark_job_complete(job_id, images)

def generate_with_comfy(prompt, lora_path, seed):
    """Call ComfyUI API to generate image"""

    workflow = {
        "prompt": prompt,
        "negative_prompt": "low quality, blurry, distorted",
        "lora": {
            "model": lora_path,
            "strength": 0.9
        },
        "steps": 30,
        "cfg_scale": 7,
        "seed": seed,
        "width": 1024,
        "height": 1024
    }

    response = requests.post(
        "http://localhost:8188/api/prompt",
        json=workflow
    )

    return response.json()["image_url"]
```

---

### Phase 2: Frontend (Week 2)

#### File: `app/page.tsx`

```tsx
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import ImageGallery from '@/components/ImageGallery'

export default function Home() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [images, setImages] = useState([])

  const handleGenerate = async () => {
    setLoading(true)

    // Start generation
    const response = await fetch('/api/generate', {
      method: 'POST',
      body: JSON.stringify({
        prompt,
        model_name: 'jade',
        num_images: 4
      })
    })

    const { job_id } = await response.json()

    // Poll for results
    const interval = setInterval(async () => {
      const status = await fetch(`/api/status/${job_id}`)
      const data = await status.json()

      if (data.status === 'completed') {
        clearInterval(interval)
        const result = await fetch(`/api/result/${job_id}`)
        const { images } = await result.json()
        setImages(images)
        setLoading(false)
      }
    }, 2000)
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-4xl font-bold mb-8">
        AI Image Generator - Jade
      </h1>

      <div className="flex gap-4 mb-8">
        <Input
          placeholder="Describe the image... (e.g., red dress, beach sunset)"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          className="flex-1"
        />
        <Button
          onClick={handleGenerate}
          disabled={loading || !prompt}
        >
          {loading ? 'Generating...' : 'Generate'}
        </Button>
      </div>

      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin">⏳</div>
          <p className="mt-4">Generating your images...</p>
        </div>
      )}

      {images.length > 0 && (
        <ImageGallery images={images} />
      )}
    </div>
  )
}
```

#### File: `components/ImageGallery.tsx`

```tsx
import { Download } from 'lucide-react'
import { Button } from './ui/button'

export default function ImageGallery({ images }) {
  const handleDownload = (url: string, index: number) => {
    const a = document.createElement('a')
    a.href = url
    a.download = `jade-generated-${index + 1}.jpg`
    a.click()
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {images.map((url, index) => (
        <div key={index} className="relative group">
          <img
            src={url}
            alt={`Generated ${index + 1}`}
            className="w-full h-auto rounded-lg shadow-lg"
          />
          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all rounded-lg flex items-center justify-center">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleDownload(url, index)}
              className="opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}
```

---

## 🚀 Deployment

### Step 1: Deploy ComfyUI on RunPod

```bash
# Use RunPod template: ComfyUI (SDXL)
# GPU: RTX 4090
# Expose port: 8188

# Upload your LoRA
scp models/jade/jade-v1.safetensors root@pod:/workspace/ComfyUI/models/loras/
```

### Step 2: Deploy Backend API

**Option A: Railway**
```bash
railway init
railway up
```

**Option B: RunPod Serverless**
```bash
# Create serverless endpoint
# Point to your FastAPI app
```

### Step 3: Deploy Frontend

```bash
vercel deploy
# or
netlify deploy
```

---

## 💰 Cost Estimate

| Service | Cost/Month |
|---------|-----------|
| RunPod GPU (on-demand, 8hrs/day) | ~$80 |
| AWS S3 Storage (100GB) | $2.30 |
| CloudFront CDN (1TB transfer) | $85 |
| Database (optional) | $5-15 |
| **Total** | **~$170-180/month** |

**Revenue potential:**
- $0.50 per generation
- 500 generations/day = $250/day
- **$7,500/month potential**

---

## 🎯 Features Roadmap

### MVP (Week 1-2)
- [x] Prompt input
- [x] Generate 4 images
- [x] Download button
- [x] Basic gallery

### V1.0 (Week 3-4)
- [ ] User accounts
- [ ] Generation history
- [ ] Advanced settings (steps, CFG, seed)
- [ ] Multiple LoRA models

### V2.0 (Month 2)
- [ ] Image-to-image (upload reference)
- [ ] Inpainting/outpainting
- [ ] Batch generation
- [ ] API access for developers

---

## 🔐 Security

- Rate limiting (10 generations/hour per IP)
- API key authentication
- NSFW content filtering (optional)
- User registration required for unlimited access

---

## 📊 Monitoring

- Track generation count
- Monitor GPU usage
- Cost per generation
- User engagement metrics

---

Ready to build when you are! 🚀
