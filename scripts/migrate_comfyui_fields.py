"""
Database Migration - Add ComfyUI Integration Fields
Run this to add lora_strength and comfyui_workflow to characters table
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
        print("🔄 Starting ComfyUI fields migration...")

        # 1. Add lora_strength column
        print("1️⃣  Adding lora_strength to characters table...")
        cur.execute("""
            ALTER TABLE characters
            ADD COLUMN IF NOT EXISTS lora_strength FLOAT DEFAULT 0.8;
        """)

        # 2. Add comfyui_workflow column
        print("2️⃣  Adding comfyui_workflow to characters table...")
        cur.execute("""
            ALTER TABLE characters
            ADD COLUMN IF NOT EXISTS comfyui_workflow TEXT DEFAULT 'workflows/qwen/instagram_single.json';
        """)

        # 3. Update existing characters with default workflow
        print("3️⃣  Setting default workflow for existing characters...")
        cur.execute("""
            UPDATE characters
            SET comfyui_workflow = 'workflows/qwen/instagram_single.json'
            WHERE comfyui_workflow IS NULL;
        """)

        conn.commit()
        print("✅ ComfyUI fields migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
