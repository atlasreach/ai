"""
Test Supabase connection and create a test table
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Get database URL from env
DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

print("🔗 Connecting to Supabase...")
print(f"   Database: {DATABASE_URL.split('@')[1].split(':')[0] if '@' in DATABASE_URL else 'unknown'}")

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("✅ Connected successfully!")

    # Create a test table
    print("\n📝 Creating test table 'characters'...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lora_file TEXT NOT NULL,
            trigger_word TEXT NOT NULL,
            description TEXT,
            thumbnail_url TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    conn.commit()
    print("✅ Table 'characters' created!")

    # Insert test data
    print("\n📥 Inserting test characters...")

    cursor.execute("""
        INSERT INTO characters (id, name, lora_file, trigger_word, description)
        VALUES
            ('milan', 'Milan', 'milan_000002000.safetensors', 'milan', 'Professional female model'),
            ('skyler', 'Skyler', 'skyler_000002000.safetensors', 'skyler', 'Professional female model')
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            lora_file = EXCLUDED.lora_file,
            trigger_word = EXCLUDED.trigger_word,
            description = EXCLUDED.description
    """)

    conn.commit()
    print("✅ Test characters inserted!")

    # Query the table
    print("\n📊 Querying characters table...")
    cursor.execute("SELECT id, name, lora_file, trigger_word FROM characters")
    rows = cursor.fetchall()

    print(f"   Found {len(rows)} characters:")
    for row in rows:
        print(f"   - {row[1]} ({row[0]}): {row[2]}")

    # Test creating content_items table
    print("\n📝 Creating 'content_items' table...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            character_id TEXT REFERENCES characters(id),
            content_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            prompt TEXT,
            negative_prompt TEXT,
            caption TEXT,

            -- Media URLs
            source_image_url TEXT,
            processed_image_url TEXT,
            video_url TEXT,
            thumbnail_url TEXT,

            -- Storage
            s3_key TEXT,
            storage_metadata JSONB,

            -- Generation parameters
            generation_params JSONB,
            generation_time REAL,

            -- Workflow
            workflow_type TEXT,
            workflow_steps JSONB,

            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    conn.commit()
    print("✅ Table 'content_items' created!")

    # Create index
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
    print("✅ Indexes created!")

    # Test insert content item
    print("\n📥 Inserting test content item...")
    cursor.execute("""
        INSERT INTO content_items (
            character_id, content_type, status, prompt,
            processed_image_url, generation_params
        )
        VALUES (
            'milan',
            'image',
            'ready',
            'Milan, professional headshot, studio lighting',
            'https://ai-character-generations.s3.us-east-2.amazonaws.com/test.png',
            '{"steps": 30, "cfg": 4.0}'::jsonb
        )
        RETURNING id, character_id, content_type, status
    """)

    result = cursor.fetchone()
    conn.commit()
    print(f"✅ Test content item created: {result[0]}")

    # Count content items
    cursor.execute("SELECT COUNT(*) FROM content_items")
    count = cursor.fetchone()[0]
    print(f"   Total content items: {count}")

    print("\n🎉 All tests passed! Supabase is fully functional!")

    # Close connection
    cursor.close()
    conn.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
