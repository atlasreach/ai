"""
Add storage policies for training-images bucket
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

def add_policies():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        print("🔒 Adding storage policies...")

        # Drop existing policies if they exist
        cur.execute("DROP POLICY IF EXISTS \"Allow public uploads\" ON storage.objects;")
        cur.execute("DROP POLICY IF EXISTS \"Allow public reads\" ON storage.objects;")
        cur.execute("DROP POLICY IF EXISTS \"Allow public deletes\" ON storage.objects;")

        # Create policies for public access (for now - can restrict later)
        print("📝 Creating upload policy...")
        cur.execute("""
            CREATE POLICY "Allow public uploads"
            ON storage.objects FOR INSERT
            WITH CHECK (bucket_id = 'training-images');
        """)

        print("📝 Creating read policy...")
        cur.execute("""
            CREATE POLICY "Allow public reads"
            ON storage.objects FOR SELECT
            USING (bucket_id = 'training-images');
        """)

        print("📝 Creating delete policy...")
        cur.execute("""
            CREATE POLICY "Allow public deletes"
            ON storage.objects FOR DELETE
            USING (bucket_id = 'training-images');
        """)

        conn.commit()
        print("✅ Storage policies added successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed: {e}")
        raise

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_policies()
