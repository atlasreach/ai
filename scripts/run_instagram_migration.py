#!/usr/bin/env python3
"""
Run Instagram Library Migration
Execute this to create instagram_accounts and instagram_posts tables
"""
from supabase import create_client
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def main():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in .env")
        return

    print(f"Connecting to Supabase: {supabase_url[:40]}...")
    supabase = create_client(supabase_url, supabase_key)

    # Read SQL file
    sql_file = os.path.join(os.path.dirname(__file__), 'create_instagram_library.sql')
    with open(sql_file, 'r') as f:
        sql = f.read()

    print("\n" + "="*60)
    print("📋 Copy this SQL to Supabase SQL Editor:")
    print("="*60)
    print(sql)
    print("="*60)
    print("\nOr manually run: scripts/create_instagram_library.sql")

if __name__ == '__main__':
    main()
