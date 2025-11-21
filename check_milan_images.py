#!/usr/bin/env python3
"""
Check Milan reference images in Supabase
"""
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

# Get Supabase credentials
url = os.getenv('SUPABASE_URL', 'https://yiriqesejsbzmzxdxiqt.supabase.co')
key = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlpcmlxZXNlanNiem16eGR4aXF0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMxNTA2MjUsImV4cCI6MjA3ODcyNjYyNX0.Ii8uNcc5X3lxt8PCt2VpmEQl2pyECgHRVklUfky7DEk')

# Create Supabase client
supabase = create_client(url, key)

print("🔍 Checking Milan reference images...\n")

try:
    # Get Milan images
    print("📊 Milan Reference Images:\n")

    response = supabase.table('reference_images') \
        .select('*') \
        .eq('category', 'milan') \
        .order('created_at', desc=True) \
        .execute()

    if response.data:
        print(f"✓ Found {len(response.data)} Milan images\n")

        for i, row in enumerate(response.data[:5], 1):
            print(f"{i}. {row['filename']}")
            print(f"   Storage Path: {row['storage_path']}")
            print(f"   Created: {row['created_at']}")
            print(f"   Vision Description:")
            print(f"   {row.get('vision_description', 'No description')}")
            print()

        if len(response.data) > 5:
            print(f"... and {len(response.data) - 5} more Milan images")
    else:
        print("   No Milan images found.")

    # Get category summary
    print("\n📊 Category Summary:")
    all_response = supabase.table('reference_images').select('category').execute()

    categories = {}
    for row in all_response.data:
        cat = row['category']
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items()):
        print(f"   {cat}: {count} images")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
