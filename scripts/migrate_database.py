"""
Database Migration - Add Training Datasets Support
Run this once to add new tables for Dataset Creator
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
        print("🔄 Starting database migration...")

        # 1. Add character_constraints column to characters table (if not exists)
        print("1️⃣  Adding character_constraints to characters table...")
        cur.execute("""
            ALTER TABLE characters
            ADD COLUMN IF NOT EXISTS character_constraints JSONB DEFAULT '{"constants": []}';
        """)

        # 2. Add trigger_word column to characters table (if not exists)
        print("2️⃣  Adding trigger_word to characters table...")
        cur.execute("""
            ALTER TABLE characters
            ADD COLUMN IF NOT EXISTS trigger_word TEXT;
        """)

        # Set trigger_word = id for existing characters if NULL
        cur.execute("""
            UPDATE characters
            SET trigger_word = id
            WHERE trigger_word IS NULL;
        """)

        # 3. Add lora_file column to characters table (if not exists)
        print("3️⃣  Adding lora_file to characters table...")
        cur.execute("""
            ALTER TABLE characters
            ADD COLUMN IF NOT EXISTS lora_file TEXT;
        """)

        # 4. Create training_datasets table
        print("4️⃣  Creating training_datasets table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS training_datasets (
                id UUID PRIMARY KEY,
                character_id TEXT REFERENCES characters(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                dataset_type TEXT NOT NULL,  -- 'SFW' or 'NSFW'
                description TEXT,
                dataset_constraints JSONB DEFAULT '{"rules": []}',
                caption_format TEXT,
                image_count INTEGER DEFAULT 0,
                storage_url TEXT,  -- S3/Dropbox URL for ZIP
                lora_file TEXT,  -- LoRA file after training
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # 5. Create training_images table
        print("5️⃣  Creating training_images table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS training_images (
                id UUID PRIMARY KEY,
                dataset_id UUID REFERENCES training_datasets(id) ON DELETE CASCADE,
                image_url TEXT NOT NULL,
                caption TEXT NOT NULL,
                metadata JSONB DEFAULT '{}',
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # 6. Create indexes for performance
        print("6️⃣  Creating indexes...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_training_datasets_character
            ON training_datasets(character_id);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_training_images_dataset
            ON training_images(dataset_id);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_training_images_order
            ON training_images(dataset_id, display_order);
        """)

        conn.commit()
        print("✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
