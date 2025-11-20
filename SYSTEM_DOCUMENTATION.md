# AI Model Generator - System Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Backend API](#backend-api)
5. [Frontend Application](#frontend-application)
6. [Generation Workflow](#generation-workflow)
7. [Features](#features)
8. [Configuration](#configuration)

---

## Overview

An automated AI image generation system that combines:
- **LoRA model configurations** (4 models: Milan, Skyler, Sky, Cam)
- **Grok Vision captioned reference images** (100+ bikini photos)
- **ComfyUI workflow processing** via RunPod
- **Batch generation with variations**
- **Supabase database & storage**

### Tech Stack
- **Frontend**: React 18 + Vite + TailwindCSS + React Router
- **Backend**: Node.js + Express
- **Database**: Supabase (PostgreSQL)
- **Storage**: Supabase Storage (public buckets)
- **AI Processing**: ComfyUI on RunPod GPU

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│  - Generate Page: Batch generation UI                      │
│  - Gallery Page: View all generated images                 │
└────────────┬────────────────────────────────────────────────┘
             │
             │ HTTP API Calls
             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Express API Server                        │
│  - /api/upload-image: Upload to ComfyUI                   │
│  - /api/generate: Submit generation jobs                   │
│  - /api/jobs: Get job queue                                │
│  - /api/jobs/:id/check: Check ComfyUI status              │
└───────┬──────────────────────┬──────────────────────────────┘
        │                      │
        │                      │
        ▼                      ▼
┌──────────────────┐    ┌─────────────────────────────┐
│  Supabase DB     │    │   ComfyUI (RunPod GPU)     │
│  - Models        │    │   - Image generation        │
│  - Jobs          │    │   - LoRA processing         │
│  - Ref Images    │    │   - Returns result          │
└───────┬──────────┘    └─────────────┬───────────────┘
        │                              │
        │                              │
        ▼                              ▼
┌──────────────────────────────────────────────────────────┐
│              Supabase Storage                            │
│  - reference-images/ (input photos)                     │
│  - generated-images/ (AI outputs)                       │
└──────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Tables

#### `models`
Stores AI model configurations (LoRA files, trigger words, attributes).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(100) | Model name (Milan, Skyler, etc.) |
| slug | VARCHAR(50) | URL-friendly identifier |
| skin_tone | VARCHAR(50) | Skin tone attribute |
| hair_color | VARCHAR(50) | Hair color |
| hair_style | VARCHAR(200) | Hair style description |
| lora_file | VARCHAR(200) | LoRA filename on ComfyUI |
| trigger_word | VARCHAR(100) | Model trigger word for prompts |
| negative_prompt | TEXT | Default negative prompt |

**Data**: 4 models (Milan, Skyler, Sky, Cam)

---

#### `reference_images`
Catalog of reference images with Grok Vision captions.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| filename | VARCHAR(500) | Original filename |
| category | VARCHAR(100) | Category (e.g., bikini-mirror-pics) |
| storage_path | VARCHAR(1000) | Path in Supabase Storage |
| vision_description | TEXT | Grok Vision AI caption |
| analyzed_at | TIMESTAMP | When vision analysis was done |

**Data**: 100 reference images with AI captions

---

#### `generation_jobs`
Tracks all image generation requests and status.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| model_id | INTEGER | FK to models |
| workflow_id | INTEGER | FK to workflows (optional) |
| reference_image_id | INTEGER | FK to reference_images (optional) |
| parameters | JSONB | Generation parameters (denoise, cfg, etc.) |
| prompt_used | TEXT | Final positive prompt sent to ComfyUI |
| negative_prompt_used | TEXT | Final negative prompt |
| runpod_job_id | VARCHAR(200) | ComfyUI job ID |
| status | VARCHAR(50) | queued/processing/completed/failed |
| result_image_url | TEXT | Supabase Storage URL of generated image |
| error_message | TEXT | Error if failed |
| created_at | TIMESTAMP | Job creation time |
| started_at | TIMESTAMP | When ComfyUI started processing |
| completed_at | TIMESTAMP | When generation finished |

**Indexes**:
- `idx_jobs_status` on status
- `idx_jobs_model` on model_id
- `idx_jobs_created` on created_at DESC

---

#### `workflows`
ComfyUI workflow templates (currently just img2img-lora).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(100) | Workflow name |
| slug | VARCHAR(50) | Identifier |
| description | TEXT | Description |
| comfyui_workflow | JSONB | Workflow JSON template |
| editable_params | JSONB | UI parameter definitions |

---

### Storage Buckets

#### `reference-images` (public)
- Contains all reference bikini photos
- Path structure: `category/filename.jpg`
- Example: `bikini-mirror-pics/3619935470697612901_60140989072_1.jpg`

#### `generated-images` (public)
- Contains all AI-generated outputs
- Filename format: `{model_slug}_{reference_filename}_{counter}.png`
- Example: `milan_3619935470697612901_60140989072_1_00001_.png`

---

## Backend API

### Base URL
- Local: `http://localhost:3001`
- Codespaces: Auto-detected (replaces port 5173 with 3001)

### Endpoints

#### `POST /api/upload-image`
Upload a reference image to ComfyUI.

**Request**: `multipart/form-data`
```
image: (file)
```

**Response**:
```json
{
  "success": true,
  "filename": "uploaded_image.jpg"
}
```

---

#### `POST /api/generate`
Submit an image generation job.

**Request**:
```json
{
  "modelId": 1,
  "workflowSlug": "img2img-lora",
  "uploadedImageFilename": "reference.jpg",
  "parameters": {
    "denoise": 0.75,
    "cfg": 3.8,
    "steps": 28,
    "seed": -1,
    "lora_strength": 0.65,
    "positive_prompt_suffix": "bikini, professional photo...",
    "negative_prompt_suffix": "blurry, deformed, bad anatomy"
  }
}
```

**Response**:
```json
{
  "success": true,
  "jobId": 123,
  "runpodJobId": "abc-123-def"
}
```

**What it does**:
1. Fetches model config from database
2. Builds combined prompt: `{trigger_word}, {hair_style}, {skin_tone} skin, {vision_caption}`
3. Fills workflow template with variables
4. Submits to ComfyUI
5. Creates job record in database
6. Returns job ID

---

#### `GET /api/jobs`
Get all generation jobs (newest first, limit 50).

**Response**:
```json
[
  {
    "id": 123,
    "model_id": 1,
    "status": "completed",
    "result_image_url": "https://...",
    "prompt_used": "milan, long brunette hair...",
    "negative_prompt_used": "blonde hair...",
    "parameters": {...},
    "created_at": "2025-11-20T...",
    "completed_at": "2025-11-20T...",
    "models": {
      "name": "Milan",
      "slug": "milan"
    }
  }
]
```

---

#### `GET /api/jobs/:id`
Get specific job details.

---

#### `POST /api/jobs/:id/check`
Check job status with ComfyUI and update database.

**What it does**:
1. Queries ComfyUI history for job
2. If completed:
   - Downloads generated image from ComfyUI
   - Uploads to Supabase Storage `generated-images/`
   - Updates job with Supabase URL
3. If failed: marks job as failed
4. If processing: returns current status

---

#### `GET /api/workflows`
Get available workflows from filesystem.

---

## Frontend Application

### Structure

```
web/
├── src/
│   ├── components/
│   │   └── Layout.jsx          # Top navigation + layout wrapper
│   ├── pages/
│   │   ├── Generate.jsx        # Batch generation UI
│   │   └── Gallery.jsx         # View all generated images
│   ├── App.jsx                 # Router setup
│   ├── supabase.js            # Supabase client
│   └── main.jsx               # Entry point
```

### Pages

#### Generate Page (`/generate`)

**Features**:
- **Model selection**: Choose from 4 models
- **Workflow selection**: Currently img2img-lora
- **Reference image browser**:
  - Grid view of 100 reference images
  - Category filters
  - Multi-select with checkboxes
  - Shows Grok Vision captions
- **Parameters**:
  - Denoise strength (0.5-1.0)
  - CFG scale (1-15)
  - Steps (10-50)
  - LoRA strength (0.3-1.0)
  - **Variations** (1-5): How many versions per image
  - Seed
  - Positive/negative prompt additions
- **Live calculation**: "3 images × 2 variations = 6 total jobs"
- **Live job queue** (right sidebar):
  - Shows all pending/processing/completed jobs
  - Auto-refreshes every 5 seconds
  - Click "Check Status" to force poll ComfyUI

**Workflow**:
1. Select model (Milan, Skyler, Sky, Cam)
2. Select 1+ reference images (multi-select)
3. Adjust parameters + set variations
4. Click "Generate X Images"
5. Watch queue auto-update

---

#### Gallery Page (`/gallery`)

**Features**:
- **Grid view** of all generated images
- **Filters**:
  - By model (all/Milan/Skyler/etc.)
  - By status (all/completed/processing/failed)
- **Lightbox modal**:
  - Full-size generated image
  - Model used
  - Status badge
  - **Full positive prompt**
  - **Full negative prompt**
  - **All parameters** (denoise, cfg, steps, etc.)
  - Timestamps (created, completed)
  - Download button

**Purpose**:
- Review all generated images
- Debug prompts and parameters
- See what prompts produced which results

---

### Auto-Polling

The Generate page automatically polls every **5 seconds**:
1. Fetches all jobs from `/api/jobs`
2. For any `processing` jobs, calls `/api/jobs/:id/check`
3. Detects newly completed jobs
4. Shows toast notification: "✅ 3 images generated!"

**No manual refresh needed!**

---

### Toast Notifications

Green toast notifications slide in from bottom-right when:
- Jobs complete
- Errors occur
- Auto-dismiss after 4 seconds

---

## Generation Workflow

### End-to-End Flow

```
User selects:
  - Model: Milan
  - Reference images: 3 bikini photos
  - Variations: 2
  = 6 total jobs

For each reference image (3×):
  For each variation (2×):

    1. Frontend downloads reference from Supabase Storage
    2. Frontend uploads to ComfyUI
    3. Frontend calls /api/generate with:
       - Model ID
       - Uploaded filename
       - Parameters (with random seed)

    4. API Server:
       - Fetches model: "milan, long brunette hair, tan skin"
       - Builds positive prompt:
         "milan, long brunette hair, tan skin, {grok_caption}"
       - Builds negative prompt:
         "blonde hair, light hair, pale skin, blurry, deformed, bad anatomy"
       - Fills workflow template variables
       - Submits to ComfyUI
       - Creates job in database (status: queued)
       - Returns job ID

    5. ComfyUI (RunPod):
       - Loads Qwen model + Milan LoRA
       - Processes img2img generation
       - Saves output image

    6. Auto-polling (every 5s):
       - API calls ComfyUI history endpoint
       - If completed:
         - Downloads generated image
         - Uploads to Supabase Storage
         - Updates job: status=completed, result_image_url
       - Frontend detects completion
       - Shows toast notification
       - Image appears in queue
```

### Prompt Construction

**Positive Prompt**:
```
{trigger_word}, {hair_style}, {skin_tone} skin, {vision_description}
```

**Example**:
```
milan, long brunette hair, tan skin, orange bikini top, mirror selfie, holding phone, bathroom setting, neutral lighting
```

**Negative Prompt**:
```
{model.negative_prompt}, {user_negative_suffix}
```

**Example**:
```
blonde hair, light hair, pale skin, blurry, deformed, bad anatomy
```

---

## Features

### ✅ Implemented

#### Batch Generation
- Select multiple reference images at once
- Set variations per image (1-5)
- Submits all jobs in sequence
- Example: 5 images × 3 variations = 15 jobs

#### Auto-Polling
- Queue refreshes every 5 seconds automatically
- No manual refresh needed
- Polls ComfyUI for processing jobs
- Updates appear instantly

#### Multi-Select Reference Images
- Click to select/deselect
- Blue border + checkmark on selected
- "Clear all" button
- Shows count: "5 images selected"

#### Toast Notifications
- Slide in from bottom-right
- Green for success, red for errors
- Auto-dismiss after 4 seconds
- "✅ 3 images generated!"

#### Gallery with Metadata
- Grid view of all generated images
- Click for lightbox with full details
- See exact prompts used
- See all parameters
- Download button

#### Supabase Storage Integration
- Generated images auto-upload to Supabase
- Public URLs for easy sharing
- Organized by model + reference filename

#### Template Variable Replacement
- Workflow templates use `{{variable}}` syntax
- Both standalone and inline replacements
- Example: `"{{model_name}}_{{reference_filename}}"`
- Properly fills: `"milan_photo123_00001_.png"`

---

### 📋 Planned Features

#### Sub-Models & Face Variants
- Each model will have 3 face variants
- Face swap via Replicate API after generation
- Each face links to separate Instagram account

#### Models Page
- View all models
- Click model → see stats + gallery
- Manage face variants
- View active queue per model

#### Instagram Integration
- Auto-caption with AI
- Schedule posts
- Multiple accounts per model
- Calendar view

---

## Configuration

### Environment Variables

#### Backend (`api/.env`)
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
RUNPOD_API_KEY=rpa_xxx
COMFYUI_API_URL=https://xxx.proxy.runpod.net
PORT=3001
```

#### Frontend (`web/.env.local`)
```bash
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGc...
# VITE_API_URL=""  # Leave empty for auto-detect
```

#### Root (`.env`)
```bash
# Direct database connection for migrations
DATABASE_URL=postgresql://postgres.xxx:password@aws-1-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
DIRECT_URL=postgresql://postgres.xxx:password@aws-1-us-east-1.pooler.supabase.com:5432/postgres
```

### Running the System

#### Start API Server
```bash
cd api
npm install
npm start
# Runs on http://localhost:3001
```

#### Start Frontend
```bash
cd web
npm install
npm run dev
# Runs on http://localhost:5173
```

#### Both Services
```bash
# Terminal 1
cd api && npm start

# Terminal 2
cd web && npm run dev
```

### Database Setup

```bash
# Create tables
python setup_database.py

# Add workflows schema
python setup_workflows_schema.py

# Create storage buckets
python create_storage_buckets.py
```

---

## Workflow Template Format

Located at: `workflows/img2img-lora.json`

### Template Variables
```json
{
  "1": {
    "inputs": {
      "image": "{{reference_image}}"
    }
  },
  "4": {
    "inputs": {
      "lora_name": "{{lora_file}}",
      "strength_model": "{{lora_strength}}"
    }
  },
  "7": {
    "inputs": {
      "text": "{{positive_prompt}}"
    }
  },
  "8": {
    "inputs": {
      "text": "{{negative_prompt}}"
    }
  },
  "10": {
    "inputs": {
      "seed": "{{seed}}",
      "steps": "{{steps}}",
      "cfg": "{{cfg}}",
      "denoise": "{{denoise}}"
    }
  },
  "12": {
    "inputs": {
      "filename_prefix": "{{model_name}}_{{reference_filename}}"
    }
  }
}
```

### Variables Provided
- `reference_image`: Uploaded filename
- `lora_file`: Model LoRA file
- `lora_strength`: 0.3-1.0
- `positive_prompt`: Combined prompt
- `negative_prompt`: Combined negative
- `seed`: Random or specified
- `steps`: 10-50
- `cfg`: 1-15
- `denoise`: 0.5-1.0
- `model_name`: Model slug (milan, skyler)
- `reference_filename`: Reference image name (no extension)

---

## Notes

### Known Issues
1. **Only Milan LoRA works** - Other model LoRAs not uploaded to ComfyUI yet
2. **First generation slow** - ComfyUI model loading (~5 min), subsequent gens fast (~1.5 min)
3. **Auto-polling dependency** - Uses `[jobs]` dependency which can cause unnecessary re-renders

### Future Improvements
1. **WebSocket connection** instead of polling for real-time updates
2. **Grouped job display** - Show variations grouped by reference image
3. **Better error handling** - More descriptive error messages
4. **Batch download** - Download multiple generated images at once
5. **Job cancellation** - Cancel processing jobs

---

## Git Repository

- **Branch**: `website`
- **Structure**:
  ```
  /api          - Express backend
  /web          - React frontend
  /workflows    - ComfyUI workflow templates
  /sql          - Database schemas
  *.py          - Setup scripts
  ```

---

**Last Updated**: November 20, 2025
**Version**: 1.0
**Status**: Production-ready for Generate & Gallery pages
