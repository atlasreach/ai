#!/usr/bin/env python3
"""
Batch image generation via ComfyUI API
Generates multiple images in parallel using batch processing
"""
import json
import requests
import time
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any
import random

# Configuration
RUNPOD_HOST = "38.80.152.249"
RUNPOD_PORT = 30206
RUNPOD_SSH_KEY = "/home/codespace/.ssh/id_ed25519"
COMFYUI_URL = "http://127.0.0.1:3001"

# Available LoRas
LORAS = {
    "milan": "milan_000002000.safetensors",
    "skyler": "skyler_000002000.safetensors",
    "1girl": "1girlqwen.safetensors",
}

def load_workflow(workflow_path: str) -> Dict[str, Any]:
    """Load workflow JSON"""
    with open(workflow_path, 'r') as f:
        return json.load(f)

def update_workflow(
    workflow: Dict[str, Any],
    prompt: str,
    lora: str,
    lora_strength: float,
    batch_size: int,
    steps: int,
    seed: int
) -> Dict[str, Any]:
    """Update workflow parameters"""

    # Update LoRa
    workflow["74"]["inputs"]["lora_name"] = lora
    workflow["74"]["inputs"]["strength_model"] = lora_strength

    # Update prompt
    workflow["6"]["inputs"]["text"] = prompt

    # Update batch size
    workflow["58"]["inputs"]["batch_size"] = batch_size

    # Update sampler settings
    workflow["3"]["inputs"]["steps"] = steps
    workflow["3"]["inputs"]["seed"] = seed

    return workflow

def submit_via_ssh(workflow: Dict[str, Any]) -> str:
    """Submit workflow to ComfyUI via SSH"""

    # Create payload
    payload = {
        "prompt": workflow,
        "client_id": f"batch_api_{int(time.time())}_{random.randint(1000,9999)}"
    }

    # Save to temp file
    temp_file = f"/tmp/batch_workflow_{int(time.time())}.json"
    with open(temp_file, 'w') as f:
        json.dump(payload, f)

    # Upload to RunPod
    cmd = [
        "scp", "-o", "StrictHostKeyChecking=no",
        "-P", str(RUNPOD_PORT), "-i", RUNPOD_SSH_KEY,
        temp_file,
        f"root@{RUNPOD_HOST}:/tmp/batch_payload.json"
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    # Submit via SSH curl
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", str(RUNPOD_PORT), "-i", RUNPOD_SSH_KEY,
        f"root@{RUNPOD_HOST}",
        f"curl -s -X POST {COMFYUI_URL}/prompt -H 'Content-Type: application/json' -d @/tmp/batch_payload.json"
    ]

    result = subprocess.run(ssh_cmd, capture_output=True, text=True, check=True)
    response = json.loads(result.stdout)

    return response.get("prompt_id")

def check_status(prompt_id: str) -> Dict[str, Any]:
    """Check generation status"""
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", str(RUNPOD_PORT), "-i", RUNPOD_SSH_KEY,
        f"root@{RUNPOD_HOST}",
        f"curl -s {COMFYUI_URL}/history/{prompt_id}"
    ]

    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    try:
        history = json.loads(result.stdout)
        if prompt_id in history:
            return history[prompt_id]
    except:
        pass
    return {}

def wait_for_completion(prompt_ids: List[str], timeout: int = 600) -> Dict[str, Any]:
    """Wait for all generations to complete"""
    start = time.time()
    completed = {}

    print(f"\n⏳ Waiting for {len(prompt_ids)} batches to complete...")

    while len(completed) < len(prompt_ids):
        if time.time() - start > timeout:
            print(f"\n⏱️  Timeout after {timeout}s")
            break

        for prompt_id in prompt_ids:
            if prompt_id in completed:
                continue

            history = check_status(prompt_id)
            if history:
                status = history.get("status", {})

                if status.get("completed"):
                    outputs = history.get("outputs", {})
                    images = []
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            images.extend(node_output["images"])

                    completed[prompt_id] = {
                        "images": images,
                        "status": "success"
                    }
                    print(f"   ✅ Batch {len(completed)}/{len(prompt_ids)} complete ({len(images)} images)")

                elif "error" in status:
                    completed[prompt_id] = {
                        "status": "error",
                        "error": status.get("error")
                    }
                    print(f"   ❌ Batch failed: {status.get('error')}")

        time.sleep(2)

    return completed

def download_images(results: Dict[str, Any], output_dir: str) -> List[str]:
    """Download all generated images"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    downloaded = []

    print(f"\n📥 Downloading images to {output_dir}...")

    for prompt_id, result in results.items():
        if result["status"] != "success":
            continue

        for i, img_info in enumerate(result["images"]):
            filename = img_info["filename"]
            subfolder = img_info.get("subfolder", "")

            if subfolder:
                remote_path = f"/workspace/ComfyUI/output/{subfolder}/{filename}"
            else:
                remote_path = f"/workspace/ComfyUI/output/{filename}"

            local_path = output_path / filename

            cmd = [
                "scp", "-o", "StrictHostKeyChecking=no",
                "-P", str(RUNPOD_PORT), "-i", RUNPOD_SSH_KEY,
                f"root@{RUNPOD_HOST}:{remote_path}",
                str(local_path)
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
                downloaded.append(str(local_path))
            except:
                print(f"   ⚠️  Failed to download {filename}")

    print(f"   ✓ Downloaded {len(downloaded)} images")
    return downloaded

def generate_batch(
    prompts: List[str],
    lora: str = "milan",
    lora_strength: float = 0.8,
    batch_size: int = 4,
    steps: int = 20,
    output_dir: str = "./outputs/batch",
    workflow_path: str = "/workspaces/ai/workflows/qwen/txt2img_batch_fast.json"
) -> List[str]:
    """
    Generate multiple batches of images

    Args:
        prompts: List of prompts to generate
        lora: Which LoRa to use (milan, skyler, 1girl)
        lora_strength: LoRa strength (0.0-1.0)
        batch_size: Images per batch
        steps: Sampling steps (15-30)
        output_dir: Where to save images
        workflow_path: Path to batch workflow JSON

    Returns:
        List of downloaded image paths
    """

    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"🎨 BATCH IMAGE GENERATION")
    print(f"{'='*60}")
    print(f"Prompts: {len(prompts)}")
    print(f"Batch size: {batch_size}")
    print(f"Total images: {len(prompts) * batch_size}")
    print(f"LoRa: {LORAS.get(lora, lora)}")
    print(f"Steps: {steps}")
    print(f"{'='*60}\n")

    # Load base workflow
    workflow = load_workflow(workflow_path)
    lora_file = LORAS.get(lora, lora)

    # Submit all batches
    prompt_ids = []

    for i, prompt_text in enumerate(prompts, 1):
        print(f"📤 Submitting batch {i}/{len(prompts)}: {prompt_text[:50]}...")

        # Update workflow
        seed = random.randint(1, 1000000)
        updated_workflow = update_workflow(
            workflow.copy(),
            prompt_text,
            lora_file,
            lora_strength,
            batch_size,
            steps,
            seed
        )

        # Submit
        try:
            prompt_id = submit_via_ssh(updated_workflow)
            if prompt_id:
                prompt_ids.append(prompt_id)
                print(f"   ✓ Queued (ID: {prompt_id[:8]}...)")
        except Exception as e:
            print(f"   ❌ Failed: {e}")

    if not prompt_ids:
        print("\n❌ No batches submitted")
        return []

    # Wait for completion
    results = wait_for_completion(prompt_ids)

    # Download images
    downloaded = download_images(results, output_dir)

    total_time = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"✅ BATCH GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total images: {len(downloaded)}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"Time per image: {total_time/len(downloaded):.1f}s")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    return downloaded

def main():
    parser = argparse.ArgumentParser(description="Batch image generation")
    parser.add_argument("--prompts", nargs="+", required=True, help="Prompts to generate")
    parser.add_argument("--lora", default="milan", choices=["milan", "skyler", "1girl"], help="LoRa to use")
    parser.add_argument("--strength", type=float, default=0.8, help="LoRa strength")
    parser.add_argument("--batch-size", type=int, default=4, help="Images per batch")
    parser.add_argument("--steps", type=int, default=20, help="Sampling steps")
    parser.add_argument("--output", default="./outputs/batch", help="Output directory")

    args = parser.parse_args()

    images = generate_batch(
        prompts=args.prompts,
        lora=args.lora,
        lora_strength=args.strength,
        batch_size=args.batch_size,
        steps=args.steps,
        output_dir=args.output
    )

    print(f"\nGenerated {len(images)} images:")
    for img in images[:10]:
        print(f"  - {img}")
    if len(images) > 10:
        print(f"  ... and {len(images) - 10} more")

if __name__ == "__main__":
    # Example usage if run without arguments
    if len(__import__("sys").argv) == 1:
        print("Example usage:")
        print('  python batch_generate.py --prompts "milan, beach photo" "milan, city street" "milan, studio portrait" --batch-size 8 --lora milan')
        print("\nOr use programmatically:")
        print('  from batch_generate import generate_batch')
        print('  images = generate_batch(["prompt 1", "prompt 2"], lora="milan", batch_size=4)')
    else:
        main()
