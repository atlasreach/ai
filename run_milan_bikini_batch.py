#!/usr/bin/env python3
"""
Batch process all 120 bikini images with Milan's face
Uses the Milan_Bikini_Batch.json workflow via SSH
"""

import json
import subprocess
import glob
import time
import random

# RunPod Configuration
RUNPOD_HOST = "149.36.1.167"
RUNPOD_PORT = 43613
SSH_KEY = "/home/codespace/.ssh/id_ed25519"
COMFYUI_URL = "http://127.0.0.1:8188"

# Paths on RunPod
WORKFLOW_PATH = "/workspace/ComfyUI/user/default/workflows/Milan_Bikini_Batch.json"
INPUT_FOLDER = "/workspace/ComfyUI/input/bikini_pics"

def ssh_command(cmd):
    """Execute command on RunPod via SSH"""
    full_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", str(RUNPOD_PORT), "-i", SSH_KEY,
        f"root@{RUNPOD_HOST}",
        cmd
    ]
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    return result.stdout.strip()

def get_all_bikini_images():
    """Get list of all bikini images from RunPod"""
    cmd = f"ls {INPUT_FOLDER}/*.jpg {INPUT_FOLDER}/*.png 2>/dev/null | xargs -n 1 basename"
    result = ssh_command(cmd)
    return [img.strip() for img in result.split('\n') if img.strip()]

def load_workflow():
    """Load workflow from RunPod"""
    cmd = f"cat {WORKFLOW_PATH}"
    result = ssh_command(cmd)
    return json.loads(result)

def submit_prompt(workflow, image_name):
    """Submit a prompt to ComfyUI"""
    # Update image name
    workflow["1"]["inputs"]["image"] = image_name

    # Randomize seed
    workflow["10"]["inputs"]["seed"] = random.randint(1, 2**32 - 1)

    # Create payload
    payload = {
        "prompt": workflow,
        "client_id": f"batch_{int(time.time())}_{random.randint(1000,9999)}"
    }

    # Save to temp file locally
    temp_file = f"/tmp/comfy_workflow_{int(time.time())}.json"
    with open(temp_file, 'w') as f:
        json.dump(payload, f)

    # Upload to RunPod
    scp_cmd = [
        "scp", "-o", "StrictHostKeyChecking=no",
        "-P", str(RUNPOD_PORT), "-i", SSH_KEY,
        temp_file,
        f"root@{RUNPOD_HOST}:/tmp/batch_payload.json"
    ]
    subprocess.run(scp_cmd, check=True, capture_output=True)

    # Submit via curl on RunPod
    curl_cmd = f"curl -s -X POST {COMFYUI_URL}/prompt -H 'Content-Type: application/json' -d @/tmp/batch_payload.json"
    result = ssh_command(curl_cmd)

    try:
        response = json.loads(result)
        return response.get("prompt_id")
    except:
        return None

def main():
    print("\n" + "="*60)
    print("MILAN BIKINI BATCH GENERATOR")
    print("="*60)

    # Get all images
    print("\n📁 Loading image list from RunPod...")
    images = get_all_bikini_images()

    if not images:
        print("❌ No images found!")
        return

    print(f"✓ Found {len(images)} bikini reference images")

    # Load workflow
    print(f"\n📄 Loading workflow from RunPod...")
    workflow = load_workflow()
    print(f"✓ Workflow loaded")

    print(f"\n🚀 Starting batch generation...")
    print(f"   This will process all {len(images)} images")
    print(f"   Each image takes ~30-60 seconds\n")

    # Process each image
    successful = 0
    failed = 0

    for i, image_name in enumerate(images, 1):
        print(f"[{i:3d}/{len(images)}] {image_name[:40]:<40}", end=" ")

        try:
            prompt_id = submit_prompt(workflow.copy(), image_name)
            if prompt_id:
                print(f"✓ Queued ({prompt_id[:8]}...)")
                successful += 1
                # Small delay to avoid overwhelming queue
                time.sleep(0.3)
            else:
                print(f"✗ Failed to queue")
                failed += 1
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1

    print(f"\n" + "="*60)
    print(f"BATCH SUBMISSION COMPLETE")
    print(f"="*60)
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")
    print(f"\n💡 Images will process in ComfyUI queue")
    print(f"   Monitor progress in ComfyUI web interface")
    print(f"   Output: /workspace/ComfyUI/output/Milan_Bikini_*.png")
    print(f"="*60 + "\n")

if __name__ == "__main__":
    main()
