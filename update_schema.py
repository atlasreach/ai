"""
Update database schema for Content Studio
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

print("🔄 Updating database schema for Content Studio...")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Drop old content_items table and recreate with correct schema
print("   Dropping old content_items table...")
cursor.execute("DROP TABLE IF EXISTS content_items CASCADE")

print("   Creating new content_items table...")
cursor.execute("""
    CREATE TABLE content_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        character_id TEXT REFERENCES characters(id),

        -- Type
        content_type TEXT,
        status TEXT DEFAULT 'processing',

        -- Files
        original_file_url TEXT,
        face_swapped_url TEXT,
        video_url TEXT,
        final_url TEXT,

        -- Metadata
        caption TEXT,
        operations_performed JSONB,
        replicate_models_used JSONB,
        processing_time_seconds REAL,

        -- Social media
        platforms TEXT[],

        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
""")

# Create indexes
print("   Creating indexes...")
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_content_items_character
    ON content_items(character_id)
""")
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_content_items_status
    ON content_items(status)
""")
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_content_items_created
    ON content_items(created_at DESC)
""")

conn.commit()

print("✅ Schema updated!")

# Verify
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'content_items'")
columns = [row[0] for row in cursor.fetchall()]
print(f"\n📊 Content items columns: {', '.join(columns)}")

cursor.close()
conn.close()

print("\n✅ Database ready for Content Studio!")
