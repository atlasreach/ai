#!/usr/bin/env python3
"""
Add training status fields to training_datasets table
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

def migrate():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        print("🔄 Adding training status fields...")

        # Add training status columns
        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS training_status TEXT DEFAULT 'not_started';
        """)
        print("  ✅ Added training_status")

        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS runpod_job_id TEXT;
        """)
        print("  ✅ Added runpod_job_id")

        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS training_progress INTEGER DEFAULT 0;
        """)
        print("  ✅ Added training_progress")

        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS training_config JSONB;
        """)
        print("  ✅ Added training_config")

        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS training_error TEXT;
        """)
        print("  ✅ Added training_error")

        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS lora_download_url TEXT;
        """)
        print("  ✅ Added lora_download_url")

        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS huggingface_url TEXT;
        """)
        print("  ✅ Added huggingface_url")

        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS training_started_at TIMESTAMP;
        """)
        print("  ✅ Added training_started_at")

        cur.execute("""
            ALTER TABLE training_datasets
            ADD COLUMN IF NOT EXISTS training_completed_at TIMESTAMP;
        """)
        print("  ✅ Added training_completed_at")

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
