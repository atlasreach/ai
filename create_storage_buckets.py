#!/usr/bin/env python3
"""
Create Supabase Storage buckets for images
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Creating Supabase Storage buckets...")

# Create reference-images bucket
try:
    supabase.storage.create_bucket(
        'reference-images',
        options={'public': True}
    )
    print("✓ Created 'reference-images' bucket (public)")
except Exception as e:
    print(f"  'reference-images' bucket: {e}")

# Create generated-images bucket
try:
    supabase.storage.create_bucket(
        'generated-images',
        options={'public': True}
    )
    print("✓ Created 'generated-images' bucket (public)")
except Exception as e:
    print(f"  'generated-images' bucket: {e}")

print("\n✓ Storage buckets ready!")
