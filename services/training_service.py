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
    def get_hf_username() -> str:
        """Get HuggingFace username from API token"""
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=HUGGINGFACE_TOKEN)
            user_info = api.whoami()
            return user_info['name']
        except Exception as e:
            raise Exception(f"Failed to get HuggingFace username: {e}")

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
    def generate_kohya_config(dataset_data: Dict, config: Dict, dataset_path: str) -> str:
        """
        Generate Kohya sd-scripts config (TOML format)

        Args:
            dataset_data: Output from prepare_dataset()
            config: Training configuration {gpu_type, rank, steps, lr}
            dataset_path: Path to training data on pod
        """
        character = dataset_data['character']
        dataset = dataset_data['dataset']

        # Determine batch size based on GPU
        gpu_type = config.get('gpu_type', 'rtx6000')
        batch_size = 1 if gpu_type == '5090' else 1

        config_toml = f"""# Kohya LoRA Training Config
# Dataset: {dataset['name']}
# Character: {character['name']} ({character['trigger_word']})

[general]
pretrained_model_name_or_path = "/workspace/models/flux1-dev.safetensors"
clip_l = "/workspace/models/clip_l.safetensors"
t5xxl = "/workspace/models/t5xxl_fp16.safetensors"
ae = "/workspace/models/ae.safetensors"
train_data_dir = "{dataset_path}"
output_dir = "/workspace/kohya_output/{dataset['name']}"
output_name = "{dataset['name']}_lora"

[network]
network_module = "networks.lora_flux"
network_dim = {config.get('rank', 16)}
network_alpha = {config.get('rank', 16)}

[training]
learning_rate = {config.get('lr', 0.0002)}
max_train_steps = {config.get('steps', 2000)}
train_batch_size = {batch_size}
gradient_accumulation_steps = 1
gradient_checkpointing = true
mixed_precision = "bf16"
save_precision = "bf16"
optimizer_type = "AdamW"

[dataset]
resolution = "1024,1024"
caption_extension = ".txt"
caption_dropout_rate = 0.05
shuffle_caption = false
keep_tokens = 1
cache_latents = true
cache_latents_to_disk = true

[saving]
save_every_n_steps = {config.get('save_every_n_steps', 500)}
save_model_as = "safetensors"
save_last_n_steps_state = 4

[logging]
logging_dir = "{dataset_path}/logs"
log_with = "tensorboard"
"""
        return config_toml

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

                    # Add caption txt (use trigger word if caption is empty)
                    caption_filename = f"image_{i+1:03d}.txt"
                    caption_text = img['caption'] if img.get('caption') else dataset_data['character']['trigger_word']
                    zip_file.writestr(caption_filename, caption_text)

                    print(f"  ✅ Added {image_filename}")
                else:
                    print(f"  ⚠️  Failed to download {image_url}")

        zip_buffer.seek(0)
        print(f"✅ ZIP created with {len(dataset_data['images'])} image pairs")
        return zip_buffer

    @staticmethod
    def upload_to_runpod(zip_buffer: BytesIO, config_content: str, dataset_name: str, ssh_url: str, ssh_port: int, upload_path: str) -> str:
        """
        Upload dataset and config to Runpod via SCP/SSH
        Returns: upload_path on pod
        """
        print("📤 Uploading to Runpod via SSH...")

        try:
            import subprocess
            import tempfile

            # Save ZIP to temp file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
                tmp_zip.write(zip_buffer.read())
                tmp_zip_path = tmp_zip.name

            # Save config to temp file (TOML for Kohya)
            with tempfile.NamedTemporaryFile(suffix='.toml', delete=False, mode='w') as tmp_config:
                tmp_config.write(config_content)
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
                print(f"  Uploading config TOML...")
                scp_config_cmd = f"scp -o StrictHostKeyChecking=no -P {ssh_port} {tmp_config_path} {ssh_url}:{upload_path}/config.toml"
                subprocess.run(scp_config_cmd, shell=True, check=True, capture_output=True)

                # Unzip on pod into subfolder (Kohya expects parent/subfolder structure)
                print(f"  Extracting dataset into subfolder...")
                unzip_cmd = f"ssh -o StrictHostKeyChecking=no -p {ssh_port} {ssh_url} 'cd {upload_path} && mkdir -p 10_character && unzip -q dataset.zip -d 10_character && rm dataset.zip'"
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

            # 3. Generate upload path
            import uuid
            training_id = str(uuid.uuid4())[:8]
            upload_path = f"/workspace/training_data_{training_id}"

            # 4. Generate Kohya config
            config_toml = TrainingService.generate_kohya_config(dataset_data, training_config, upload_path)

            # 5. Create ZIP
            zip_buffer = TrainingService.create_training_zip(dataset_data)

            # 6. Upload to Runpod
            TrainingService.upload_to_runpod(
                zip_buffer,
                config_toml,
                dataset_data['dataset']['name'],
                ssh_url,
                ssh_port,
                upload_path
            )

            # 7. Kill any existing training processes to free GPU memory
            import subprocess
            import time

            print(f"🧹 Cleaning up old training processes...")
            cleanup_cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -p {ssh_port} {ssh_url} 'pkill -9 -f flux_train_network.py'"

            try:
                subprocess.run(cleanup_cmd, shell=True, timeout=30, capture_output=True)
                print(f"   ✅ Killed old training processes")
            except Exception as e:
                print(f"   Note: No old processes to kill ({e})")

            # Wait for GPU memory to be released
            time.sleep(3)

            # 8. Start training via SSH with Kohya (run in background with nohup)
            # Use a simple command that returns immediately
            train_command = f"cd /workspace/sd-scripts && nohup python3 flux_train_network.py --config {upload_path}/config.toml > {upload_path}/training.log 2>&1 </dev/null &"
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -p {ssh_port} {ssh_url} '{train_command}' &"

            print(f"🚀 Starting training on pod (non-blocking)...")

            # Start in background - don't wait for completion
            subprocess.Popen(ssh_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Give it a moment to start
            time.sleep(2)

            print(f"✅ Training command sent to pod (running in background)")

            # 9. Create job record
            job_id = str(uuid.uuid4())

            # 10. Update dataset with job info
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
        Check training job status by parsing training.log on pod

        Returns: {status, progress, current_step, total_steps, logs, error}
        """
        try:
            # Get dataset from job_id
            dataset_result = supabase.table('training_datasets').select('*').eq('runpod_job_id', job_id).single().execute()
            dataset = dataset_result.data

            if not dataset:
                return {
                    'status': 'not_found',
                    'progress': 0,
                    'error': 'Job not found'
                }

            training_path = dataset.get('training_path')
            training_config = dataset.get('training_config', {})
            total_steps = training_config.get('steps', 2000)
            dataset_name = dataset.get('name')

            if not training_path:
                return {
                    'status': 'not_started',
                    'progress': 0,
                    'error': 'Training path not found'
                }

            # Get pod SSH details
            pod_status = TrainingService.get_pod_status()
            ssh_url = pod_status['ssh_url']
            ssh_port = pod_status['ssh_port']

            # Check if training completed (final LoRA file exists)
            output_dir = f"/workspace/kohya_output/{dataset_name}"
            lora_filename = f"{dataset_name}_lora.safetensors"
            lora_path = f"{output_dir}/{lora_filename}"

            import subprocess

            check_complete_cmd = f"ssh -o StrictHostKeyChecking=no -p {ssh_port} {ssh_url} 'test -f {lora_path} && echo exists || echo missing'"
            result = subprocess.run(check_complete_cmd, shell=True, capture_output=True, text=True, timeout=30)

            if 'exists' in result.stdout:
                # Training completed
                return {
                    'status': 'completed',
                    'progress': 100,
                    'current_step': total_steps,
                    'total_steps': total_steps
                }

            # Read training log to get current progress
            log_path = f"{training_path}/training.log"
            read_log_cmd = f"ssh -o StrictHostKeyChecking=no -p {ssh_port} {ssh_url} 'tail -n 50 {log_path} 2>/dev/null || echo \"Log not found\"'"
            log_result = subprocess.run(read_log_cmd, shell=True, capture_output=True, text=True, timeout=30)

            log_output = log_result.stdout

            if 'Log not found' in log_output or not log_output.strip():
                return {
                    'status': 'queued',
                    'progress': 0,
                    'current_step': 0,
                    'total_steps': total_steps,
                    'logs': 'Training starting...'
                }

            # Parse log for current step
            # Kohya logs look like: "steps: 450/2000" or "epoch 1, step 450"
            import re
            current_step = 0

            # Try to find step count in various formats
            # Kohya FLUX logs format: "steps: 29%|██▉ | 580/2000 [17:24<42:37, 1.80s/it]"
            step_patterns = [
                r'\|\s*(\d+)/(\d+)\s*\[',  # Match "| 580/2000 [" format (most reliable)
                r'steps?:\s*(\d+)/(\d+)',   # Match "steps: 580/2000" (fallback)
                r'step\s+(\d+)',             # Match "step 580" (generic)
                r'Steps:\s*(\d+)',           # Match "Steps: 580" (generic)
            ]

            for pattern in step_patterns:
                matches = re.findall(pattern, log_output, re.IGNORECASE)
                if matches:
                    if isinstance(matches[-1], tuple):
                        current_step = int(matches[-1][0])
                    else:
                        current_step = int(matches[-1])
                    break

            # Check for errors in log
            error_keywords = ['error', 'exception', 'failed', 'traceback']
            has_error = any(keyword in log_output.lower() for keyword in error_keywords)

            if has_error and current_step == 0:
                return {
                    'status': 'failed',
                    'progress': 0,
                    'current_step': 0,
                    'total_steps': total_steps,
                    'error': 'Training failed - check logs',
                    'logs': log_output[-1000:]  # Last 1000 chars
                }

            # Calculate progress
            progress = int((current_step / total_steps) * 100) if total_steps > 0 else 0

            return {
                'status': 'running',
                'progress': progress,
                'current_step': current_step,
                'total_steps': total_steps,
                'logs': log_output[-500:]  # Last 500 chars of log
            }

        except Exception as e:
            print(f"❌ Error checking training status: {e}")
            return {
                'status': 'error',
                'progress': 0,
                'error': str(e)
            }

    @staticmethod
    def download_lora(dataset_id: str) -> Dict:
        """
        Download trained LoRA from Runpod, upload to Hugging Face, update database

        Returns: dict with huggingface_url, download_url, file_size
        """
        print(f"\n📥 Downloading and uploading LoRA for dataset {dataset_id}...")

        try:
            # 1. Get dataset and character info
            dataset_result = supabase.table('training_datasets').select('*, characters(*)').eq('id', dataset_id).single().execute()
            dataset = dataset_result.data
            character = dataset['characters']

            if not dataset.get('training_path'):
                raise Exception("Training path not found in dataset")

            training_path = dataset['training_path']
            dataset_name = dataset['name']
            output_name = f"{dataset_name}_lora"

            print(f"   Dataset: {dataset_name}")
            print(f"   Character: {character['name']} ({character['trigger_word']})")

            # 2. Get pod SSH details
            pod_status = TrainingService.get_pod_status()
            ssh_url = pod_status['ssh_url']
            ssh_port = pod_status['ssh_port']

            # 3. Find ALL checkpoint files on pod (not just final)
            output_dir = f"/workspace/kohya_output/{dataset_name}"

            print(f"   Looking for checkpoints in: {output_dir}")

            # List all .safetensors files in output directory
            import subprocess
            list_cmd = f"ssh -o StrictHostKeyChecking=no -p {ssh_port} {ssh_url} 'ls {output_dir}/*.safetensors 2>/dev/null || echo none'"
            result = subprocess.run(list_cmd, shell=True, capture_output=True, text=True, timeout=30)

            if 'none' in result.stdout or not result.stdout.strip():
                raise Exception(f"No checkpoint files found in {output_dir}")

            # Parse checkpoint files
            checkpoint_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]

            # 4. Download and upload ALL checkpoints
            import tempfile
            import os
            import re

            print(f"   Found {len(checkpoint_files)} checkpoint(s): {[os.path.basename(f) for f in checkpoint_files]}")

            with tempfile.TemporaryDirectory() as tmpdir:
                from huggingface_hub import HfApi, create_repo, upload_file

                api = HfApi(token=HUGGINGFACE_TOKEN)

                # Get HuggingFace username dynamically
                hf_username = TrainingService.get_hf_username()

                # Get training steps from config
                training_config = dataset.get('training_config', {})
                max_steps = training_config.get('steps', 2000)

                # Create repo name with character, dataset, and steps
                repo_name = f"{character['name'].lower().replace(' ', '-')}-{dataset_name.lower().replace(' ', '-')}-{max_steps}steps-lora"
                repo_id = f"{hf_username}/{repo_name}"

                # Create repo once (ignore if exists)
                print(f"   Creating/verifying HuggingFace repo: {repo_id}")
                try:
                    create_repo(repo_id=repo_id, repo_type="model", private=False, exist_ok=True, token=HUGGINGFACE_TOKEN)
                except Exception as e:
                    print(f"   Note: {e}")

                # Download and upload each checkpoint
                checkpoint_info = []
                for checkpoint_path in checkpoint_files:
                    checkpoint_filename = os.path.basename(checkpoint_path)
                    local_path = os.path.join(tmpdir, checkpoint_filename)

                    print(f"   Downloading {checkpoint_filename}...")
                    scp_cmd = f"scp -o StrictHostKeyChecking=no -P {ssh_port} {ssh_url}:{checkpoint_path} {local_path}"
                    subprocess.run(scp_cmd, shell=True, check=True, timeout=300)

                    file_size_bytes = os.path.getsize(local_path)
                    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

                    # Extract step number from filename if present
                    step_match = re.search(r'-(\d+)\.safetensors$', checkpoint_filename)
                    step_num = int(step_match.group(1)) if step_match else max_steps

                    # Upload to HuggingFace with clear naming
                    hf_filename = f"checkpoint-{step_num}.safetensors"
                    print(f"   Uploading as {hf_filename} ({file_size_mb} MB)...")

                    upload_file(
                        path_or_fileobj=local_path,
                        path_in_repo=hf_filename,
                        repo_id=repo_id,
                        token=HUGGINGFACE_TOKEN
                    )

                    checkpoint_info.append({
                        'step': step_num,
                        'filename': hf_filename,
                        'size_mb': file_size_mb
                    })

                    print(f"   ✅ Uploaded checkpoint at step {step_num}")

                # Sort checkpoints by step
                checkpoint_info.sort(key=lambda x: x['step'])
                total_size_mb = sum(c['size_mb'] for c in checkpoint_info)

                # 5. Create model card with all checkpoints listed
                checkpoints_list = "\n".join([
                    f"- **[checkpoint-{c['step']}.safetensors]** ({c['size_mb']} MB) - Step {c['step']}"
                    for c in checkpoint_info
                ])

                model_card = f"""---
license: other
tags:
- flux
- lora
- character
base_model: black-forest-labs/FLUX.1-dev
---

# {character['name']} - {dataset_name}

LoRA trained on FLUX.1-dev with {dataset.get('image_count', 'N/A')} images.

**Trigger word:** `{character['trigger_word']}`

## Available Checkpoints

This repo contains {len(checkpoint_info)} checkpoint(s) from different training steps. You can download and compare them to find the best one for your use case.

{checkpoints_list}

**Total Size:** {total_size_mb} MB

## Usage

### In ComfyUI:
1. Download any `.safetensors` file from the Files tab
2. Place in `ComfyUI/models/loras/`
3. Use "Load LoRA" node
4. Set strength to 0.8-1.0
5. Include trigger word in prompt: "{character['trigger_word']}, [your prompt]"

**Tip:** Try different checkpoints! Earlier steps (500-1000) may give different results than final step ({max_steps}).

## Training Details
- **Total Steps:** {max_steps}
- **Checkpoints Saved:** {len(checkpoint_info)}
- **Save Frequency:** Every {training_config.get('save_every_n_steps', 500)} steps
- **Rank:** {training_config.get('rank', 16)}
- **Learning Rate:** {training_config.get('lr', 0.0002)}
- **Base Model:** FLUX.1-dev
- **Training Images:** {dataset.get('image_count', 'N/A')}

## Example Prompts
```
{character['trigger_word']}, professional portrait, studio lighting
{character['trigger_word']}, casual outdoor photo, natural light
{character['trigger_word']}, creative artistic style
```

---

*Generated with automated LoRA training system*
"""

                # Upload model card
                from io import BytesIO
                upload_file(
                    path_or_fileobj=BytesIO(model_card.encode('utf-8')),
                    path_in_repo="README.md",
                    repo_id=repo_id,
                    token=HUGGINGFACE_TOKEN
                )

                hf_url = f"https://huggingface.co/{repo_id}"

                # Use the latest checkpoint as the main download URL
                latest_checkpoint = checkpoint_info[-1]
                download_url = f"https://huggingface.co/{repo_id}/resolve/main/{latest_checkpoint['filename']}"

                print(f"   ✅ Uploaded to: {hf_url}")
                print(f"   ✅ Uploaded {len(checkpoint_info)} checkpoints")

                # 6. Update database with checkpoint info
                supabase.table('training_datasets').update({
                    'training_status': 'uploaded',
                    'huggingface_url': hf_url,
                    'lora_download_url': download_url,
                    'output_filename': latest_checkpoint['filename'],
                    'file_size_mb': total_size_mb,
                    'huggingface_repo': repo_id,
                    'checkpoints': checkpoint_info  # Store all checkpoint info
                }).eq('id', dataset_id).execute()

                print(f"   ✅ Database updated with {len(checkpoint_info)} checkpoints")

                return {
                    'huggingface_url': hf_url,
                    'download_url': download_url,
                    'file_size_mb': total_size_mb,
                    'filename': latest_checkpoint['filename'],
                    'repo_id': repo_id,
                    'checkpoints': checkpoint_info,
                    'checkpoint_count': len(checkpoint_info)
                }

        except Exception as e:
            print(f"   ❌ Error: {e}")

            # Update database with error
            supabase.table('training_datasets').update({
                'training_status': 'upload_failed',
                'training_error': str(e)
            }).eq('id', dataset_id).execute()

            raise

    @staticmethod
    async def generate_validation_images(dataset_id: str, checkpoints: List[Dict]) -> List[Dict]:
        """
        Generate validation images for each checkpoint using ComfyUI

        Args:
            dataset_id: Dataset ID
            checkpoints: List of checkpoint dicts with step, filename, etc.

        Returns:
            List of validation image records
        """
        print(f"\n🖼️  Generating validation images for dataset {dataset_id}...")

        try:
            # Get dataset and validation prompts
            dataset_result = supabase.table('training_datasets').select('*, characters(*)').eq('id', dataset_id).single().execute()
            dataset = dataset_result.data
            character = dataset['characters']

            validation_prompts = dataset.get('validation_prompts', [])
            if not validation_prompts:
                print("   ⚠️  No validation prompts found, skipping image generation")
                return []

            huggingface_repo = dataset.get('huggingface_repo')
            if not huggingface_repo:
                raise Exception("No HuggingFace repo found")

            print(f"   Found {len(validation_prompts)} validation prompts")
            print(f"   Generating images for {len(checkpoints)} checkpoints")

            # Import ComfyUI service
            from services.comfyui_service import ComfyUIService
            comfyui = ComfyUIService()

            validation_images = []

            # Generate images for each checkpoint
            for checkpoint in checkpoints:
                step = checkpoint['step']
                checkpoint_filename = checkpoint['filename']

                print(f"\n   📸 Checkpoint step {step}: Generating {len(validation_prompts)} images...")

                # Create temporary character dict with this checkpoint
                temp_character = {
                    'id': character['id'],
                    'name': character['name'],
                    'trigger_word': character['trigger_word'],
                    'lora_file': f"https://huggingface.co/{huggingface_repo}/resolve/main/{checkpoint_filename}",  # Direct HF URL
                    'lora_strength': 0.9
                }

                # Generate image for each validation prompt
                for prompt_idx, prompt in enumerate(validation_prompts):
                    try:
                        result = await comfyui.generate(
                            character=temp_character,
                            workflow_path="workflows/qwen/instagram_api_fast.json",
                            prompt_additions=prompt,
                            lora_strength_override=0.9
                        )

                        if result.get('success') and result.get('images'):
                            image_url = result['images'][0]

                            validation_images.append({
                                'dataset_id': dataset_id,
                                'checkpoint_step': step,
                                'prompt': prompt,
                                'prompt_index': prompt_idx,
                                'image_url': image_url,
                                'checkpoint_filename': checkpoint_filename
                            })

                            print(f"      ✅ Generated image {prompt_idx + 1}/{len(validation_prompts)}")
                        else:
                            print(f"      ⚠️  Failed to generate image {prompt_idx + 1}: {result.get('error', 'Unknown error')}")

                    except Exception as e:
                        print(f"      ❌ Error generating image: {e}")

            print(f"\n   ✅ Generated {len(validation_images)} validation images total")

            # Store in database
            if validation_images:
                # Create validation_images table entry or update dataset
                supabase.table('training_datasets').update({
                    'validation_images': validation_images
                }).eq('id', dataset_id).execute()

                print(f"   ✅ Stored validation images in database")

            return validation_images

        except Exception as e:
            print(f"   ❌ Error generating validation images: {e}")
            return []
