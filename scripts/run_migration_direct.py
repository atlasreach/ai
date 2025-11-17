#!/usr/bin/env python3
"""
Run database migration directly on Supabase
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

if not DATABASE_URL:
    print("❌ DIRECT_DATABASE_URL not found in .env")
    exit(1)

print("🔄 Connecting to Supabase database...")

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("✅ Connected to database")
    print("📋 Running migration SQL...")

    # Read SQL file
    with open('/workspaces/ai/scripts/migrate_new_schema.sql', 'r') as f:
        sql = f.read()

    # Execute SQL
    cur.execute(sql)
    conn.commit()

    print("✅ Migration completed successfully!")

    # Verify tables exist
    print("\n🔍 Verifying tables...")

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('models', 'datasets', 'dataset_images')
        ORDER BY table_name;
    """)

    tables = cur.fetchall()

    for table in tables:
        print(f"  ✓ {table[0]} table exists")

    # Check counts
    print("\n📊 Current data:")

    cur.execute("SELECT COUNT(*) FROM models")
    model_count = cur.fetchone()[0]
    print(f"  - Models: {model_count}")

    cur.execute("SELECT COUNT(*) FROM datasets")
    dataset_count = cur.fetchone()[0]
    print(f"  - Datasets: {dataset_count}")

    cur.execute("SELECT COUNT(*) FROM dataset_images")
    image_count = cur.fetchone()[0]
    print(f"  - Images: {image_count}")

    cur.close()
    conn.close()

    print("\n✅ Migration verification complete!")
    print("🚀 Ready to start the application")

except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
