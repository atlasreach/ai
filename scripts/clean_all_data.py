#!/usr/bin/env python3
"""
Clean all training data including model gallery references
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🗑️  Cleaning all training data...")

# Get counts first
try:
    datasets = supabase.table('training_datasets').select('id').execute()
    images = supabase.table('training_images').select('id').execute()
    characters = supabase.table('characters').select('id').execute()
    gallery = supabase.table('model_gallery').select('id').execute()
    content_items = supabase.table('content_items').select('id').execute()

    print(f"\nFound:")
    print(f"  - {len(content_items.data)} content items")
    print(f"  - {len(gallery.data)} model gallery items")
    print(f"  - {len(datasets.data)} datasets")
    print(f"  - {len(images.data)} images")
    print(f"  - {len(characters.data)} characters")

    # Delete in correct order to handle foreign keys
    print("\nDeleting...")

    # 1. Delete content items first (references characters)
    if len(content_items.data) > 0:
        supabase.table('content_items').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"  ✅ Deleted {len(content_items.data)} content items")

    # 2. Delete model gallery (references characters)
    if len(gallery.data) > 0:
        supabase.table('model_gallery').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"  ✅ Deleted {len(gallery.data)} model gallery items")

    # 3. Delete training images
    if len(images.data) > 0:
        supabase.table('training_images').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"  ✅ Deleted {len(images.data)} training images")

    # 4. Delete datasets
    if len(datasets.data) > 0:
        supabase.table('training_datasets').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"  ✅ Deleted {len(datasets.data)} datasets")

    # 5. Delete characters

    if len(characters.data) > 0:
        supabase.table('characters').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"  ✅ Deleted {len(characters.data)} characters")

    print("\n✅ All training data cleaned! Ready for fresh test.")

except Exception as e:
    print(f"\n❌ Error: {e}")
