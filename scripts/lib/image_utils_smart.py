"""Smart image processing with face-aware cropping"""

from PIL import Image
import cv2
import numpy as np
from pathlib import Path


def resize_image_smart(input_path, output_path, target_size=1024, face_priority=True):
    """
    Resize image to square with intelligent face-aware cropping

    Args:
        input_path: Path to input image
        output_path: Path to save resized image
        target_size: Target dimension (default 1024x1024)
        face_priority: If True, crop around detected face (default True)

    Returns:
        (width, height) of resized image
    """
    img = Image.open(input_path)

    # Convert RGBA to RGB if needed
    if img.mode == 'RGBA':
        img = img.convert('RGB')

    width, height = img.size

    # If already square, just resize
    if width == height:
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        img.save(output_path, 'JPEG', quality=95)
        return img.size

    # Determine crop box
    if face_priority:
        crop_box = get_face_aware_crop_box(input_path, width, height)
    else:
        crop_box = get_center_crop_box(width, height)

    # Crop to square
    img = img.crop(crop_box)

    # Resize to target
    img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)

    # Save
    img.save(output_path, 'JPEG', quality=95)

    return img.size


def get_face_aware_crop_box(image_path, width, height):
    """
    Calculate crop box that keeps face in frame

    Returns: (left, top, right, bottom)
    """
    # Load image for face detection
    img_cv = cv2.imread(str(image_path))
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Try to detect face
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    if len(faces) > 0:
        # Use the largest detected face
        face = max(faces, key=lambda f: f[2] * f[3])  # Sort by area
        fx, fy, fw, fh = face

        # Calculate face center
        face_center_x = fx + fw // 2
        face_center_y = fy + fh // 2

        # Determine crop size (make it square)
        crop_size = min(width, height)

        # Calculate crop box centered on face
        if width > height:
            # Landscape: crop width, keep height
            left = max(0, face_center_x - crop_size // 2)
            left = min(left, width - crop_size)  # Don't go past edge
            return (left, 0, left + crop_size, height)
        else:
            # Portrait: crop height, keep width
            top = max(0, face_center_y - crop_size // 2)
            top = min(top, height - crop_size)  # Don't go past edge
            return (0, top, width, top + crop_size)
    else:
        # No face detected, fall back to center crop
        print(f"  ⚠ No face detected in {Path(image_path).name}, using center crop")
        return get_center_crop_box(width, height)


def get_center_crop_box(width, height):
    """
    Calculate center crop box

    Returns: (left, top, right, bottom)
    """
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    return (left, top, left + min_dim, top + min_dim)


# Maintain compatibility with old function name
def resize_image(input_path, output_path, target_size=1024):
    """Backward compatible wrapper"""
    return resize_image_smart(input_path, output_path, target_size, face_priority=True)
