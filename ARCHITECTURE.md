# ComfyUI Integration Architecture

## Overview

This document outlines the professional architecture for the ComfyUI image generation system, designed for scalability and maintainability.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Web UI / Frontend                     │
│         (React, TypeScript - user configures generations)   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP/REST
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Endpoints (/api/v1/...)                        │   │
│  │  - /generate/single                                 │   │
│  │  - /generate/batch                                  │   │
│  │  - /edit/inpaint                                    │   │
│  │  - /workflows (list available workflows)           │   │
│  └─────────────────────────────────────────────────────┘   │
│                       │                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Workflow Manager Service                           │   │
│  │  - Load workflow configs from registry             │   │
│  │  - Validate parameters                              │   │
│  │  - Queue management                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                       │                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ComfyUI Service                                    │   │
│  │  - Submit prompts to ComfyUI                        │   │
│  │  - Poll for completion                              │   │
│  │  - Download results                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP API
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              RunPod ComfyUI Instance                         │
│              (GPU processing)                                │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Storage (S3, Supabase)                          │
│              (Generated images, metadata)                    │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
/workspaces/ai/
├── workflows/                    # Workflow JSON files
│   ├── registry.json            # Central workflow registry
│   ├── qwen/
│   │   ├── single.json          # Single image generation
│   │   ├── batch.json           # Batch processing
│   │   ├── inpaint.json         # Inpainting/editing
│   │   └── upscale.json         # Upscaling
│   └── flux/                    # Other model families
│       └── single.json
│
├── services/                     # Business logic
│   ├── comfyui_service.py       # Core ComfyUI API client
│   ├── workflow_manager.py      # Workflow registry & validation
│   └── storage_service.py       # S3/Supabase storage
│
├── api/                          # FastAPI endpoints
│   ├── main.py                  # Main FastAPI app
│   ├── models.py                # Pydantic request/response models
│   └── endpoints/
│       ├── generate.py          # Generation endpoints
│       ├── edit.py              # Editing endpoints
│       ├── workflows.py         # Workflow management
│       └── status.py            # Job status endpoints
│
├── database/                     # Database schemas & migrations
│   ├── schema.sql               # PostgreSQL schema
│   └── migrations/
│
├── react-app/                    # Frontend UI
│   └── src/
│       ├── components/
│       │   ├── WorkflowSelector.tsx
│       │   ├── ParameterControls.tsx
│       │   └── GenerationQueue.tsx
│       └── pages/
│           ├── Generate.tsx
│           └── Results.tsx
│
├── tests/                        # Tests
│   ├── test_workflows.py
│   └── test_api.py
│
└── config/                       # Configuration
    ├── workflows.yaml           # Workflow configs (alternative to JSON)
    └── settings.py              # App settings
```

## Workflow Registry Pattern

### 1. Central Registry (`workflows/registry.json`)

```json
{
  "workflows": {
    "qwen_single": {
      "id": "qwen_single",
      "name": "Single Image Generation",
      "description": "Generate one image from one input",
      "category": "generation",
      "model_family": "qwen",
      "workflow_path": "workflows/qwen/single.json",
      "supports_batch": false,
      "requires_input_image": true,
      "requires_mask": false,
      "configurable_params": {
        "steps": {
          "type": "int",
          "min": 1,
          "max": 50,
          "default": 20,
          "description": "Number of diffusion steps"
        },
        "cfg": {
          "type": "float",
          "min": 1.0,
          "max": 20.0,
          "default": 4.0,
          "description": "Classifier-free guidance scale"
        },
        "denoise": {
          "type": "float",
          "min": 0.0,
          "max": 1.0,
          "default": 0.75,
          "description": "Denoising strength (0=no change, 1=full generation)"
        },
        "lora_strength": {
          "type": "float",
          "min": 0.0,
          "max": 2.0,
          "default": 0.5,
          "description": "LoRA model strength"
        },
        "seed": {
          "type": "int",
          "min": -1,
          "max": 2147483647,
          "default": -1,
          "description": "Random seed (-1 for random)"
        }
      },
      "example_payload": {
        "character_id": "milan",
        "input_image": "input.jpg",
        "prompt": "woman with long hair, professional photo",
        "params": {
          "steps": 20,
          "cfg": 4.0,
          "denoise": 0.75,
          "lora_strength": 0.5,
          "seed": -1
        }
      }
    },
    "qwen_batch": {
      "id": "qwen_batch",
      "name": "Batch Image Generation",
      "description": "Generate multiple images from multiple inputs",
      "category": "generation",
      "model_family": "qwen",
      "workflow_path": "workflows/qwen/batch.json",
      "supports_batch": true,
      "requires_input_image": true,
      "max_batch_size": 10,
      "configurable_params": {
        "steps": { "type": "int", "min": 1, "max": 50, "default": 20 },
        "cfg": { "type": "float", "min": 1.0, "max": 20.0, "default": 4.0 },
        "denoise": { "type": "float", "min": 0.0, "max": 1.0, "default": 0.75 },
        "lora_strength": { "type": "float", "min": 0.0, "max": 2.0, "default": 0.5 }
      }
    },
    "qwen_inpaint": {
      "id": "qwen_inpaint",
      "name": "Image Inpainting",
      "description": "Edit specific regions of an image",
      "category": "editing",
      "model_family": "qwen",
      "workflow_path": "workflows/qwen/inpaint.json",
      "supports_batch": false,
      "requires_input_image": true,
      "requires_mask": true,
      "configurable_params": {
        "steps": { "type": "int", "min": 1, "max": 50, "default": 25 },
        "cfg": { "type": "float", "min": 1.0, "max": 20.0, "default": 5.0 },
        "denoise": { "type": "float", "min": 0.0, "max": 1.0, "default": 1.0 }
      }
    }
  }
}
```

### 2. Workflow Manager Service

```python
# services/workflow_manager.py
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

class WorkflowManager:
    """Manages workflow registry and validation"""

    def __init__(self, registry_path: str = "workflows/registry.json"):
        self.registry_path = Path(registry_path)
        self.workflows = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        """Load workflow registry from JSON"""
        with open(self.registry_path, 'r') as f:
            data = json.load(f)
        return data.get('workflows', {})

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow config by ID"""
        return self.workflows.get(workflow_id)

    def list_workflows(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all workflows, optionally filtered by category"""
        workflows = list(self.workflows.values())
        if category:
            workflows = [w for w in workflows if w.get('category') == category]
        return workflows

    def validate_params(self, workflow_id: str, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate parameters against workflow config"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False, f"Workflow '{workflow_id}' not found"

        configurable = workflow.get('configurable_params', {})

        for param_name, param_value in params.items():
            if param_name not in configurable:
                return False, f"Parameter '{param_name}' not supported"

            param_config = configurable[param_name]
            param_type = param_config['type']

            # Type validation
            if param_type == 'int' and not isinstance(param_value, int):
                return False, f"Parameter '{param_name}' must be int"
            if param_type == 'float' and not isinstance(param_value, (int, float)):
                return False, f"Parameter '{param_name}' must be float"

            # Range validation
            if 'min' in param_config and param_value < param_config['min']:
                return False, f"Parameter '{param_name}' below minimum {param_config['min']}"
            if 'max' in param_config and param_value > param_config['max']:
                return False, f"Parameter '{param_name}' above maximum {param_config['max']}"

        return True, None

    def get_default_params(self, workflow_id: str) -> Dict[str, Any]:
        """Get default parameters for a workflow"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {}

        defaults = {}
        for param_name, param_config in workflow.get('configurable_params', {}).items():
            defaults[param_name] = param_config.get('default')

        return defaults
```

### 3. Updated API Structure

```python
# api/main.py
from fastapi import FastAPI, HTTPException
from services.workflow_manager import WorkflowManager
from services.comfyui_service import ComfyUIService

app = FastAPI(title="ComfyUI Generation API", version="2.0.0")
workflow_manager = WorkflowManager()
comfyui_service = ComfyUIService()

# Get all available workflows
@app.get("/api/v1/workflows")
async def list_workflows(category: Optional[str] = None):
    """List all available workflows"""
    workflows = workflow_manager.list_workflows(category)
    return {"workflows": workflows}

# Get specific workflow details
@app.get("/api/v1/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow configuration and parameters"""
    workflow = workflow_manager.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

# Generate with any workflow
@app.post("/api/v1/generate")
async def generate(request: GenerateRequest):
    """
    Universal generation endpoint
    Works with any workflow from registry
    """
    # Validate workflow exists
    workflow = workflow_manager.get_workflow(request.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Validate parameters
    valid, error = workflow_manager.validate_params(
        request.workflow_id,
        request.params or {}
    )
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    # Get character
    character = get_character(request.character_id)

    # Generate
    result = await comfyui_service.generate(
        character=character,
        workflow_path=workflow['workflow_path'],
        input_image_filename=request.input_image,
        prompt_additions=request.prompt,
        sampler_overrides=request.params,
        lora_strength_override=request.params.get('lora_strength')
    )

    return result
```

## Benefits of This Architecture

✅ **Scalable**: Easy to add new workflows without changing code
✅ **Maintainable**: Clear separation of concerns
✅ **Type-safe**: Parameter validation at API level
✅ **Self-documenting**: Registry describes all capabilities
✅ **UI-friendly**: Frontend can dynamically generate forms from registry
✅ **Version control**: Workflows are just JSON files
✅ **Testable**: Each layer can be tested independently

## Next Steps

1. Implement `WorkflowManager` service
2. Create workflow registry JSON
3. Update API to use workflow manager
4. Build React UI that reads from `/api/v1/workflows`
5. Add database layer for job queue and results

## Example Frontend Usage

```typescript
// React component automatically generates form from workflow config
const WorkflowForm = () => {
  const { data: workflow } = useQuery('/api/v1/workflows/qwen_single');

  return (
    <form>
      {Object.entries(workflow.configurable_params).map(([name, config]) => (
        <SliderInput
          key={name}
          label={name}
          min={config.min}
          max={config.max}
          default={config.default}
          description={config.description}
        />
      ))}
    </form>
  );
};
```
