#!/usr/bin/env python3
"""
Run the persona system database migration
"""
import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    """Execute the persona system SQL migration"""

    # Get database URL
    db_url = os.getenv('DIRECT_DATABASE_URL')
    if not db_url:
        print("❌ DIRECT_DATABASE_URL not found in .env")
        sys.exit(1)

    # Read SQL file
    sql_file = Path(__file__).parent / 'migrate_persona_system_safe.sql'
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        sys.exit(1)

    print(f"📄 Reading SQL from: {sql_file}")
    sql = sql_file.read_text()

    # Connect and execute
    print(f"🔌 Connecting to database...")

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        print("🚀 Running migration...")

        # Execute the entire SQL file as one transaction
        cursor.execute(sql)
        conn.commit()

        print("✅ Migration completed successfully!")

        # Verify tables created
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('models', 'reference_libraries', 'personas', 'generated_content')
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print(f"\n📊 Created/verified {len(tables)} tables:")
        for (table_name,) in tables:
            print(f"   ✓ {table_name}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_migration()
