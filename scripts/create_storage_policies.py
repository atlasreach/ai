#!/usr/bin/env python3
"""
Create storage policies for training-images bucket
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Get database connection from Supabase URL
# Format: postgresql://postgres:[PASSWORD]@db.yiriqesejsbzmzxdxiqt.supabase.co:5432/postgres
SUPABASE_DB_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD')
SUPABASE_PROJECT_REF = 'yiriqesejsbzmzxdxiqt'

if not SUPABASE_DB_PASSWORD:
    print("❌ SUPABASE_DB_PASSWORD not found in .env")
    print("You can find it in your Supabase project settings > Database > Connection string")
    exit(1)

conn_string = f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{SUPABASE_DB_PASSWORD}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

print("🔌 Connecting to Supabase database...")

try:
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()

    print("✅ Connected to database")

    # Create policy for public read access
    print("📝 Creating public read policy...")
    cur.execute("""
        CREATE POLICY "Public Access"
        ON storage.objects FOR SELECT
        USING (bucket_id = 'training-images');
    """)

    # Create policy for authenticated uploads
    print("📝 Creating authenticated upload policy...")
    cur.execute("""
        CREATE POLICY "Authenticated users can upload"
        ON storage.objects FOR INSERT
        TO authenticated
        WITH CHECK (bucket_id = 'training-images');
    """)

    # Create policy for authenticated updates
    print("📝 Creating authenticated update policy...")
    cur.execute("""
        CREATE POLICY "Authenticated users can update"
        ON storage.objects FOR UPDATE
        TO authenticated
        USING (bucket_id = 'training-images');
    """)

    # Create policy for authenticated deletes
    print("📝 Creating authenticated delete policy...")
    cur.execute("""
        CREATE POLICY "Authenticated users can delete"
        ON storage.objects FOR DELETE
        TO authenticated
        USING (bucket_id = 'training-images');
    """)

    # Commit changes
    conn.commit()
    print("✅ All storage policies created successfully!")

    cur.close()
    conn.close()

except psycopg2.errors.DuplicateObject as e:
    print("⚠️  Policies may already exist:", e)
    print("✅ Storage bucket is ready to use!")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
