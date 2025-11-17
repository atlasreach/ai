#!/usr/bin/env python3
"""
Check what's in the instagram_posts table
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

print("\n📊 Checking instagram_posts table...\n")

try:
    result = supabase.table('instagram_posts').select('*').execute()
    print(f"Total posts: {len(result.data)}")

    if result.data:
        for post in result.data[:5]:
            print(f"  - {post.get('id')}: {post.get('caption', 'No caption')[:50]}")
    else:
        print("  No posts found")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n📊 Checking instagram_accounts table...\n")

try:
    result = supabase.table('instagram_accounts').select('*').execute()
    print(f"Total accounts: {len(result.data)}")

    if result.data:
        for acc in result.data:
            print(f"  - {acc.get('username')}: {acc.get('id')}")
            print(f"    model_id: {acc.get('model_id')}")
    else:
        print("  No accounts found")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n📊 Checking models table...\n")

try:
    result = supabase.table('models').select('id, name, instagram_account_id, instagram_username').execute()
    print(f"Total models: {len(result.data)}")

    if result.data:
        for model in result.data:
            print(f"  - {model.get('name')}: {model.get('id')}")
            print(f"    instagram_account_id: {model.get('instagram_account_id')}")
            print(f"    instagram_username: {model.get('instagram_username')}")
    else:
        print("  No models found")

except Exception as e:
    print(f"❌ Error: {e}")
