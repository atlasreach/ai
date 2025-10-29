"""File naming and organization utilities"""

import os
import json
from pathlib import Path
from datetime import datetime


def get_smart_filename(model_name, source_id, target_id, content_type, stage):
    """
    Generate smart filename: {model}-s{n}-t{n}-{type}-{stage}.jpg

    Args:
        model_name: Model name (e.g., 'andie')
        source_id: Source image number (1-indexed)
        target_id: Target image number (1-indexed)
        content_type: 'nsfw' or 'sfw'
        stage: 'original', 'swapped', or 'enhanced'

    Returns:
        filename string like 'andie-s1-t3-nsfw-swapped.jpg'
    """
    return f"{model_name}-s{source_id}-t{target_id}-{content_type}-{stage}.jpg"


def get_model_path(model_name):
    """Get base path for model: models/{model_name}/"""
    return Path('models') / model_name


def get_source_path(model_name):
    """Get source images path: models/{model_name}/source/"""
    return get_model_path(model_name) / 'source'


def get_targets_path(model_name, content_type):
    """Get targets path: models/{model_name}/targets/{type}/"""
    return get_model_path(model_name) / 'targets' / content_type


def get_results_path(model_name, content_type, source_id, stage):
    """
    Get results path: models/{model_name}/results/{type}/source_{n}/{stage}/

    Args:
        model_name: Model name
        content_type: 'nsfw' or 'sfw'
        source_id: Source image number (1-indexed)
        stage: 'swapped' or 'enhanced'

    Returns:
        Path object
    """
    return (get_model_path(model_name) / 'results' / content_type /
            f'source_{source_id}' / stage)


def ensure_directories(model_name):
    """Create all necessary directories for a model"""
    base = get_model_path(model_name)

    # Create base structure
    (base / 'source').mkdir(parents=True, exist_ok=True)
    (base / 'targets' / 'nsfw').mkdir(parents=True, exist_ok=True)
    (base / 'targets' / 'sfw').mkdir(parents=True, exist_ok=True)

    # Results directories created on-demand during processing
    return base


def list_source_images(model_name):
    """
    List all source images for a model

    Returns:
        list of tuples: [(source_id, filename, filepath), ...]
    """
    source_dir = get_source_path(model_name)
    if not source_dir.exists():
        return []

    # Get all image files (jpg, jpeg, png)
    all_files = []
    all_files.extend(source_dir.glob('*.jpg'))
    all_files.extend(source_dir.glob('*.jpeg'))
    all_files.extend(source_dir.glob('*.png'))
    all_files.extend(source_dir.glob('*.JPG'))
    all_files.extend(source_dir.glob('*.JPEG'))
    all_files.extend(source_dir.glob('*.PNG'))

    sources = []
    for i, filepath in enumerate(sorted(all_files), start=1):
        sources.append((i, filepath.name, str(filepath)))

    return sources


def list_target_images(model_name, content_type):
    """
    List all target images for a model

    Returns:
        list of tuples: [(target_id, filename, filepath), ...]
    """
    targets_dir = get_targets_path(model_name, content_type)
    if not targets_dir.exists():
        return []

    # Get all image files (jpg, jpeg, png)
    all_files = []
    all_files.extend(targets_dir.glob('*.jpg'))
    all_files.extend(targets_dir.glob('*.jpeg'))
    all_files.extend(targets_dir.glob('*.png'))
    all_files.extend(targets_dir.glob('*.JPG'))
    all_files.extend(targets_dir.glob('*.JPEG'))
    all_files.extend(targets_dir.glob('*.PNG'))

    targets = []
    for i, filepath in enumerate(sorted(all_files), start=1):
        targets.append((i, filepath.name, str(filepath)))

    return targets


def load_config(model_name):
    """Load model config.json"""
    config_path = get_model_path(model_name) / 'config.json'

    if not config_path.exists():
        return None

    with open(config_path, 'r') as f:
        return json.load(f)


def save_config(model_name, config):
    """Save model config.json"""
    config_path = get_model_path(model_name) / 'config.json'

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def create_default_config(model_name, bucket_name):
    """Create default config for new model"""
    return {
        'model_name': model_name,
        'created_at': datetime.now().isoformat(),
        'bucket_name': bucket_name,
        'settings': {
            'enhancement_level': 2,
            'auto_upload_s3': True,
            'keep_intermediate': True
        },
        'sources': [],
        'processing_history': {
            'nsfw': {'targets_processed': 0},
            'sfw': {'targets_processed': 0}
        }
    }


def update_processing_history(model_name, content_type, count):
    """Update processing history in config"""
    config = load_config(model_name)
    if not config:
        return

    config['processing_history'][content_type]['targets_processed'] = count
    config['processing_history'][content_type]['last_run'] = datetime.now().isoformat()

    save_config(model_name, config)


def list_all_models():
    """
    List all available models

    Returns:
        list of model names
    """
    models_dir = Path('models')
    if not models_dir.exists():
        return []

    return [d.name for d in models_dir.iterdir() if d.is_dir()]


def model_exists(model_name):
    """
    Check if a model exists by looking for directory with images

    Args:
        model_name: Model name to check

    Returns:
        bool: True if model directory exists with images
    """
    model_path = Path('models') / model_name

    if not model_path.exists():
        return False

    # Check for images in source or targets
    source_images = list((model_path / 'source').glob('*.jpg')) if (model_path / 'source').exists() else []
    source_images += list((model_path / 'source').glob('*.jpeg')) if (model_path / 'source').exists() else []
    source_images += list((model_path / 'source').glob('*.png')) if (model_path / 'source').exists() else []

    nsfw_targets = list((model_path / 'targets' / 'nsfw').glob('*.jpg')) if (model_path / 'targets' / 'nsfw').exists() else []
    nsfw_targets += list((model_path / 'targets' / 'nsfw').glob('*.jpeg')) if (model_path / 'targets' / 'nsfw').exists() else []

    sfw_targets = list((model_path / 'targets' / 'sfw').glob('*.jpg')) if (model_path / 'targets' / 'sfw').exists() else []
    sfw_targets += list((model_path / 'targets' / 'sfw').glob('*.jpeg')) if (model_path / 'targets' / 'sfw').exists() else []

    # Model exists if it has any images
    return len(source_images) > 0 or len(nsfw_targets) > 0 or len(sfw_targets) > 0


def get_model_status(model_name):
    """
    Get detailed status of a model

    Returns:
        dict with model info or None if doesn't exist
    """
    if not model_exists(model_name):
        return None

    model_path = Path('models') / model_name
    config = load_config(model_name)

    # Count images
    sources = list_source_images(model_name)
    nsfw_targets = list_target_images(model_name, 'nsfw')
    sfw_targets = list_target_images(model_name, 'sfw')

    # Count processed results
    nsfw_results = list((model_path / 'results' / 'nsfw').glob('**/enhanced/*.jpg')) if (model_path / 'results' / 'nsfw').exists() else []
    sfw_results = list((model_path / 'results' / 'sfw').glob('**/enhanced/*.jpg')) if (model_path / 'results' / 'sfw').exists() else []

    return {
        'name': model_name,
        'has_config': config is not None,
        'bucket': config.get('bucket_name') if config else None,
        'source_count': len(sources),
        'nsfw_target_count': len(nsfw_targets),
        'sfw_target_count': len(sfw_targets),
        'nsfw_results_count': len(nsfw_results),
        'sfw_results_count': len(sfw_results)
    }


def list_uninitialized_models():
    """
    List models that have images but no config.json
    (i.e., pending initialization)

    Returns:
        list of model names
    """
    models_dir = Path('models')
    if not models_dir.exists():
        return []

    uninitialized = []
    for model_dir in models_dir.iterdir():
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name

        # Has images but no config = uninitialized
        if model_exists(model_name) and not load_config(model_name):
            uninitialized.append(model_name)

    return sorted(uninitialized)
