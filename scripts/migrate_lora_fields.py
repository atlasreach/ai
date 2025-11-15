#!/usr/bin/env python3
"""
Database migration: Add LoRA metadata fields
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Get direct database URL
db_url = os.getenv('DIRECT_DATABASE_URL')

print("🗄️  Running database migration...")
print(f"   Connecting to database...")

# Connect and run migration
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Execute ALTER TABLE statements
statements = [
    "ALTER TABLE training_datasets ADD COLUMN IF NOT EXISTS output_filename TEXT",
    "ALTER TABLE training_datasets ADD COLUMN IF NOT EXISTS huggingface_repo TEXT",
    "ALTER TABLE training_datasets ADD COLUMN IF NOT EXISTS lora_download_url TEXT",
    "ALTER TABLE training_datasets ADD COLUMN IF NOT EXISTS file_size_mb REAL",
    "ALTER TABLE training_datasets ADD COLUMN IF NOT EXISTS comfyui_installed BOOLEAN DEFAULT FALSE",
    "CREATE INDEX IF NOT EXISTS idx_training_datasets_status ON training_datasets(training_status)",
    "CREATE INDEX IF NOT EXISTS idx_training_datasets_character ON training_datasets(character_id)"
]

for stmt in statements:
    try:
        cur.execute(stmt)
        print(f"   ✅ {stmt[:70]}...")
    except Exception as e:
        print(f"   ⚠️  {stmt[:50]}... : {e}")

conn.commit()
cur.close()
conn.close()

print("\n✅ Database migration completed!")
print("   Added fields: output_filename, huggingface_repo, lora_download_url, file_size_mb, comfyui_installed")
