"""
Training API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.training_service import TrainingService

router = APIRouter(prefix="/api/training", tags=["training"])


class StartTrainingRequest(BaseModel):
    dataset_id: str
    gpu_type: str = "rtx6000"  # rtx6000 or 5090
    rank: int = 16  # 16 or 32
    steps: int = 2000
    lr: float = 0.0002
    save_every_n_steps: int = 500


class TrainingStatusResponse(BaseModel):
    status: str  # not_started, queued, running, completed, failed
    progress: int
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    job_id: Optional[str] = None
    lora_url: Optional[str] = None
    huggingface_url: Optional[str] = None
    error: Optional[str] = None


@router.post("/start")
async def start_training(request: StartTrainingRequest):
    """
    Start a training job on Runpod

    Body:
    {
        "dataset_id": "uuid",
        "gpu_type": "rtx6000",  // or "5090"
        "rank": 16,  // or 32
        "steps": 2000,
        "lr": 0.0002
    }

    Returns:
    {
        "success": true,
        "job_id": "uuid",
        "message": "Training started"
    }
    """
    try:
        training_config = {
            'gpu_type': request.gpu_type,
            'rank': request.rank,
            'steps': request.steps,
            'lr': request.lr,
            'save_every_n_steps': request.save_every_n_steps
        }

        job_id = TrainingService.start_training_job(
            request.dataset_id,
            training_config
        )

        return {
            "success": True,
            "job_id": job_id,
            "message": "Training job started successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_training_status(job_id: str):
    """
    Get training job status

    Returns:
    {
        "status": "running",
        "progress": 45,
        "current_step": 900,
        "total_steps": 2000
    }
    """
    try:
        status_data = TrainingService.check_training_status(job_id)

        # Auto-upload to HuggingFace when training completes
        if status_data.get('status') == 'completed':
            from supabase import create_client
            from dotenv import load_dotenv
            import threading

            load_dotenv()
            supabase = create_client(
                os.getenv('SUPABASE_URL'),
                os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            )

            # Get dataset from job_id
            dataset = supabase.table('training_datasets').select('*').eq('runpod_job_id', job_id).single().execute()

            if dataset.data:
                dataset_id = dataset.data['id']
                hf_url = dataset.data.get('huggingface_url')
                training_status = dataset.data.get('training_status')

                # Only trigger upload if not already uploaded or uploading
                if not hf_url and training_status not in ['uploading', 'uploaded']:
                    # Update status to uploading
                    supabase.table('training_datasets').update({
                        'training_status': 'uploading'
                    }).eq('id', dataset_id).execute()

                    # Trigger upload in background thread
                    def upload_in_background():
                        try:
                            result = TrainingService.download_lora(dataset_id)

                            # After successful upload, generate validation images
                            if result and result.get('checkpoints'):
                                print(f"🖼️  Starting validation image generation for {len(result['checkpoints'])} checkpoints...")

                                # Generate validation images in async context
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                                try:
                                    validation_images = loop.run_until_complete(
                                        TrainingService.generate_validation_images(dataset_id, result['checkpoints'])
                                    )
                                    print(f"✅ Generated {len(validation_images)} validation images")
                                finally:
                                    loop.close()

                        except Exception as e:
                            print(f"❌ Auto-upload failed: {e}")

                    thread = threading.Thread(target=upload_in_background)
                    thread.daemon = True
                    thread.start()

                    status_data['status'] = 'uploading'
                    status_data['message'] = 'Training complete, uploading to HuggingFace...'

        return {
            "success": True,
            **status_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download/{dataset_id}")
async def download_lora(dataset_id: str):
    """
    Download completed LoRA and upload to Hugging Face

    Returns:
    {
        "success": true,
        "huggingface_url": "https://huggingface.co/...",
        "lora_download_url": "https://...",
        "file_size_mb": 317.5,
        "filename": "character-name-lora.safetensors",
        "repo_id": "nicksanford2341/character-name-lora"
    }
    """
    try:
        result = TrainingService.download_lora(dataset_id)

        return {
            "success": True,
            **result,
            "message": "LoRA downloaded and uploaded to Hugging Face"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{dataset_id}")
async def export_dataset_zip(dataset_id: str):
    """
    Export dataset as ZIP for manual upload
    (For users who want to upload manually to AiToolkit)

    Returns: ZIP file download
    """
    try:
        from fastapi.responses import StreamingResponse

        dataset_data = TrainingService.prepare_dataset(dataset_id)
        zip_buffer = TrainingService.create_training_zip(dataset_data)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={dataset_data['dataset']['name']}.zip"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-pod/{dataset_id}")
async def stop_training_pod(dataset_id: str):
    """
    Stop the training pod for a dataset (to save costs)

    Returns:
    {
        "success": true,
        "message": "Pod stopped"
    }
    """
    try:
        from supabase import create_client
        import os
        from dotenv import load_dotenv

        load_dotenv()
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )

        # Get pod ID from dataset
        dataset = supabase.table('training_datasets').select('*').eq('id', dataset_id).single().execute()

        if not dataset.data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        pod_id = dataset.data.get('runpod_pod_id')
        if not pod_id:
            raise HTTPException(status_code=400, detail="No pod ID found for this dataset")

        TrainingService.stop_pod(pod_id)

        return {
            "success": True,
            "message": "Pod stopped successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
