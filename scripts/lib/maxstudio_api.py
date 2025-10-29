"""MaxStudio API wrapper for face swap and enhancement"""

import os
import time
import base64
import requests


class MaxStudioAPI:
    """Wrapper for MaxStudio API operations"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('MAXSTUDIO_API_KEY')
        self.base_url = 'https://api.maxstudio.ai'

        if not self.api_key:
            raise ValueError("MAXSTUDIO_API_KEY not set")

    def _get_headers(self):
        """Get common request headers"""
        return {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }

    def detect_face(self, image_url, retries=3):
        """
        Detect face in image

        Args:
            image_url: Public URL or presigned URL to image
            retries: Number of retry attempts

        Returns:
            dict with face coordinates (x, y, width, height)

        Raises:
            ValueError if no face detected after retries
        """
        url = f"{self.base_url}/detect-face-image"
        payload = {'imageUrl': image_url}

        for attempt in range(retries):
            try:
                response = requests.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    faces = data.get('detectedFaces', data.get('faces', []))
                    if faces and len(faces) > 0:
                        return faces[0]

                elif response.status_code == 429:
                    time.sleep(10)
                    continue

                else:
                    if attempt < retries - 1:
                        time.sleep(5)
                        continue

            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                raise

        raise ValueError("No face detected after retries")

    def swap_face(self, source_url, target_url, original_face):
        """
        Initiate face swap job

        Args:
            source_url: URL of source face image
            target_url: URL of target body image
            original_face: Face coordinates dict from detect_face()

        Returns:
            job_id string
        """
        url = f"{self.base_url}/swap-image"
        payload = {
            'mediaUrl': target_url,
            'faces': [{
                'newFace': source_url,
                'originalFace': original_face
            }]
        }

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        return data.get('jobId')

    def check_swap_status(self, job_id):
        """Check face swap job status"""
        url = f"{self.base_url}/swap-image/{job_id}"
        headers = {'x-api-key': self.api_key}

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        return response.json()

    def wait_for_swap(self, job_id, max_attempts=60, poll_interval=5):
        """
        Wait for face swap job to complete

        Args:
            job_id: Job ID from swap_face()
            max_attempts: Maximum polling attempts
            poll_interval: Seconds between polls

        Returns:
            result_url string if successful

        Raises:
            RuntimeError if job fails or times out
        """
        for attempt in range(max_attempts):
            status_data = self.check_swap_status(job_id)
            status = status_data.get('status')

            if status == 'completed':
                return status_data.get('result', {}).get('mediaUrl')

            elif status == 'failed':
                error = status_data.get('error', 'Unknown error')
                raise RuntimeError(f"Face swap failed: {error}")

            time.sleep(poll_interval)

        raise RuntimeError(f"Face swap timed out after {max_attempts * poll_interval}s")

    def enhance_image(self, image_base64, upscale=2):
        """
        Initiate image enhancement job

        Args:
            image_base64: Base64 encoded image (without data URI prefix)
            upscale: Upscale factor (2 or 4)

        Returns:
            job_id string
        """
        url = f"{self.base_url}/image-enhancer"
        headers = {'x-api-key': self.api_key}
        payload = {
            'image': image_base64,
            'upscale': upscale
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get('jobId')

    def check_enhance_status(self, job_id):
        """Check enhancement job status"""
        url = f"{self.base_url}/image-enhancer/{job_id}"
        headers = {'x-api-key': self.api_key}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def wait_for_enhance(self, job_id, max_attempts=60, poll_interval=5):
        """
        Wait for enhancement job to complete

        Args:
            job_id: Job ID from enhance_image()
            max_attempts: Maximum polling attempts
            poll_interval: Seconds between polls

        Returns:
            base64 encoded result image

        Raises:
            RuntimeError if job fails or times out
        """
        for attempt in range(max_attempts):
            status_data = self.check_enhance_status(job_id)
            status = status_data.get('status')

            if status == 'completed':
                return status_data.get('result')

            elif status == 'failed':
                error = status_data.get('error', 'Unknown error')
                raise RuntimeError(f"Enhancement failed: {error}")

            time.sleep(poll_interval)

        raise RuntimeError(f"Enhancement timed out after {max_attempts * poll_interval}s")


def image_to_base64(filepath):
    """Convert image file to base64 (no data URI prefix)"""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def base64_to_image(b64_string, filepath):
    """Convert base64 to image file"""
    # Remove data URI prefix if present
    if ',' in b64_string:
        b64_string = b64_string.split(',', 1)[1]

    img_data = base64.b64decode(b64_string)
    with open(filepath, 'wb') as f:
        f.write(img_data)


def download_image(url, filepath):
    """Download image from URL"""
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    with open(filepath, 'wb') as f:
        f.write(response.content)
