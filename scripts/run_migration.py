#!/usr/bin/env python3
"""
Migration Helper Script
Guides user through database migration process
"""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://yiriqesejsbzmzxdxiqt.supabase.co')

print("=" * 70)
print("  DATABASE MIGRATION: New Model/Dataset Schema")
print("=" * 70)
print()
print("This migration will:")
print("  ✓ Backup existing tables (characters, training_datasets, training_images)")
print("  ✓ Create new tables (models, datasets, dataset_images)")
print("  ✓ Add indexes and triggers")
print("  ✓ Set up Row Level Security")
print()
print("📋 TO RUN THIS MIGRATION:")
print()
print("1. Open Supabase SQL Editor:")
print(f"   {SUPABASE_URL}/project/_/sql")
print()
print("2. Copy the SQL from:")
print("   /workspaces/ai/scripts/migrate_new_schema.sql")
print()
print("3. Paste and run in SQL Editor")
print()
print("4. Verify tables created:")
print("   - models")
print("   - datasets")
print("   - dataset_images")
print()
print("=" * 70)
print()

response = input("Would you like to see the SQL file content now? (yes/no): ")

if response.lower() == 'yes':
    print("\n" + "=" * 70)
    with open('/workspaces/ai/scripts/migrate_new_schema.sql', 'r') as f:
        print(f.read())
    print("=" * 70)
