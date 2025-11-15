#!/usr/bin/env python3
"""
Make lora_file column nullable in characters table
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'ai_studio')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

print("🔌 Connecting to database...")

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()

    print("✅ Connected to database")

    # Make lora_file nullable
    print("📝 Making lora_file column nullable...")
    cur.execute("""
        ALTER TABLE characters
        ALTER COLUMN lora_file DROP NOT NULL;
    """)

    conn.commit()
    print("✅ Migration completed successfully!")

    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
