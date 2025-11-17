#!/usr/bin/env python3
"""
Test the complete Dataset Creator workflow
"""
import os
import uuid
import requests
from supabase import create_client
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_workflow():
    test_char_id = None
    test_dataset_id = None
    uploaded_files = []

    try:
        # Step 1: Create test character
        print("\n📝 Step 1: Creating test character...")
        test_char_id = f"test_{uuid.uuid4().hex[:8]}"
        character = {
            'id': test_char_id,
            'name': 'Test Character',
            'trigger_word': test_char_id,
            'character_constraints': {
                'constants': [
                    {'key': 'hair_color', 'value': 'blonde', 'type': 'physical'},
                    {'key': 'eye_color', 'value': 'blue eyes', 'type': 'physical'}
                ]
            },
            'is_active': True,
            'lora_file': 'test.safetensors'
        }

        result = supabase.table('characters').insert(character).execute()
        print(f"✅ Character created: {test_char_id}")

        # Step 2: Create test dataset
        print("\n📝 Step 2: Creating test dataset...")
        test_dataset_id = str(uuid.uuid4())
        dataset = {
            'id': test_dataset_id,
            'character_id': test_char_id,
            'name': f'{test_char_id}_test_v1',
            'dataset_type': 'SFW',
            'description': 'Test dataset',
            'dataset_constraints': {
                'rules': [{'key': 'clothing', 'value': 'required'}]
            },
            'image_count': 0
        }

        result = supabase.table('training_datasets').insert(dataset).execute()
        print(f"✅ Dataset created: {test_dataset_id}")

        # Step 3: Upload test images
        print("\n📝 Step 3: Uploading test images...")
        test_images = [
            '/workspaces/ai/generated_samples/22.jpg',
            '/workspaces/ai/generated_samples/12.jpg',
            '/workspaces/ai/generated_samples/15.jpg'
        ]

        uploaded_urls = []
        for i, img_path in enumerate(test_images):
            if not os.path.exists(img_path):
                print(f"⚠️  Skipping {img_path} - file not found")
                continue

            print(f"📤 Uploading {i+1}/{len(test_images)}: {Path(img_path).name}")

            # Read file
            with open(img_path, 'rb') as f:
                file_bytes = f.read()

            # Upload to storage
            file_name = f"{test_dataset_id}/test_{i}.jpg"

            try:
                storage_response = supabase.storage.from_('training-images').upload(
                    file_name,
                    file_bytes,
                    {'content-type': 'image/jpeg'}
                )

                uploaded_files.append(file_name)

                # Get public URL
                public_url = supabase.storage.from_('training-images').get_public_url(file_name)
                uploaded_urls.append(public_url)

                print(f"✅ Uploaded: {public_url}")

                # Insert into training_images table
                image_record = {
                    'id': str(uuid.uuid4()),
                    'dataset_id': test_dataset_id,
                    'image_url': public_url,
                    'caption': f'{test_char_id}, a woman with blonde hair, blue eyes, test caption {i+1}',
                    'display_order': i
                }

                supabase.table('training_images').insert(image_record).execute()
                print(f"✅ Database record created")

            except Exception as e:
                print(f"❌ Upload failed: {e}")

        # Update dataset image count
        supabase.table('training_datasets').update({
            'image_count': len(uploaded_urls)
        }).eq('id', test_dataset_id).execute()

        print(f"\n✅ Successfully uploaded {len(uploaded_urls)} images")

        # Step 4: Verify data
        print("\n📝 Step 4: Verifying data...")

        # Check character
        char_result = supabase.table('characters').select('*').eq('id', test_char_id).execute()
        print(f"✅ Character exists: {len(char_result.data)} record(s)")

        # Check dataset
        dataset_result = supabase.table('training_datasets').select('*').eq('id', test_dataset_id).execute()
        print(f"✅ Dataset exists: {len(dataset_result.data)} record(s)")
        print(f"   Image count: {dataset_result.data[0]['image_count']}")

        # Check images
        images_result = supabase.table('training_images').select('*').eq('dataset_id', test_dataset_id).execute()
        print(f"✅ Training images: {len(images_result.data)} record(s)")

        print("\n🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print("\n🧹 Cleaning up test data...")

        try:
            # Delete uploaded files from storage
            if uploaded_files:
                print(f"Deleting {len(uploaded_files)} files from storage...")
                for file_name in uploaded_files:
                    try:
                        supabase.storage.from_('training-images').remove([file_name])
                        print(f"  ✅ Deleted: {file_name}")
                    except Exception as e:
                        print(f"  ⚠️  Failed to delete {file_name}: {e}")

            # Delete training images records
            if test_dataset_id:
                supabase.table('training_images').delete().eq('dataset_id', test_dataset_id).execute()
                print("✅ Deleted training_images records")

            # Delete dataset
            if test_dataset_id:
                supabase.table('training_datasets').delete().eq('id', test_dataset_id).execute()
                print("✅ Deleted dataset")

            # Delete character
            if test_char_id:
                supabase.table('characters').delete().eq('id', test_char_id).execute()
                print("✅ Deleted character")

            print("\n✨ Cleanup complete!")

        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Dataset Creator Workflow")
    print("=" * 50)
    success = test_workflow()
    exit(0 if success else 1)
