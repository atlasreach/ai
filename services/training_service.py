"""
Training Service - Automate LoRA training on Runpod with AiToolkit
"""
import os
import json
import uuid
import requests
import zipfile
from io import BytesIO
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

RUNPOD_TRAINING_POD_ID = os.getenv('RUNPOD_TRAINING_POD_ID')
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Runpod API base URL
RUNPOD_API_BASE = "https://api.runpod.io/graphql"


class TrainingService:
    """Manage LoRA training jobs on Runpod"""

    @staticmethod
    def _runpod_graphql(query: str, variables: Dict = None) -> Dict:
        """Execute Runpod GraphQL API request"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RUNPOD_API_KEY}"
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(RUNPOD_API_BASE, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_pod_status(pod_id: str = None) -> Dict:
        """Get pod status and connection info"""
        if not pod_id:
            pod_id = RUNPOD_TRAINING_POD_ID

        query = """
        query Pod($podId: String!) {
            pod(input: {podId: $podId}) {
                id
                name
                runtime {
                    uptimeInSeconds
                    ports {
                        ip
                        isIpPublic
                        privatePort
                        publicPort
                        type
                    }
                }
                desiredStatus
                imageName
                machineId
                machine {
                    gpuDisplayName
                }
            }
        }
        """

        result = TrainingService._runpod_graphql(query, {"podId": pod_id})
        pod_data = result.get("data", {}).get("pod")

        if not pod_data:
            raise Exception(f"Pod {pod_id} not found")

        # Get SSH connection details from exposed TCP port 22
        runtime = pod_data.get("runtime", {})
        ports = runtime.get("ports", [])
        ssh_port = next((p for p in ports if p.get("privatePort") == 22 and p.get("type") == "tcp"), None)

        if not ssh_port:
            raise Exception(f"SSH port (22) not exposed on pod {pod_id}. Please expose TCP port 22.")

        ssh_host = ssh_port.get("ip")
        ssh_port_num = ssh_port.get("publicPort")
        ssh_url = f"root@{ssh_host}"

        return {
            "id": pod_data["id"],
            "name": pod_data.get("name"),
            "status": pod_data.get("desiredStatus"),
            "gpu": pod_data.get("machine", {}).get("gpuDisplayName"),
            "ssh_host": ssh_host,
            "ssh_port": ssh_port_num,
            "ssh_url": ssh_url,
            "uptime": runtime.get("uptimeInSeconds", 0)
        }

    @staticmethod
    def start_pod(pod_id: str = None) -> Dict:
        """Start a stopped pod"""
        if not pod_id:
            pod_id = RUNPOD_TRAINING_POD_ID

        print(f"🟢 Starting pod {pod_id}...")

        query = """
        mutation StartPod($podId: String!) {
            podResume(input: {podId: $podId}) {
                id
                desiredStatus
            }
        }
        """

        result = TrainingService._runpod_graphql(query, {"podId": pod_id})

        # Wait for pod to be running (poll status)
        import time
        max_wait = 180  # 3 minutes
        waited = 0

        while waited < max_wait:
            status = TrainingService.get_pod_status(pod_id)
            if status["status"] == "RUNNING":
                print(f"✅ Pod is running")
                return status

            print(f"  Waiting for pod to start... ({waited}s)")
            time.sleep(10)
            waited += 10

        raise Exception(f"Pod failed to start within {max_wait}s")

    @staticmethod
    def stop_pod(pod_id: str = None) -> Dict:
        """Stop a running pod"""
        if not pod_id:
            pod_id = RUNPOD_TRAINING_POD_ID

        print(f"🔴 Stopping pod {pod_id}...")

        query = """
        mutation StopPod($podId: String!) {
            podStop(input: {podId: $podId}) {
                id
                desiredStatus
            }
        }
        """

        result = TrainingService._runpod_graphql(query, {"podId": pod_id})
        print(f"✅ Pod stop requested")

        return result

    @staticmethod
    def prepare_dataset(dataset_id: str) -> Dict:
        """
        Fetch dataset images and captions from Supabase
        Returns: {images: [...], character: {...}, dataset: {...}}
        """
        print(f"📦 Preparing dataset {dataset_id}...")

        # Get dataset info
        dataset_result = supabase.table('training_datasets').select('*').eq('id', dataset_id).single().execute()
        dataset = dataset_result.data

        if not dataset:
            raise Exception(f"Dataset {dataset_id} not found")

        # Get character info
        character_result = supabase.table('characters').select('*').eq('id', dataset['character_id']).single().execute()
        character = character_result.data

        # Get images with captions
        images_result = supabase.table('training_images').select('*').eq('dataset_id', dataset_id).order('display_order').execute()
        images = images_result.data

        print(f"✅ Dataset prepared: {len(images)} images")

        return {
            'dataset': dataset,
            'character': character,
            'images': images
        }

    @staticmethod
    def generate_aitoolkit_config(dataset_data: Dict, config: Dict) -> str:
        """
        Generate AiToolkit config YAML

        Args:
            dataset_data: Output from prepare_dataset()
            config: Training configuration {gpu_type, rank, steps, lr}
        """
        character = dataset_data['character']
        dataset = dataset_data['dataset']

        # Determine batch size based on GPU
        gpu_type = config.get('gpu_type', 'rtx6000')
        batch_size = 1 if gpu_type == '5090' else 1

        config_yaml = f"""job: extension
config:
  name: {dataset['name']}
  training_folder: "/app/ai-toolkit/output"
  process:
    - type: 'ui_trainer'
      training_folder: "/app/ai-toolkit/output"
      sqlite_db_path: "./aitk_db.db"
      device: cuda:0
      trigger_word: "{character['trigger_word']}"
      network:
        type: "lora"
        linear: {config.get('rank', 16)}
        linear_alpha: {config.get('rank', 16)}
      save:
        dtype: float16
        save_every: 500
        max_step_saves_to_keep: 4
      datasets:
        - folder_path: "/workspace/training_data"
          caption_ext: "txt"
          caption_dropout_rate: 0.05
          shuffle_tokens: false
          cache_latents_to_disk: true
          resolution: [1024, 1024]
      train:
        batch_size: {batch_size}
        steps: {config.get('steps', 2000)}
        gradient_accumulation_steps: 1
        train_unet: true
        train_text_encoder: false
        content_or_style: balanced
        gradient_checkpointing: true
        noise_scheduler: "flowmatch"
        optimizer: "adamw8bit"
        lr: {config.get('lr', 0.0002)}
        ema_config:
          use_ema: true
          ema_decay: 0.99
        dtype: bf16
  model:
    name_or_path: "Qwen/Qwen2-VL-2B-Instruct"
    is_v_pred: false
    is_flux: false
meta:
  name: "{dataset['name']}"
  version: '1.0'
"""
        return config_yaml

    @staticmethod
    def create_training_zip(dataset_data: Dict) -> BytesIO:
        """
        Create ZIP file with images and caption txt files
        Format: image_001.jpg + image_001.txt
        """
        print("📦 Creating training ZIP...")

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, img in enumerate(dataset_data['images']):
                # Download image from Supabase Storage
                image_url = img['image_url']
                image_response = requests.get(image_url)

                if image_response.status_code == 200:
                    # Add image
                    image_filename = f"image_{i+1:03d}.jpg"
                    zip_file.writestr(image_filename, image_response.content)

                    # Add caption txt
                    caption_filename = f"image_{i+1:03d}.txt"
                    zip_file.writestr(caption_filename, img['caption'])

                    print(f"  ✅ Added {image_filename}")
                else:
                    print(f"  ⚠️  Failed to download {image_url}")

        zip_buffer.seek(0)
        print(f"✅ ZIP created with {len(dataset_data['images'])} image pairs")
        return zip_buffer

    @staticmethod
    def upload_to_runpod(zip_buffer: BytesIO, config_yaml: str, dataset_name: str, ssh_url: str, ssh_port: int) -> str:
        """
        Upload dataset and config to Runpod via SCP/SSH
        Returns: upload_path on pod
        """
        print("📤 Uploading to Runpod via SSH...")

        # Create unique training folder
        training_id = str(uuid.uuid4())[:8]
        upload_path = f"/workspace/training_data_{training_id}"

        try:
            import subprocess
            import tempfile

            # Save ZIP to temp file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
                tmp_zip.write(zip_buffer.read())
                tmp_zip_path = tmp_zip.name

            # Save config to temp file
            with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False, mode='w') as tmp_config:
                tmp_config.write(config_yaml)
                tmp_config_path = tmp_config.name

            try:
                # Create directory on pod
                print(f"  Creating directory {upload_path}...")
                mkdir_cmd = f"ssh -o StrictHostKeyChecking=no -p {ssh_port} {ssh_url} 'mkdir -p {upload_path}'"
                subprocess.run(mkdir_cmd, shell=True, check=True, capture_output=True)

                # Upload ZIP file
                print(f"  Uploading dataset ZIP...")
                scp_zip_cmd = f"scp -o StrictHostKeyChecking=no -P {ssh_port} {tmp_zip_path} {ssh_url}:{upload_path}/dataset.zip"
                subprocess.run(scp_zip_cmd, shell=True, check=True, capture_output=True)

                # Upload config file
                print(f"  Uploading config YAML...")
                scp_config_cmd = f"scp -o StrictHostKeyChecking=no -P {ssh_port} {tmp_config_path} {ssh_url}:{upload_path}/config.yaml"
                subprocess.run(scp_config_cmd, shell=True, check=True, capture_output=True)

                # Unzip on pod
                print(f"  Extracting dataset...")
                unzip_cmd = f"ssh -o StrictHostKeyChecking=no -p {ssh_port} {ssh_url} 'cd {upload_path} && unzip -q dataset.zip && rm dataset.zip'"
                subprocess.run(unzip_cmd, shell=True, check=True, capture_output=True)

                print(f"✅ Dataset uploaded to {upload_path}")

            finally:
                # Clean up temp files
                os.unlink(tmp_zip_path)
                os.unlink(tmp_config_path)

            return upload_path

        except subprocess.CalledProcessError as e:
            error_msg = f"SSH/SCP failed: {e.stderr.decode() if e.stderr else str(e)}"
            print(f"❌ Upload error: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            print(f"❌ Upload error: {e}")
            raise

    @staticmethod
    def start_training_job(dataset_id: str, training_config: Dict) -> str:
        """
        Start training job on Runpod (auto-starts pod if stopped)

        Args:
            dataset_id: UUID of training_datasets record
            training_config: {gpu_type, rank, steps, lr}

        Returns:
            job_id (UUID)
        """
        print(f"\n🚀 Starting training job for dataset {dataset_id}")
        print(f"   Config: {training_config}")

        try:
            # 1. Check pod status and start if needed
            print("\n📡 Checking training pod status...")
            pod_status = TrainingService.get_pod_status()
            print(f"   Pod: {pod_status['name']} ({pod_status['gpu']})")
            print(f"   Status: {pod_status['status']}")

            if pod_status['status'] != 'RUNNING':
                print(f"   Pod is {pod_status['status']}, starting it...")
                pod_status = TrainingService.start_pod()

            ssh_url = pod_status['ssh_url']
            ssh_port = pod_status['ssh_port']

            # 2. Prepare dataset
            dataset_data = TrainingService.prepare_dataset(dataset_id)

            # 3. Generate config
            config_yaml = TrainingService.generate_aitoolkit_config(dataset_data, training_config)

            # 4. Create ZIP
            zip_buffer = TrainingService.create_training_zip(dataset_data)

            # 5. Upload to Runpod
            upload_path = TrainingService.upload_to_runpod(
                zip_buffer,
                config_yaml,
                dataset_data['dataset']['name'],
                ssh_url,
                ssh_port
            )

            # 6. Start training via SSH (run in background with nohup)
            import subprocess

            train_command = f"cd /app/ai-toolkit && nohup python3 run.py {upload_path}/config.yaml > {upload_path}/training.log 2>&1 &"
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no -p {ssh_port} {ssh_url} '{train_command}'"

            print(f"🚀 Starting training on pod...")
            result = subprocess.run(ssh_cmd, shell=True, check=True, capture_output=True, timeout=30)

            print(f"✅ Training command executed on pod")

            # 7. Create job record
            job_id = str(uuid.uuid4())

            # 8. Update dataset with job info
            supabase.table('training_datasets').update({
                'training_status': 'running',
                'runpod_job_id': job_id,
                'runpod_pod_id': RUNPOD_TRAINING_POD_ID,
                'training_progress': 0,
                'training_config': training_config,
                'training_path': upload_path
            }).eq('id', dataset_id).execute()

            print(f"✅ Training started! Job ID: {job_id}")

            return job_id

        except Exception as e:
            print(f"❌ Failed to start training: {e}")

            # Update status to failed
            supabase.table('training_datasets').update({
                'training_status': 'failed',
                'training_error': str(e)
            }).eq('id', dataset_id).execute()

            raise

    @staticmethod
    def check_training_status(job_id: str) -> Dict:
        """
        Check training job status

        Returns: {status, progress, logs, error}
        """
        # Query Runpod for job status
        # For now, return mock data - will implement actual polling
        return {
            'status': 'running',  # queued, running, completed, failed
            'progress': 0,
            'current_step': 0,
            'total_steps': 2000,
            'logs': ''
        }

    @staticmethod
    def download_lora(job_id: str, dataset_id: str) -> str:
        """
        Download trained LoRA from Runpod
        Upload to Hugging Face
        Update character record

        Returns: huggingface_url
        """
        print(f"📥 Downloading LoRA for job {job_id}...")

        # Get dataset info
        dataset_result = supabase.table('training_datasets').select('*').eq('id', dataset_id).single().execute()
        dataset = dataset_result.data

        # Download safetensors file from Runpod
        # This will be implemented based on Runpod's file download API

        # Upload to Hugging Face
        # Will implement with huggingface_hub library

        # Update database
        supabase.table('training_datasets').update({
            'training_status': 'completed',
            'lora_download_url': 'pending_implementation',
            'huggingface_url': 'pending_implementation'
        }).eq('id', dataset_id).execute()

        return 'pending_implementation'
