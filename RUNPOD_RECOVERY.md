# RunPod ComfyUI Recovery Guide

## If ComfyUI Crashes on RunPod

### Check ComfyUI Logs
```bash
tail -f /workspace/logs/comfyui.log
```

### Download Milan LoRA Model
If the Milan LoRA is missing after a pod restart:

```bash
cd /workspace/ComfyUI/models/loras

# Download from Hugging Face with resume support
wget -c "https://huggingface.co/nicksanford2341/businessmodels/resolve/main/milan_000002000.safetensors"
```

### Restart Backend Wrapper (in Codespaces)
```bash
# Kill old backend
pkill -f "runpod_comfyui_wrapper.py"

# Start new backend
cd /workspaces/ai && python3 runpod_comfyui_wrapper.py > /tmp/wrapper.log 2>&1 &

# Check logs
tail -20 /tmp/wrapper.log
```

### Update .env with New Pod ID
If you restart with a new RunPod pod, update these files:

**`/workspaces/ai/.env`**:
```
RUNPOD_POD_ID=your_new_pod_id
RUNPOD_API_URL=https://your_new_pod_id-3001.proxy.runpod.net
RUNPOD_SSH_URL=ssh root@your_new_pod_id.proxy.runpod.net
```

**`/workspaces/ai/runpod_comfyui_wrapper.py`** (line 51):
```python
COMFYUI_URL = "https://your_new_pod_id-3001.proxy.runpod.net"
```

## Current Configuration

- **Pod ID**: zly4w0etf28llh
- **ComfyUI URL**: https://zly4w0etf28llh-3001.proxy.runpod.net
- **React App**: Port 5173
- **Backend API**: Port 8001
- **Workflow**: `qwen instagram influencer workflow (Aiorbust).json`

## Common Issues

### Flash Attention Crashes (RTX 5090)
- **Symptom**: CUDA error at 0% generation
- **Cause**: Blackwell architecture incompatible with flash attention kernels
- **Solution**: Run ONE image at a time (not multiple simultaneously)

### Timeout Errors
- **Symptom**: "Network Error" in React app
- **Cause**: Image generation takes longer than frontend timeout
- **Solution**: Image still completes - check ComfyUI output folder or S3

### 502 Errors
- **Symptom**: History check returns 502
- **Cause**: ComfyUI overloaded or restarting
- **Solution**: Wait for current generation to complete, then restart
