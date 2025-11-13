# Diffusers Setup Guide (Working Solution)

**Date**: November 13, 2025
**Status**: ✅ WORKING - Generates images with Milan LoRA

## What We Learned

### ComfyUI Issues (Why We Switched)
- ComfyUI kept crashing during generation (OOM, workflow format issues)
- Workflow JSON export format doesn't match API format (nodes as array vs dictionary)
- Harder to debug and customize
- Adds complexity we don't need for a production API

### Diffusers Solution (What Works)
- Direct Python API - no middleware
- Same quality output (uses same models)
- More stable and predictable
- Easier to integrate with FastAPI
- Better error handling

---

## RunPod Setup (CRITICAL - Save This!)

### Required Packages
```bash
pip install diffusers transformers accelerate peft torch
```

### Models Location
- **Base Qwen Model**: Auto-downloaded from HuggingFace (`Qwen/Qwen-Image`)
- **Milan LoRA**: `/workspace/ComfyUI/models/loras/milan_000002000.safetensors`

### Working Generation Script
Location: `/workspace/ai/runpod_generate.py`

**Key Configuration:**
```python
pipe = DiffusionPipeline.from_pretrained(
    "Qwen/Qwen-Image",
    scheduler=scheduler,
    torch_dtype=torch.bfloat16,
    device_map="balanced",  # Critical for VRAM management
    low_cpu_mem_usage=True
)

pipe.load_lora_weights("/workspace/ComfyUI/models/loras/milan_000002000.safetensors")
pipe.fuse_lora(lora_scale=0.8)
```

---

## Generation Parameters

### Basic Text-to-Image
```python
image = pipe(
    prompt="Milan, woman, professional photo, studio lighting",
    negative_prompt="blurry, low quality",
    width=1024,
    height=768,
    num_inference_steps=30,
    guidance_scale=4.0,
    generator=torch.manual_seed(12345),
).images[0]
```

### Parameter Guide
- **width/height**: 512-2048 (larger = more VRAM)
- **num_inference_steps**: 20-50 (more = better quality, slower)
- **guidance_scale**: 1-10 (higher = follow prompt more closely)
- **lora_scale**: 0.5-1.0 (strength of character LoRA)

---

## Next Steps (Architecture)

### Phase 1: RunPod API Server ✅ NEXT
Create FastAPI server on RunPod that:
- Accepts generation requests (prompt, character, settings)
- Loads appropriate LoRA based on character
- Returns image bytes or S3 URL

### Phase 2: Update Codespaces Backend
Change `comfyui_service.py` to call RunPod Diffusers API instead of ComfyUI

### Phase 3: Frontend
Build React UI with:
- Character selector (Milan, future characters)
- Prompt input
- Settings sliders (steps, guidance, etc.)
- Gallery of generated images

---

## Troubleshooting

### Out of Memory Errors
- Use `device_map="balanced"` not `"auto"`
- Reduce `num_inference_steps`
- Reduce image dimensions
- Clear GPU cache: `torch.cuda.empty_cache()`

### LoRA Not Loading
- Install: `pip install peft`
- Check file path exists
- Verify `.safetensors` format

### Slow Generation
- Normal: First generation takes 2-3 min (model loading)
- After: 60-90 seconds per image
- Use lower steps (20 instead of 30) for faster results

---

## Files to Keep

### On RunPod
- `/workspace/ai/runpod_generate.py` - Working generation script
- `/workspace/ComfyUI/models/loras/milan_000002000.safetensors` - Milan LoRA
- Dependencies: diffusers, peft, transformers, accelerate

### In Git Repo
- `backend/` - FastAPI backend
- `runpod_generate.py` - Generation script
- Documentation files

### Can Delete
- `test_*.py` - Debug scripts (no longer needed)
- `workflows/*.json` - ComfyUI workflows (not using anymore)
- `backend/services/comfyui_service.py` - Will replace with diffusers_service.py

---

## Cost Comparison

### RunPod Costs
- RTX 5090: ~$0.89/hour
- Generation: ~60-90 seconds = ~$0.015 per image
- Much cheaper than ComfyUI cloud services

### S3 Storage
- ~$0.023 per GB/month
- 1000 images (~500MB) = ~$0.01/month

**Total**: ~$0.015 per image generated

---

## Success Checklist

- [x] Diffusers installed on RunPod
- [x] Qwen-Image model loads
- [x] Milan LoRA loads successfully
- [x] Test generation completes
- [ ] API server on RunPod
- [ ] Backend integrated
- [ ] Frontend built
- [ ] End-to-end test works

---

**Last Updated**: November 13, 2025
**Next Task**: Build FastAPI server on RunPod for generation endpoint
