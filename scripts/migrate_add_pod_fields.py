#!/usr/bin/env python3
"""
Add pod_id and training_path fields to training_datasets
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

print("🔄 Adding pod fields to training_datasets...")

# Connect directly to database
conn = psycopg2.connect(os.getenv('DIRECT_DATABASE_URL'))
cur = conn.cursor()

# Add runpod_pod_id and training_path columns
migrations = [
    "ALTER TABLE training_datasets ADD COLUMN IF NOT EXISTS runpod_pod_id TEXT;",
    "ALTER TABLE training_datasets ADD COLUMN IF NOT EXISTS training_path TEXT;"
]

for migration in migrations:
    try:
        cur.execute(migration)
        conn.commit()
        print(f"✅ {migration}")
    except Exception as e:
        print(f"⚠️  {migration}")
        print(f"   Error: {e}")
        conn.rollback()

cur.close()
conn.close()

print("\n✅ Migration complete!")
