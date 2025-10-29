#!/usr/bin/env python3
"""Face swap using MaxStudio API"""

import os
import json
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('MAXSTUDIO_API_KEY')
BASE_URL = 'https://api.maxstudio.ai'

def detect_face(image_url):
    """Detect face in target image"""
    url = f"{BASE_URL}/detect-face-image"
    headers = {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json'
    }
    payload = {'imageUrl': image_url}

    for retry in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # API returns 'detectedFaces' not 'faces'
                faces = data.get('detectedFaces', data.get('faces', []))
                if faces and len(faces) > 0:
                    return faces[0]
            elif response.status_code == 429:
                print(f"    Rate limited, waiting 10s...")
                time.sleep(10)
            else:
                print(f"    API error {response.status_code}: {response.text[:200]}")
                if retry < 2:
                    time.sleep(5)
        except Exception as e:
            print(f"    Request error: {e}")
            if retry < 2:
                time.sleep(5)

    raise ValueError("No face detected after 3 retries")

def swap_face(source_url, target_url, original_face):
    """Initiate face swap job using swap-image API"""
    url = f"{BASE_URL}/swap-image"
    headers = {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json'
    }
    payload = {
        'mediaUrl': target_url,
        'faces': [
            {
                'newFace': source_url,
                'originalFace': original_face
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    return data.get('jobId')

def check_job_status(job_id):
    """Check face swap job status"""
    url = f"{BASE_URL}/swap-image/{job_id}"
    headers = {'x-api-key': API_KEY}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def download_image(url, filepath):
    """Download image from URL"""
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    with open(filepath, 'wb') as f:
        f.write(response.content)

def main():
    # Load URLs from previous step
    with open('urls.json', 'r') as f:
        urls = json.load(f)

    source_url = urls['source']
    results = []

    print(f"Source: {source_url[:80]}...\n")

    for target_info in urls['targets']:
        target_id = target_info['id']
        target_url = target_info['url']

        print(f"[{target_id}/5] Processing target {target_id:03d}...")

        # Step 1: Detect face in target
        print(f"  • Detecting face...")
        try:
            detected_face = detect_face(target_url)
            print(f"  ✓ Face detected: x={detected_face['x']}, y={detected_face['y']}, w={detected_face['width']}, h={detected_face['height']}")
        except Exception as e:
            print(f"  ✗ Face detection failed: {e}")
            continue

        # Step 2: Initiate face swap
        print(f"  • Starting face swap...")
        try:
            job_id = swap_face(source_url, target_url, detected_face)
            print(f"  ✓ Job created: {job_id}")
        except Exception as e:
            print(f"  ✗ Face swap failed: {e}")
            continue

        # Step 3: Poll for completion
        print(f"  • Polling for completion...")
        max_attempts = 60
        attempt = 0

        while attempt < max_attempts:
            try:
                status_data = check_job_status(job_id)
                status = status_data.get('status')

                if status == 'completed':
                    result_url = status_data.get('result', {}).get('mediaUrl')
                    print(f"  ✓ Completed! URL: {result_url}")

                    # Download result
                    output_file = f'swapped/andie_nsfw_{target_id:03d}.jpg'
                    download_image(result_url, output_file)
                    print(f"  ✓ Saved to {output_file}")

                    results.append({
                        'id': target_id,
                        'job_id': job_id,
                        'result_url': result_url,
                        'local_path': output_file
                    })
                    break

                elif status == 'failed':
                    print(f"  ✗ Job failed: {status_data.get('error', 'Unknown error')}")
                    break

                else:
                    print(f"  ⏳ Status: {status} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(5)
                    attempt += 1

            except Exception as e:
                print(f"  ✗ Error checking status: {e}")
                break

        if attempt >= max_attempts:
            print(f"  ✗ Timeout waiting for job {job_id}")

        print()

    # Save results
    with open('swap_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"✓ Face swap complete: {len(results)}/5 successful")
    print(f"✓ Results saved to swap_results.json")

if __name__ == "__main__":
    main()
