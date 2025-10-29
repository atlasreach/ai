#!/usr/bin/env python3
"""
MaxStudio Workflow Master CLI
Interactive menu system for managing multiple AI models
"""

import os
import sys
import shutil
from pathlib import Path
from glob import glob
from dotenv import load_dotenv

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from lib import (
    S3Manager,
    MaxStudioAPI,
    FaceDetector,
    ProgressTracker,
    image_to_base64,
    base64_to_image,
    download_image,
    ensure_directories,
    list_source_images,
    list_target_images,
    load_config,
    save_config,
    create_default_config,
    list_all_models,
    list_uninitialized_models,
    get_smart_filename,
    get_source_path,
    get_targets_path,
    get_results_path,
    update_processing_history,
    get_model_status
)
from lib.image_utils_smart import resize_image
from lib.caption_generator import CaptionGenerator

# Load environment variables
load_dotenv()


def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header(title):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_menu(options):
    """Print menu options"""
    for key, label in options.items():
        print(f"  [{key}] {label}")
    print()


def get_input(prompt, valid_options=None, allow_back=True):
    """Get validated user input"""
    while True:
        if allow_back:
            choice = input(f"{prompt} (0=back): ").strip()
        else:
            choice = input(f"{prompt}: ").strip()

        # Always allow 0 to go back
        if choice == '0' and allow_back:
            return '0'

        if valid_options is None or choice in valid_options:
            return choice
        print(f"Invalid choice. Please choose from: {', '.join(valid_options)}")


def main_menu():
    """Display main menu"""
    clear_screen()
    print_header("MaxStudio Workflow - Main Menu")
    print_menu({
        '1': 'Create New Model',
        '2': 'Work with Existing Model',
        '3': 'View All Models',
        '4': 'Exit'
    })
    return get_input("Choose option", ['1', '2', '3', '4'], allow_back=False)


def create_new_model():
    """Create new model workflow - initialize models with images"""
    clear_screen()
    print_header("Create New Model")

    # Check for uninitialized models (have images but no config)
    uninitialized = list_uninitialized_models()

    if uninitialized:
        print("📂 Found models with images (not yet initialized):\n")
        for i, model in enumerate(uninitialized, 1):
            status = get_model_status(model)
            print(f"  [{i}] {model}")
            print(f"      • Sources: {status['source_count']}")
            print(f"      • NSFW targets: {status['nsfw_target_count']}")
            print(f"      • SFW targets: {status['sfw_target_count']}")
            print()

        print(f"  [{len(uninitialized) + 1}] Create brand new model (enter name manually)")
        print()

        valid_choices = [str(i) for i in range(1, len(uninitialized) + 2)]
        choice = get_input(f"Choose option", valid_choices)

        if choice == '0':
            return

        choice_idx = int(choice) - 1

        if choice_idx < len(uninitialized):
            # Initialize existing model
            model_name = uninitialized[choice_idx]
        else:
            # Manual entry
            model_name = input("\nEnter model name (lowercase, no spaces): ").strip().lower()
            if not model_name or ' ' in model_name:
                print("✗ Invalid model name")
                input("\nPress Enter to continue...")
                return

            # Check if already exists
            all_models = list_all_models()
            if model_name in all_models:
                config = load_config(model_name)
                if config:
                    print(f"✗ Model '{model_name}' already initialized")
                    input("\nPress Enter to continue...")
                    return

            # Create directories for new model
            print(f"\nCreating directories for '{model_name}'...")
            ensure_directories(model_name)
            print("✓ Directories created")
            print(f"\n📁 Next: Drop images into:")
            print(f"   • models/{model_name}/source/")
            print(f"   • models/{model_name}/targets/nsfw/")
            print(f"   • models/{model_name}/targets/sfw/")
            print(f"\nThen run this command again to initialize!")
            input("\nPress Enter to continue...")
            return
    else:
        # No uninitialized models, manual entry
        model_name = input("Enter model name (lowercase, no spaces): ").strip().lower()
        if not model_name or ' ' in model_name:
            print("✗ Invalid model name")
            input("\nPress Enter to continue...")
            return

        # Check if already exists
        all_models = list_all_models()
        if model_name in all_models:
            config = load_config(model_name)
            if config:
                print(f"✗ Model '{model_name}' already initialized")
                input("\nPress Enter to continue...")
                return

        # Create directories for new model
        print(f"\nCreating directories for '{model_name}'...")
        ensure_directories(model_name)
        print("✓ Directories created")
        print(f"\n📁 Next: Drop images into:")
        print(f"   • models/{model_name}/source/")
        print(f"   • models/{model_name}/targets/nsfw/")
        print(f"   • models/{model_name}/targets/sfw/")
        print(f"\nThen run this command again to initialize!")
        input("\nPress Enter to continue...")
        return

    # Initialize the selected model
    print(f"\n{'=' * 60}")
    print(f"  Initializing '{model_name}'")
    print(f"{'=' * 60}\n")

    # Validate source images
    detector = FaceDetector()
    sources = list_source_images(model_name)

    if not sources:
        print("✗ No source images found")
        input("\nPress Enter to continue...")
        return

    print(f"Validating {len(sources)} source image(s)...")
    valid_sources = []
    for source_id, filename, filepath in sources:
        success, message = detector.validate_image(filepath)
        print(f"  {message}: {filename}")
        if success:
            valid_sources.append((source_id, filename, filepath))

    if not valid_sources:
        print("\n✗ No valid source images with faces detected")
        input("\nPress Enter to continue...")
        return

    print(f"✓ {len(valid_sources)} valid source image(s)")

    # Rename sources to smart format
    print("\n--- Renaming Source Files ---")
    source_dir = get_source_path(model_name)
    renamed_sources = []

    for source_id, filename, filepath in valid_sources:
        old_path = Path(filepath)
        new_filename = f"{model_name}-s{source_id}-original.jpg"
        new_path = source_dir / new_filename

        if old_path != new_path:
            shutil.move(str(old_path), str(new_path))
            print(f"  ✓ {filename} → {new_filename}")
            renamed_sources.append((source_id, new_filename, str(new_path)))
        else:
            renamed_sources.append((source_id, filename, filepath))

    valid_sources = renamed_sources

    # Duplicate and rename targets for each source combination
    print("\n--- Creating Target Combinations ---")

    # Get list of content types with targets
    content_types = []
    nsfw_targets_dir = get_targets_path(model_name, 'nsfw')
    sfw_targets_dir = get_targets_path(model_name, 'sfw')

    if nsfw_targets_dir.exists() and list(nsfw_targets_dir.glob('*.[jp][pn]g')) + list(nsfw_targets_dir.glob('*.jpeg')):
        content_types.append('nsfw')
    if sfw_targets_dir.exists() and list(sfw_targets_dir.glob('*.[jp][pn]g')) + list(sfw_targets_dir.glob('*.jpeg')):
        content_types.append('sfw')

    for content_type in content_types:
        print(f"\nProcessing {content_type.upper()} targets...")
        targets_dir = get_targets_path(model_name, content_type)

        # Get original target files
        original_targets = sorted([
            f for f in targets_dir.iterdir()
            if f.suffix.lower() in ['.jpg', '.jpeg', '.png']
        ])

        if not original_targets:
            continue

        print(f"  Found {len(original_targets)} target files")
        print(f"  Creating {len(valid_sources)} × {len(original_targets)} = {len(valid_sources) * len(original_targets)} combinations...")

        # Create combinations
        new_target_files = []
        for source_id, _, _ in valid_sources:
            for target_idx, target_file in enumerate(original_targets, 1):
                new_filename = f"{model_name}-s{source_id}-t{target_idx}-{content_type}-original.jpg"
                new_path = targets_dir / new_filename

                # Copy original to new combination name
                shutil.copy2(str(target_file), str(new_path))
                new_target_files.append(new_path)

        # Delete original generic target files
        for original_file in original_targets:
            original_file.unlink()

        print(f"  ✓ Created {len(new_target_files)} target combinations")
        print(f"  ✓ Removed {len(original_targets)} original files")

    # Create S3 bucket (always create for new models)
    print("\n--- Creating S3 Bucket ---")
    try:
        s3 = S3Manager()
        bucket_name = s3.create_bucket(model_name)
        print(f"✓ Bucket created: {bucket_name}")

        # Update .env
        with open('.env', 'r') as f:
            lines = f.readlines()
        with open('.env', 'w') as f:
            updated = False
            for line in lines:
                if line.startswith('AWS_S3_BUCKET='):
                    f.write(f'AWS_S3_BUCKET={bucket_name}\n')
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f'\nAWS_S3_BUCKET={bucket_name}\n')

    except Exception as e:
        print(f"✗ Failed to create bucket: {e}")
        bucket_name = input("Enter existing bucket name: ").strip()

    # Create config
    config = create_default_config(model_name, bucket_name)
    config['sources'] = [
        {'id': sid, 'filename': fname, 'original_name': fname}
        for sid, fname, _ in valid_sources
    ]
    save_config(model_name, config)

    print(f"\n✓ Model '{model_name}' initialized successfully!")
    print(f"✓ Config saved to: models/{model_name}/config.json")
    print(f"✓ S3 bucket: {bucket_name}")
    print(f"\n📋 Next: Use option [2] to process this model")

    input("\nPress Enter to continue...")


def work_with_model():
    """Work with existing model"""
    clear_screen()
    print_header("Work with Existing Model")

    # List models
    models = list_all_models()
    if not models:
        print("✗ No models found. Create one first!")
        input("\nPress Enter to continue...")
        return

    print("Available models:")
    for i, model in enumerate(models, 1):
        print(f"  [{i}] {model}")
    print()

    choice = get_input(f"Choose model (1-{len(models)})", [str(i) for i in range(1, len(models) + 1)])

    if choice == '0':
        return

    model_name = models[int(choice) - 1]

    # Load config - create if doesn't exist
    config = load_config(model_name)
    if not config:
        print(f"\n⚠ Config not found for '{model_name}', setting up...")

        # Create S3 bucket automatically
        print(f"Creating S3 bucket for '{model_name}'...")
        try:
            s3 = S3Manager()
            bucket_name = s3.create_bucket(model_name)
            print(f"✓ Bucket created: {bucket_name}")

            # Update .env with new bucket
            with open('.env', 'r') as f:
                lines = f.readlines()
            with open('.env', 'w') as f:
                updated = False
                for line in lines:
                    if line.startswith('AWS_S3_BUCKET='):
                        f.write(f'AWS_S3_BUCKET={bucket_name}\n')
                        updated = True
                    else:
                        f.write(line)
                if not updated:
                    f.write(f'\nAWS_S3_BUCKET={bucket_name}\n')

        except Exception as e:
            print(f"⚠ Could not create bucket: {e}")
            bucket_name = f"{model_name}-workflow-default"

        # Create config
        config = create_default_config(model_name, bucket_name)

        # Get existing sources
        sources = list_source_images(model_name)
        if sources:
            config['sources'] = [
                {'id': sid, 'filename': fname, 'original_name': fname}
                for sid, fname, _ in sources
            ]

        save_config(model_name, config)
        print(f"✓ Model '{model_name}' ready!\n")
        input("Press Enter to continue...")

    # Show model info
    clear_screen()
    print_header(f"Model: {model_name}")
    print(f"Created: {config.get('created_at', 'Unknown')}")
    print(f"Bucket: {config.get('bucket_name', 'None')}")
    print(f"Sources: {len(config.get('sources', []))}")

    # Count targets
    nsfw_targets = list_target_images(model_name, 'nsfw')
    sfw_targets = list_target_images(model_name, 'sfw')
    print(f"NSFW Targets: {len(nsfw_targets)}")
    print(f"SFW Targets: {len(sfw_targets)}")
    print()

    # Choose action
    while True:
        clear_screen()
        print_header(f"Model: {model_name}")
        print(f"Created: {config.get('created_at', 'Unknown')}")
        print(f"Bucket: {config.get('bucket_name', 'None')}")
        print(f"Sources: {len(config.get('sources', []))}")
        print(f"NSFW Targets: {len(nsfw_targets)}")
        print(f"SFW Targets: {len(sfw_targets)}")
        print()

        print_menu({
            '1': 'Process NSFW targets',
            '2': 'Process SFW targets',
            '3': 'Add more source images',
            '4': 'Add more target images',
            '5': 'Back to Main Menu'
        })

        choice = get_input("Choose option", ['1', '2', '3', '4', '5'])

        if choice == '0' or choice == '5':
            return
        elif choice == '1' or choice == '2':
            content_type = 'nsfw' if choice == '1' else 'sfw'
            process_model(model_name, content_type)
        elif choice == '3':
            add_sources(model_name)
            # Reload config after adding sources
            config = load_config(model_name)
        elif choice == '4':
            add_targets(model_name)
            # Reload targets after adding
            nsfw_targets = list_target_images(model_name, 'nsfw')
            sfw_targets = list_target_images(model_name, 'sfw')


def process_model(model_name, content_type):
    """Process face swap and enhancement for a model"""
    clear_screen()
    print_header(f"Processing: {model_name} ({content_type.upper()})")

    # Initialize components
    s3 = S3Manager()
    api = MaxStudioAPI()
    tracker = ProgressTracker(model_name)

    # Get sources and targets
    sources = list_source_images(model_name)
    targets = list_target_images(model_name, content_type)

    if not sources:
        print("✗ No source images found")
        input("\nPress Enter to continue...")
        return

    if not targets:
        print(f"✗ No {content_type.upper()} target images found")
        input("\nPress Enter to continue...")
        return

    # Create task pairs (all combinations of sources × targets)
    task_pairs = []
    for source_id, source_filename, source_filepath in sources:
        for target_id, target_filename, target_filepath in targets:
            task_pairs.append((source_id, target_id, source_filename, source_filepath, target_filename, target_filepath))

    print(f"Sources: {len(sources)}")
    print(f"Targets: {len(targets)}")
    print(f"Total combinations: {len(task_pairs)}")
    print()

    # Initialize progress tracking with actual task pairs only
    for source_id, target_id, _, _, _, _ in task_pairs:
        task_key = tracker.get_task_key(source_id, target_id, content_type)
        if task_key not in tracker.progress['tasks']:
            tracker.progress['tasks'][task_key] = {
                'source_id': source_id,
                'target_id': target_id,
                'content_type': content_type
            }
    tracker._save()

    # Show current progress
    stats = tracker.get_stats(content_type)
    print(f"Progress: Swap {stats['swap']}/{stats['total']} ({stats['swap_pct']}%), " +
          f"Enhance {stats['enhance']}/{stats['total']} ({stats['enhance_pct']}%), " +
          f"Caption {stats['caption']}/{stats['total']} ({stats['caption_pct']}%)")
    print()

    resume = get_input("Resume from previous run? (y/n)", ['y', 'n'])
    if resume == 'n':
        confirm = get_input("This will reset all progress. Continue? (y/n)", ['y', 'n'])
        if confirm == 'y':
            tracker.reset()
            tracker.initialize_tasks(source_ids, target_ids, content_type)
            print("✓ Progress reset")

    input("\nPress Enter to start processing...")

    # Step 1: Upload all images to S3
    print("\n--- STEP 1: Uploading to S3 ---")
    upload_urls = {}

    for source_id, filename, filepath in sources:
        s3_key = f'originals/sources/{filename}'
        print(f"Uploading source {source_id}: {filename}...")
        url = s3.upload_file(filepath, s3_key)
        upload_urls[f'source_{source_id}'] = url

    for target_id, filename, filepath in targets:
        s3_key = f'originals/targets/{content_type}/{filename}'
        print(f"Uploading target {target_id}: {filename}...")
        url = s3.upload_file(filepath, s3_key)
        upload_urls[f'target_{target_id}'] = url

    print(f"✓ Uploaded {len(sources) + len(targets)} images to S3")

    # Step 2: Face Swap
    print("\n--- STEP 2: Face Swapping ---")
    swap_count = 0

    for source_id, target_id, source_filename, source_filepath, target_filename, target_filepath in task_pairs:
        # Check if already completed
        if tracker.is_completed(source_id, target_id, content_type, 'swap'):
            print(f"[{swap_count + 1}/{len(task_pairs)}] Skipping s{source_id}-t{target_id} (already completed)")
            swap_count += 1
            continue

        print(f"\n[{swap_count + 1}/{len(task_pairs)}] Processing: source {source_id} → target {target_id}")
        source_url = upload_urls[f'source_{source_id}']
        target_url = upload_urls[f'target_{target_id}']

        try:
            # Detect face
            print("  • Detecting face...")
            face = api.detect_face(target_url)
            print(f"  ✓ Face detected at ({face['x']}, {face['y']})")

            # Start swap
            print("  • Starting face swap...")
            job_id = api.swap_face(source_url, target_url, face)
            print(f"  ✓ Job created: {job_id}")

            # Wait for completion
            print("  • Waiting for completion...")
            result_url = api.wait_for_swap(job_id)
            print(f"  ✓ Swap completed")

            # Download result
            smart_name = get_smart_filename(model_name, source_id, target_id, content_type, 'swapped')
            result_dir = get_results_path(model_name, content_type, source_id, 'swapped')
            result_dir.mkdir(parents=True, exist_ok=True)
            result_path = result_dir / smart_name

            download_image(result_url, str(result_path))
            print(f"  ✓ Saved: {result_path}")

            # Resize to 1024x1024 for consistent LoRA training
            print("  • Resizing to 1024x1024...")
            resize_image(str(result_path), str(result_path), target_size=1024)
            print(f"  ✓ Resized for training")

            # Upload swapped image to S3
            s3_key = f'results/{content_type}/source_{source_id}/swapped/{smart_name}'
            swapped_s3_url = s3.upload_file(str(result_path), s3_key)
            print(f"  ✓ Uploaded to S3")

            # Mark completed
            tracker.mark_completed(source_id, target_id, content_type, 'swap', {
                'job_id': job_id,
                'result_url': result_url,
                'local_path': str(result_path),
                's3_url': swapped_s3_url
            })

            swap_count += 1

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            continue

    print(f"\n✓ Face swap complete: {swap_count}/{len(task_pairs)} successful")

    # Step 3: Enhancement
    print("\n--- STEP 3: Enhancement ---")
    enhance_count = 0

    for source_id, target_id, source_filename, source_filepath, target_filename, target_filepath in task_pairs:
        # Check if swap completed and enhance not done
        if not tracker.is_completed(source_id, target_id, content_type, 'swap'):
            continue

        if tracker.is_completed(source_id, target_id, content_type, 'enhance'):
            print(f"[{enhance_count + 1}] Skipping s{source_id}-t{target_id} (already enhanced)")
            enhance_count += 1
            continue

        print(f"\n[{enhance_count + 1}] Enhancing: source {source_id} → target {target_id}")

        try:
            # Get swapped image path
            smart_name = get_smart_filename(model_name, source_id, target_id, content_type, 'swapped')
            swapped_path = get_results_path(model_name, content_type, source_id, 'swapped') / smart_name

            if not swapped_path.exists():
                print(f"  ✗ Swapped image not found: {swapped_path}")
                continue

            # Convert to base64
            print("  • Converting to base64...")
            img_b64 = image_to_base64(str(swapped_path))

            # Start enhancement
            print("  • Starting enhancement...")
            job_id = api.enhance_image(img_b64, upscale=2)
            print(f"  ✓ Job created: {job_id}")

            # Wait for completion
            print("  • Waiting for completion...")
            result_b64 = api.wait_for_enhance(job_id)
            print(f"  ✓ Enhancement completed")

            # Save result
            enhanced_name = get_smart_filename(model_name, source_id, target_id, content_type, 'enhanced')
            enhanced_dir = get_results_path(model_name, content_type, source_id, 'enhanced')
            enhanced_dir.mkdir(parents=True, exist_ok=True)
            enhanced_path = enhanced_dir / enhanced_name

            base64_to_image(result_b64, str(enhanced_path))
            print(f"  ✓ Saved: {enhanced_path}")

            # Upload to S3
            s3_key = f'results/{content_type}/source_{source_id}/enhanced/{enhanced_name}'
            s3_url = s3.upload_file(str(enhanced_path), s3_key)
            print(f"  ✓ Uploaded to S3")

            # Mark completed
            tracker.mark_completed(source_id, target_id, content_type, 'enhance', {
                'job_id': job_id,
                'local_path': str(enhanced_path),
                's3_url': s3_url
            })

            enhance_count += 1

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            continue

    print(f"\n✓ Enhancement complete: {enhance_count} successful")

    # Step 4: Caption Generation
    print("\n--- STEP 4: Generating Captions with Grok Vision ---")

    # Check for Grok API key
    grok_api_key = os.getenv('GROK_API_KEY')
    if not grok_api_key:
        print("⚠ GROK_API_KEY not found in .env - Skipping caption generation")
        print("  Add GROK_API_KEY to .env to enable captions")
    else:
        caption_count = 0
        generator = CaptionGenerator(grok_api_key)

        for source_id, target_id, source_filename, source_filepath, target_filename, target_filepath in task_pairs:
            # Check if enhanced exists and caption not done
            if not tracker.is_completed(source_id, target_id, content_type, 'enhance'):
                continue

            if tracker.is_completed(source_id, target_id, content_type, 'caption'):
                print(f"[{caption_count + 1}] Skipping s{source_id}-t{target_id} (caption already exists)")
                caption_count += 1
                continue

            print(f"\n[{caption_count + 1}] Generating caption: source {source_id} → target {target_id}")

            try:
                # Get enhanced image path
                enhanced_name = get_smart_filename(model_name, source_id, target_id, content_type, 'enhanced')
                enhanced_path = get_results_path(model_name, content_type, source_id, 'enhanced') / enhanced_name

                if not enhanced_path.exists():
                    print(f"  ✗ Enhanced image not found: {enhanced_path}")
                    continue

                # Generate caption
                print("  • Analyzing image with Grok Vision...")
                caption = generator.generate_caption(str(enhanced_path), model_name)

                if not caption:
                    print(f"  ✗ Failed to generate caption")
                    continue

                print(f"  ✓ Caption generated ({len(caption)} chars)")

                # Save caption locally and to S3
                print("  • Saving caption...")
                caption_s3_url = generator.save_caption(str(enhanced_path), caption, s3)

                txt_path = enhanced_path.with_suffix('.txt')
                print(f"  ✓ Saved: {txt_path}")
                if caption_s3_url:
                    print(f"  ✓ Uploaded to S3: {caption_s3_url}")
                else:
                    print(f"  ⚠ S3 upload failed (check logs above)")

                # Mark completed
                tracker.mark_completed(source_id, target_id, content_type, 'caption', {
                    'caption_preview': caption[:100] + '...' if len(caption) > 100 else caption,
                    'local_path': str(txt_path),
                    's3_url': caption_s3_url,
                    'caption_length': len(caption)
                })

                caption_count += 1

            except Exception as e:
                print(f"  ✗ Failed: {e}")
                continue

        print(f"\n✓ Caption generation complete: {caption_count} successful")

    # Update config
    update_processing_history(model_name, content_type, len(task_pairs))

    print("\n" + "=" * 60)
    print("  Processing Complete!")
    print("=" * 60)
    input("\nPress Enter to continue...")


def view_progress(model_name):
    """View model progress"""
    clear_screen()
    print_header(f"Progress: {model_name}")

    tracker = ProgressTracker(model_name)

    # Overall stats
    nsfw_stats = tracker.get_stats('nsfw')
    sfw_stats = tracker.get_stats('sfw')

    print("NSFW:")
    print(f"  Swap: {nsfw_stats['swap']}/{nsfw_stats['total']} ({nsfw_stats['swap_pct']}%)")
    print(f"  Enhance: {nsfw_stats['enhance']}/{nsfw_stats['total']} ({nsfw_stats['enhance_pct']}%)")
    print(f"  Caption: {nsfw_stats['caption']}/{nsfw_stats['total']} ({nsfw_stats['caption_pct']}%)")
    print()

    print("SFW:")
    print(f"  Swap: {sfw_stats['swap']}/{sfw_stats['total']} ({sfw_stats['swap_pct']}%)")
    print(f"  Enhance: {sfw_stats['enhance']}/{sfw_stats['total']} ({sfw_stats['enhance_pct']}%)")
    print(f"  Caption: {sfw_stats['caption']}/{sfw_stats['total']} ({sfw_stats['caption_pct']}%)")

    input("\nPress Enter to continue...")


def add_sources(model_name):
    """Add more source images to existing model"""
    clear_screen()
    print_header(f"Add Sources: {model_name}")

    source_dir = get_source_path(model_name)
    source_dir.mkdir(parents=True, exist_ok=True)

    # Upload files with improved UX
    print("\nSource Face Upload")
    print("=" * 60)
    print("\nHow to upload:")
    print("  1. DRAG & DROP files from your file explorer into this terminal")
    print("  2. Or type/paste file paths")
    print("  3. Use wildcards: ~/Photos/*.jpg")
    print("  4. Press Enter on empty line when done")
    print()

    uploaded_count = 0

    while True:
        file_input = input(f"Drop files or path (Enter to finish): ").strip()

        if not file_input:
            break

        # Remove quotes that terminals add when dragging
        file_input = file_input.strip("'\"")

        # Expand user path and wildcards
        file_input = os.path.expanduser(file_input)

        # Check if it's a glob pattern
        if '*' in file_input or '?' in file_input:
            matches = glob(file_input)
            if not matches:
                print(f"  ✗ No files match pattern: {file_input}")
                continue
            print(f"  Found {len(matches)} files from pattern")
            file_paths = matches
        else:
            file_paths = [file_input]

        # Process each file
        for file_path in file_paths:
            source_path = Path(file_path)

            if not source_path.exists():
                print(f"  ✗ Not found: {source_path.name}")
                continue

            if not source_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                print(f"  ✗ Skipping (not jpg/png): {source_path.name}")
                continue

            # Find next available number and use smart naming
            existing = list(source_dir.glob('*.jpg')) + list(source_dir.glob('*.jpeg')) + list(source_dir.glob('*.png'))
            next_num = len(existing) + 1
            dest_filename = f"{model_name}-s{next_num}-original.jpg"
            dest_path = source_dir / dest_filename

            try:
                shutil.copy2(source_path, dest_path)
                print(f"  ✓ {source_path.name} → {dest_filename}")
                uploaded_count += 1
            except Exception as e:
                print(f"  ✗ Failed: {source_path.name} - {e}")

    if uploaded_count == 0:
        print("\n✗ No files uploaded")
        input("\nPress Enter to go back...")
        return

    print(f"\n✓ Uploaded {uploaded_count} file(s)")

    # Validate new sources
    print("\nValidating faces in uploaded images...")
    detector = FaceDetector()
    sources = list_source_images(model_name)

    if not sources:
        print("✗ No source images found")
        input("\nPress Enter to go back...")
        return

    print(f"Total sources: {len(sources)}")

    valid_count = 0
    for source_id, filename, filepath in sources:
        success, message = detector.validate_image(filepath)
        if success:
            valid_count += 1
        print(f"  {message}: {filename}")

    print(f"\n✓ {valid_count}/{len(sources)} have valid faces")

    # Update config
    config = load_config(model_name)
    config['sources'] = [
        {'id': sid, 'filename': fname, 'original_name': fname}
        for sid, fname, _ in sources
    ]
    save_config(model_name, config)

    print(f"✓ Config updated")

    # Ask if they want to add targets next
    print("\n" + "=" * 60)
    print("Next step: Add target images")
    print_menu({
        '1': 'Add NSFW targets now',
        '2': 'Add SFW targets now',
        '3': 'Skip for now (back to menu)'
    })

    next_choice = get_input("What next", ['1', '2', '3'])

    if next_choice == '1':
        add_targets_direct(model_name, 'nsfw')
    elif next_choice == '2':
        add_targets_direct(model_name, 'sfw')


def add_targets_direct(model_name, content_type):
    """Add target images directly (called from add_sources flow)"""
    clear_screen()
    print_header(f"Add {content_type.upper()} Targets: {model_name}")

    targets_dir = get_targets_path(model_name, content_type)
    targets_dir.mkdir(parents=True, exist_ok=True)

    # Upload files with improved UX
    print(f"\n{content_type.upper()} Target Upload")
    print("=" * 60)
    print("\nHow to upload:")
    print("  1. DRAG & DROP files from your file explorer into this terminal")
    print("  2. Or type/paste file paths")
    print("  3. Use wildcards: ~/Downloads/*.jpg")
    print("  4. Press Enter on empty line when done")
    print()

    uploaded_count = 0

    while True:
        file_input = input(f"Drop files or path (Enter to finish): ").strip()

        if not file_input:
            break

        # Remove quotes that terminals add when dragging
        file_input = file_input.strip("'\"")

        # Expand user path and wildcards
        file_input = os.path.expanduser(file_input)

        # Check if it's a glob pattern
        if '*' in file_input or '?' in file_input:
            matches = glob(file_input)
            if not matches:
                print(f"  ✗ No files match pattern: {file_input}")
                continue
            print(f"  Found {len(matches)} files from pattern")
            file_paths = matches
        else:
            file_paths = [file_input]

        # Process each file
        for file_path in file_paths:
            source_path = Path(file_path)

            if not source_path.exists():
                print(f"  ✗ Not found: {source_path.name}")
                continue

            if not source_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                print(f"  ✗ Skipping (not jpg/png): {source_path.name}")
                continue

            # Find next available number and use smart naming
            existing = list(targets_dir.glob('*.jpg')) + list(targets_dir.glob('*.jpeg')) + list(targets_dir.glob('*.png'))
            next_num = len(existing) + 1
            dest_filename = f"{model_name}-t{next_num}-{content_type}-original.jpg"
            dest_path = targets_dir / dest_filename

            try:
                shutil.copy2(source_path, dest_path)
                print(f"  ✓ {source_path.name} → {dest_filename}")
                uploaded_count += 1
            except Exception as e:
                print(f"  ✗ Failed: {source_path.name} - {e}")

    if uploaded_count == 0:
        print("\n✗ No files uploaded")
        input("\nPress Enter to continue...")
        return

    print(f"\n✓ Uploaded {uploaded_count} file(s)")

    # Validate targets
    print("\nValidating faces in uploaded images...")
    detector = FaceDetector()
    targets = list_target_images(model_name, content_type)

    if targets:
        print(f"Total {content_type.upper()} targets: {len(targets)}")

        valid_count = 0
        for target_id, filename, filepath in targets:
            success, message = detector.validate_image(filepath)
            if success:
                valid_count += 1
            print(f"  {message}: {filename}")

        print(f"\n✓ {valid_count}/{len(targets)} have valid faces")

    # Ask if they want to process now
    print("\n" + "=" * 60)
    print("Ready to process!")
    print_menu({
        '1': f'Start processing {content_type.upper()} targets now',
        '2': 'Back to menu (process later)'
    })

    process_choice = get_input("What next", ['1', '2'])

    if process_choice == '1':
        process_model(model_name, content_type)


def add_targets(model_name):
    """Add more target images to existing model"""
    clear_screen()
    print_header(f"Add Targets: {model_name}")

    # Choose content type
    print_menu({
        '1': 'Add NSFW targets',
        '2': 'Add SFW targets',
        '3': 'Back'
    })
    choice = get_input("Choose type", ['1', '2', '3'])

    if choice == '0' or choice == '3':
        return

    content_type = 'nsfw' if choice == '1' else 'sfw'
    add_targets_direct(model_name, content_type)


def reset_progress(model_name):
    """Reset progress for a model"""
    clear_screen()
    print_header(f"Reset Progress: {model_name}")

    print("⚠ WARNING: This will clear ALL progress tracking")
    print("  - Swap and enhancement progress will be reset")
    print("  - Existing result files will NOT be deleted")
    print("  - You can re-process to skip completed tasks")
    print()

    confirm = get_input("Are you sure? (yes/no)", ['yes', 'no'])

    if confirm == 'yes':
        tracker = ProgressTracker(model_name)
        tracker.reset()
        print("\n✓ Progress reset successfully")
    else:
        print("\n✗ Reset cancelled")

    input("\nPress Enter to continue...")


def view_all_models():
    """View all available models"""
    clear_screen()
    print_header("All Models")

    models = list_all_models()
    if not models:
        print("No models found.")
    else:
        for model in models:
            config = load_config(model)
            if config:
                print(f"\n{model}:")
                print(f"  Created: {config.get('created_at', 'Unknown')}")
                print(f"  Sources: {len(config.get('sources', []))}")
                print(f"  Bucket: {config.get('bucket_name', 'None')}")

                hist = config.get('processing_history', {})
                nsfw = hist.get('nsfw', {})
                sfw = hist.get('sfw', {})
                print(f"  NSFW processed: {nsfw.get('targets_processed', 0)}")
                print(f"  SFW processed: {sfw.get('targets_processed', 0)}")

    input("\nPress Enter to continue...")


def main():
    """Main application loop"""
    while True:
        choice = main_menu()

        if choice == '1':
            create_new_model()
        elif choice == '2':
            work_with_model()
        elif choice == '3':
            view_all_models()
        elif choice == '4':
            clear_screen()
            print("Goodbye!")
            break


if __name__ == "__main__":
    main()
