#!/usr/bin/env python3
"""
Immediate cleanup script - deletes all data from database
"""
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def cleanup_all():
    """Delete all data from all tables"""
    # Initialize Supabase client
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )

    print("\n🗑️  Starting cleanup...\n")

    # Delete in order of dependencies
    tables = [
        'instagram_posts',
        'instagram_accounts',
        'dataset_images',
        'datasets',
        'models'
    ]

    for table in tables:
        try:
            print(f"🗑️  Deleting all from {table}...", end=' ')
            result = supabase.table(table).delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            count = len(result.data) if result.data else 0
            print(f"✅ Deleted {count} rows")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n✅ Cleanup complete!\n")

if __name__ == "__main__":
    cleanup_all()
