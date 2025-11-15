#!/usr/bin/env python3
"""
Delete all training datasets, images, and characters from database
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🗑️  Deleting all training data...")

# Get counts first
datasets = supabase.table('training_datasets').select('id').execute()
images = supabase.table('training_images').select('id').execute()
characters = supabase.table('characters').select('id').execute()

print(f"\nFound:")
print(f"  - {len(datasets.data)} datasets")
print(f"  - {len(images.data)} images")
print(f"  - {len(characters.data)} characters")

# Delete all (cascade should handle relationships)
print("\nDeleting...")

# Delete training images first
if len(images.data) > 0:
    supabase.table('training_images').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print(f"  ✅ Deleted {len(images.data)} training images")

# Delete datasets
if len(datasets.data) > 0:
    supabase.table('training_datasets').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print(f"  ✅ Deleted {len(datasets.data)} datasets")

# Delete characters
if len(characters.data) > 0:
    supabase.table('characters').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
    print(f"  ✅ Deleted {len(characters.data)} characters")

print("\n✅ All training data deleted! Ready for fresh start.")
