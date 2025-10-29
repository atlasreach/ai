"""Image processing utilities"""

from PIL import Image
from pathlib import Path


def resize_image(input_path, output_path, target_size=1024):
    """
    Resize image to square dimensions for LoRA training

    Args:
        input_path: Path to input image
        output_path: Path to save resized image
        target_size: Target dimension (default 1024x1024)

    Returns:
        (width, height) of resized image
    """
    img = Image.open(input_path)

    # Convert RGBA to RGB if needed
    if img.mode == 'RGBA':
        img = img.convert('RGB')

    # Resize to square, maintaining aspect ratio with center crop
    width, height = img.size

    if width != height:
        # Crop to square first (center crop)
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim
        img = img.crop((left, top, right, bottom))

    # Resize to target
    if img.size != (target_size, target_size):
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)

    # Save
    img.save(output_path, 'JPEG', quality=95)

    return img.size
