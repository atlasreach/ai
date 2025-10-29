"""Local face detection using OpenCV"""

import cv2
import numpy as np
from pathlib import Path


class FaceDetector:
    """OpenCV-based face detector for validation"""

    def __init__(self):
        # Use Haar Cascade classifier
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect(self, image_path):
        """
        Detect faces in image

        Args:
            image_path: Path to image file

        Returns:
            list of dicts with face coordinates: [{'x': int, 'y': int, 'width': int, 'height': int}, ...]

        Raises:
            ValueError if no faces detected
        """
        # Read image
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        if len(faces) == 0:
            raise ValueError(f"No faces detected in {image_path}")

        # Convert to dict format
        result = []
        for (x, y, w, h) in faces:
            result.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h)
            })

        return result

    def validate_image(self, image_path):
        """
        Validate that image contains at least one face

        Returns:
            (success: bool, message: str)
        """
        try:
            faces = self.detect(image_path)
            return (True, f"✓ {len(faces)} face(s) detected")
        except Exception as e:
            return (False, f"✗ {str(e)}")

    def batch_validate(self, image_paths):
        """
        Validate multiple images

        Returns:
            dict: {filepath: (success, message), ...}
        """
        results = {}
        for path in image_paths:
            results[path] = self.validate_image(path)
        return results
