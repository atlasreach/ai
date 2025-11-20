#!/usr/bin/env python3
"""
Run video-to-video processing via ComfyUI API
"""
import json
import requests
import time
import subprocess
import sys

# Configuration
RUNPOD_HOST = "38.80.152.249"
RUNPOD_PORT = 30206
RUNPOD_SSH_KEY = "/home/codespace/.ssh/id_ed25519"
COMFYUI_URL = "http://127.0.0.1:3001"

# Video settings
LOCAL_VIDEO = "/workspaces/ai/Instagram.mp4"
LORA_MODEL = "milan_000002000.safetensors"
PROMPT = "milan, high quality, detailed face, professional photo"

def upload_video_to_runpod(local_path: str, remote_name: str = "input_video.mp4"):
    """Upload video to RunPod ComfyUI input folder"""
    print(f"📤 Uploading {local_path} to RunPod...")

    remote_path = f"/workspace/ComfyUI/input/{remote_name}"
    cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-P", str(RUNPOD_PORT),
        "-i", RUNPOD_SSH_KEY,
        local_path,
        f"root@{RUNPOD_HOST}:{remote_path}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Upload failed: {result.stderr}")

    print(f"   ✓ Uploaded as {remote_name}")
    return remote_name

def run_via_ssh(workflow_path: str):
    """Submit workflow via SSH and curl to ComfyUI API"""
    print(f"🎬 Submitting workflow to ComfyUI API...")

    # Load workflow
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)

    # Update LoRa and prompt
    workflow["5"]["inputs"]["lora_name"] = LORA_MODEL
    workflow["6"]["inputs"]["text"] = PROMPT

    # Create API payload
    payload = {
        "prompt": workflow,
        "client_id": f"video_api_{int(time.time())}"
    }

    # Save to temp file
    temp_file = "/tmp/workflow_payload.json"
    with open(temp_file, 'w') as f:
        json.dump(payload, f)

    # Upload payload to RunPod
    print("   Uploading workflow payload...")
    cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-P", str(RUNPOD_PORT),
        "-i", RUNPOD_SSH_KEY,
        temp_file,
        f"root@{RUNPOD_HOST}:/tmp/workflow_payload.json"
    ]
    subprocess.run(cmd, check=True)

    # Submit via SSH
    print("   Submitting to ComfyUI API...")
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-p", str(RUNPOD_PORT),
        "-i", RUNPOD_SSH_KEY,
        f"root@{RUNPOD_HOST}",
        f"curl -s -X POST {COMFYUI_URL}/prompt -H 'Content-Type: application/json' -d @/tmp/workflow_payload.json"
    ]

    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    response = json.loads(result.stdout)

    if "prompt_id" in response:
        prompt_id = response["prompt_id"]
        print(f"   ✓ Submitted! Prompt ID: {prompt_id[:8]}...")
        return prompt_id
    else:
        print(f"   ❌ Submission failed: {response}")
        return None

def check_status(prompt_id: str):
    """Check processing status via SSH"""
    print(f"\n🔄 Checking status...")

    while True:
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-p", str(RUNPOD_PORT),
            "-i", RUNPOD_SSH_KEY,
            f"root@{RUNPOD_HOST}",
            f"curl -s {COMFYUI_URL}/history/{prompt_id}"
        ]

        result = subprocess.run(ssh_cmd, capture_output=True, text=True)

        try:
            history = json.loads(result.stdout)

            if prompt_id in history:
                status = history[prompt_id].get("status", {})

                if status.get("completed"):
                    print(f"   ✅ Processing complete!")
                    outputs = history[prompt_id].get("outputs", {})

                    # Find output video
                    for node_id, node_output in outputs.items():
                        if "gifs" in node_output:
                            video_info = node_output["gifs"][0]
                            filename = video_info["filename"]
                            print(f"   📹 Output: {filename}")
                            return filename
                    return None

                elif "error" in status:
                    print(f"   ❌ Error: {status.get('error')}")
                    return None

                else:
                    print(f"   ⏳ Processing...")
        except:
            pass

        time.sleep(5)

def download_result(filename: str, local_output: str = "/workspaces/ai/outputs/videos/output.mp4"):
    """Download processed video from RunPod"""
    print(f"\n📥 Downloading result...")

    remote_path = f"/workspace/ComfyUI/output/{filename}"

    cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-P", str(RUNPOD_PORT),
        "-i", RUNPOD_SSH_KEY,
        f"root@{RUNPOD_HOST}:{remote_path}",
        local_output
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Download failed: {result.stderr}")

    print(f"   ✓ Downloaded to {local_output}")
    return local_output

def main():
    print(f"\n{'='*60}")
    print(f"🎥 VIDEO-TO-VIDEO PROCESSING VIA API")
    print(f"{'='*60}")
    print(f"Video: {LOCAL_VIDEO}")
    print(f"LoRa: {LORA_MODEL}")
    print(f"Prompt: {PROMPT}")
    print(f"{'='*60}\n")

    try:
        # Step 1: Upload video
        video_filename = upload_video_to_runpod(LOCAL_VIDEO)

        # Step 2: Submit workflow
        prompt_id = run_via_ssh("/workspaces/ai/workflows/video_to_video_lora.json")

        if not prompt_id:
            print("Failed to submit workflow")
            return

        # Step 3: Monitor status
        output_filename = check_status(prompt_id)

        if not output_filename:
            print("No output video found")
            return

        # Step 4: Download result
        local_output = download_result(output_filename)

        print(f"\n{'='*60}")
        print(f"✅ COMPLETE!")
        print(f"{'='*60}")
        print(f"Output: {local_output}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
