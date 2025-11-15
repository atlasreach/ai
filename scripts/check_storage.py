#!/usr/bin/env python3
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

print("📦 Checking Supabase Storage bucket contents...")
try:
    # List all folders in bucket
    items = supabase.storage.from_('training-images').list()
    print(f"✅ Found {len(items)} items in root:")

    if len(items) == 0:
        print("   ⚠️  Bucket is EMPTY - no files uploaded yet!")
    else:
        for item in items:
            print(f"\n   📁 {item['name']}")

            # List files in each folder
            try:
                files = supabase.storage.from_('training-images').list(item['name'])
                print(f"      └─ {len(files)} files inside:")
                for f in files[:5]:  # Show first 5
                    size_kb = f.get('metadata', {}).get('size', 0) / 1024
                    print(f"         - {f['name']} ({size_kb:.1f} KB)")
            except Exception as e:
                print(f"      └─ Error listing: {e}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
