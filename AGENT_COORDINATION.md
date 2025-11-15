# Agent Coordination File
**Last Updated:** Agent 1 - Initial Setup

---

## **Agent Responsibilities**

### **Agent 1 - Dataset Creator**
**Owner:** First agent
**Files:**
- `/services/dataset_service.py` ✅ **COMPLETED**
- `/api/dataset_api.py` ✅ **COMPLETED**
- `/react-app/src/pages/DatasetCreator.tsx` ✅ **COMPLETED**
- Database schema updates ✅ **COMPLETED**

**Status:** 🟢 Completed - Ready for use

---

### **Agent 2 - ComfyUI API Integration**
**Owner:** Second agent
**Files:**
- `/services/comfyui_service.py` ✅ **COMPLETED**
- `/api/comfyui_api.py` ✅ **COMPLETED**
- `/scripts/migrate_comfyui_fields.py` ✅ **COMPLETED**
- Integration with character system ✅ **COMPLETED**

**Status:** 🟢 Completed - Ready for testing

---

## **Shared Data Structures (DO NOT MODIFY WITHOUT COORDINATION)**

### **Character Schema:**
```python
# Both agents READ this, only Agent 1 WRITES
{
  "id": "milan",  # Primary key
  "name": "Milan",  # Display name
  "trigger_word": "milan",  # Used in captions AND ComfyUI prompts
  "character_constraints": {  # Agent 1 manages this
    "constants": [
      {"key": "hair_color", "value": "blonde", "type": "physical"},
      {"key": "skin", "value": "fair skin with natural glow", "type": "physical"}
    ]
  },
  "lora_file": "milan_sfw_v1.safetensors",  # Agent 2 USES this for generation
  "lora_strength": 0.8,  # Agent 2 USES this
  "comfyui_workflow": "workflows/qwen/instagram_single.json"  # Agent 2 USES this
}
```

### **Training Dataset Schema:**
```python
# Agent 1 creates these
{
  "id": "uuid",
  "character_id": "milan",
  "name": "milan_sfw_v1",
  "dataset_type": "SFW",  # or "NSFW"
  "dataset_constraints": {
    "rules": [
      {"key": "clothing", "value": "required"}
    ]
  },
  "image_count": 30,
  "lora_file": "milan_sfw_v1.safetensors",  # After training - Agent 2 will use this
  "created_at": "timestamp"
}
```

---

## **API Endpoints**

### **Agent 1 Endpoints (Dataset Management):**
```
POST   /api/datasets/create                    - Create new dataset
GET    /api/datasets/{dataset_id}              - Get dataset details
GET    /api/characters/{char_id}/datasets      - List all datasets for character
PUT    /api/characters/{char_id}/constraints   - Update character constraints
POST   /api/datasets/{id}/generate-captions    - Generate captions with Grok
PUT    /api/datasets/{id}/images/{img_id}      - Update image caption
GET    /api/datasets/{id}/export               - Export as ZIP for training
```

### **Agent 2 Endpoints (ComfyUI Generation):**
```
POST   /api/comfyui/generate                   ⬅️ CREATE THIS
       Body: {
         "character_id": "milan",
         "workflow": "qwen_single",
         "input_image_url": "s3://...",
         "prompt_additions": "standing in garden"  # Added to character template
       }
       Returns: {"job_id": "uuid", "status": "queued"}

GET    /api/comfyui/status/{job_id}            ⬅️ CREATE THIS
       Returns: {
         "status": "processing|completed|failed",
         "output_url": "s3://...",
         "progress": 0-100
       }

POST   /api/comfyui/batch-generate             ⬅️ CREATE THIS (later)
       For batch workflow
```

---

## **Agent 2 Brief - READ THIS:**

### **Your Mission:**
Build a ComfyUI API integration so we can generate images programmatically instead of manually.

### **What You Need To Do:**

1. **Create `/services/comfyui_service.py`:**
   - ComfyUI API client class
   - Load workflow JSON from `/workflows/qwen/instagram_single.json`
   - **Dynamically inject parameters:**
     - LoRA file path (from character.lora_file)
     - Prompt (from character trigger_word + constraints + user additions)
     - Input image (for image-to-image)
   - Submit job to ComfyUI API
   - Poll for completion (websocket or HTTP polling)
   - Return output image URL

2. **Create `/api/comfyui_api.py`:**
   - FastAPI endpoints (see above)
   - Integrate with existing character system
   - Save results to database (content_items table)

3. **ComfyUI Setup:**
   - Assume ComfyUI is running at `http://localhost:8188` (or configurable)
   - Use their API: https://github.com/comfyanonymous/ComfyUI/wiki/API
   - You'll need to:
     - POST workflow to `/prompt`
     - Get prompt_id
     - Poll `/history/{prompt_id}` or use websocket
     - Download output images

4. **Workflow Parameter Injection:**
   - Load JSON: `workflows/qwen/instagram_single.json`
   - Find nodes by type (e.g., "LoraLoaderModelOnly" node)
   - Replace values:
     ```python
     # Find LoRA loader node
     for node_id, node in workflow["nodes"].items():
         if node["type"] == "LoraLoaderModelOnly":
             node["inputs"]["lora_name"] = character["lora_file"]
             node["inputs"]["strength_model"] = character["lora_strength"]

     # Find prompt node
     for node_id, node in workflow["nodes"].items():
         if node["type"] == "CLIPTextEncode" and "positive" in node["title"].lower():
             node["inputs"]["text"] = build_prompt(character, user_additions)
     ```

5. **Example Usage:**
   ```python
   # User uploads reference image
   # Calls: POST /api/comfyui/generate
   # Body: {
   #   "character_id": "milan",
   #   "input_image_url": "s3://bucket/uploaded.jpg",
   #   "prompt_additions": "wearing red dress, standing in garden"
   # }

   # Your service:
   # 1. Gets milan character data
   # 2. Loads workflows/qwen/instagram_single.json
   # 3. Injects: milan_sfw_v1.safetensors LoRA
   # 4. Builds prompt: "milan, a woman with blonde hair, fair skin, wearing red dress, standing in garden"
   # 5. Submits to ComfyUI
   # 6. Returns job_id to user
   ```

### **Reference Files:**
- `/workspaces/ai/services/replicate_service.py` - Similar async pattern
- `/workspaces/ai/workflows/qwen/instagram_single.json` - Workflow to execute
- `/workspaces/ai/api/studio_api.py` - Existing API patterns

### **Dependencies:**
- Character data from database (Agent 1 manages schema)
- LoRA files must exist in ComfyUI's loras/ folder
- Workflow JSON files in `/workflows/`

### **DO NOT:**
- Touch dataset creator files
- Modify character constraint system (read-only for you)
- Change database schema without coordinating

---

## **Progress Tracking**

### **Agent 1 Progress:**
- [x] Project restructure
- [x] Requirements.txt created
- [x] Dataset service backend (`/services/dataset_service.py`)
- [x] Dataset API endpoints (`/api/dataset_api.py`)
- [x] Database schema migration (`/scripts/migrate_database.py`)
- [x] Grok caption generation integration
- [x] API mounted and tested
- [ ] Frontend UI

**Files Created:**
- `/services/dataset_service.py` - Complete dataset management backend
- `/api/dataset_api.py` - 15 API endpoints for dataset CRUD and captioning
- `/scripts/migrate_database.py` - Adds training_datasets and training_images tables
- Updated: `/services/grok_service.py` - Added `generate_caption_from_url()` method
- Updated: `/api/studio_api.py` - Mounted dataset router

**API Endpoints Live:**
- `GET /api/datasets/characters/{id}` - Get character with constraints
- `PUT /api/datasets/characters/{id}/constraints` - Update constraints
- `POST /api/datasets/characters/{id}/constraints/add` - Add constraint
- `DELETE /api/datasets/characters/{id}/constraints/{key}` - Remove constraint
- `POST /api/datasets/create` - Create new dataset
- `GET /api/datasets/{id}` - Get dataset details
- `GET /api/datasets/character/{id}` - List character's datasets
- `GET /api/datasets/{id}/images` - Get dataset images
- `PUT /api/datasets/images/{id}/caption` - Update caption
- `GET /api/datasets/{id}/preview-template` - Preview caption template
- `POST /api/datasets/{id}/generate-caption` - Generate single caption
- `POST /api/datasets/{id}/generate-captions-batch` - Batch caption generation

### **Agent 2 Progress:**
- [x] ComfyUI service created
- [x] Workflow parameter injection working
- [x] API endpoints created
- [x] Integration with character system
- [x] Database migration for lora_strength and comfyui_workflow
- [ ] Testing with Milan LoRA
- [ ] Integration testing with live ComfyUI instance

---

## **Communication Protocol**

1. **After each session with user:**
   - Update your "Progress Tracking" section
   - Document any new interfaces/endpoints you created
   - Note any blockers or questions

2. **Before starting work:**
   - Read this file to see what the other agent has done
   - Check for any changes to shared data structures

3. **If you need to modify shared structures:**
   - Add a note in "Pending Changes" section below
   - Wait for user to coordinate

---

## **Pending Changes / Questions**

### From Agent 1:
**✅ Implementation Complete - 2025-11-15**

**What was built:**
1. **Dataset Service** (`/services/dataset_service.py`):
   - Character constraint management (CRUD)
   - Training dataset creation and management
   - Training image management
   - Dynamic Grok prompt builder
   - Caption template system

2. **Dataset API** (`/api/dataset_api.py`):
   - 15 RESTful endpoints
   - Character constraints: add/update/remove
   - Dataset CRUD operations
   - Image caption generation with Grok
   - Batch caption generation
   - Template preview system

3. **Frontend UI** (`/react-app/src/pages/DatasetCreator.tsx`):
   - 5-step wizard: Select → Constraints → Dataset → Upload → Captions
   - Real-time constraint editor with live preview
   - Drag-and-drop image upload
   - Caption review and editing interface
   - Integrated with Supabase and backend API

4. **Database Migration** (`/scripts/migrate_database.py`):
   - Added `training_datasets` table
   - Added `training_images` table
   - Updated `characters` with constraints and trigger_word

**Features:**
- ✅ Two-tier template system (character + dataset constraints)
- ✅ Dynamic caption format with live preview
- ✅ Grok vision integration for automatic captioning
- ✅ SFW/NSFW dataset separation
- ✅ Individual caption editing
- ✅ Full mobile-responsive UI

**Usage:**
1. Navigate to `/dataset-creator` in app
2. Select character (Milan, Skyler, SeaDream)
3. Edit character constraints (hair, skin, features)
4. Create new dataset (name, type, description)
5. Upload 20-30 images
6. Generate captions with Grok
7. Review/edit captions
8. Export dataset for training

**Next steps:**
- Add ZIP export functionality
- Add Dropbox integration
- Add face swap pre-processing option
- Test with real training workflow

### From Agent 2:
**✅ Implementation Complete - 2025-11-15**

**What was built:**
1. **ComfyUI Service** (`/services/comfyui_service.py`):
   - Dynamic workflow loading from JSON files
   - LoRA injection (file + strength)
   - Prompt injection (positive + negative)
   - Input image injection
   - Prompt building from character constraints
   - Job submission to ComfyUI API
   - Async polling for completion
   - Image URL generation

2. **ComfyUI API** (`/api/comfyui_api.py`):
   - `POST /generate` - Submit generation job (returns immediately)
   - `GET /status/{job_id}` - Check job status
   - `POST /batch-generate` - Placeholder for future batch workflow
   - Background task polling and database updates
   - Full integration with characters table

3. **Database Migration** (`/scripts/migrate_comfyui_fields.py`):
   - Adds `lora_strength` (FLOAT, default 0.8)
   - Adds `comfyui_workflow` (TEXT, default 'workflows/qwen/instagram_single.json')

**Setup Required:**
1. Run database migration: `python scripts/migrate_comfyui_fields.py`
2. Ensure ComfyUI is accessible at: `https://slai6mcmlxsqvh-3001.proxy.runpod.net`
3. Ensure LoRA files are in ComfyUI's `loras/` directory (e.g., `milan_000002000.safetensors`)
4. Install dependencies: `aiohttp`, `websockets` (add to requirements.txt if needed)

**Testing Needed:**
- Test with Milan character (needs character data in database with proper fields)
- Verify ComfyUI API is responding at RunPod URL
- Test full workflow: submit job → poll status → get output image
- Verify background polling saves results to database correctly

**Notes:**
- API runs on port 8003 (different from studio_api on 8002)
- Jobs are async - they return immediately with job_id, user polls for completion
- Output images are served from ComfyUI's `/view` endpoint
- Character constraints are automatically built into prompts

**Questions/Blockers:**
- None currently - ready for testing!

---

## **File Ownership**

| Path | Owner | Other Agent Can |
|------|-------|-----------------|
| `/services/dataset_service.py` | Agent 1 | Read only |
| `/api/dataset_api.py` | Agent 1 | Read only |
| `/react-app/src/pages/DatasetCreator.tsx` | Agent 1 | Read only |
| `/services/comfyui_service.py` | Agent 2 | Read/Write |
| `/api/comfyui_api.py` | Agent 2 | Read/Write |
| `/api/studio_api.py` | Shared | Coordinate changes |
| `AGENT_COORDINATION.md` | Both | Read/Write |

---

**Last Updated By:** Agent 1 (Dataset Creator) - 2025-11-15
**Status:** Both agents complete! Dataset Creator and ComfyUI Integration ready for testing.
**Next Action:** Test full workflow - create dataset, train LoRA, generate with ComfyUI.
