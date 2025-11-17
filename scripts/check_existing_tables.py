#!/usr/bin/env python3
"""Check existing database tables"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DIRECT_DATABASE_URL'))
cursor = conn.cursor()

cursor.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

print("\n📊 Existing tables:")
for (table_name,) in cursor.fetchall():
    print(f"   - {table_name}")

# Check if models table exists and its structure
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'models'
    ORDER BY ordinal_position
""")

models_columns = cursor.fetchall()
if models_columns:
    print(f"\n📋 'models' table columns:")
    for col_name, data_type in models_columns:
        print(f"   - {col_name}: {data_type}")
else:
    print(f"\n✓ 'models' table does not exist")

cursor.close()
conn.close()
