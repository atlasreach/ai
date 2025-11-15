"""
Add RLS policies for training tables
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
        print("🔒 Adding RLS policies...")

        # Enable RLS
        cur.execute("ALTER TABLE training_datasets ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE training_images ENABLE ROW LEVEL SECURITY;")

        # Drop existing policies if they exist
        cur.execute("DROP POLICY IF EXISTS \"Enable read access for all users\" ON training_datasets;")
        cur.execute("DROP POLICY IF EXISTS \"Enable insert for authenticated users\" ON training_datasets;")
        cur.execute("DROP POLICY IF EXISTS \"Enable update for authenticated users\" ON training_datasets;")
        cur.execute("DROP POLICY IF EXISTS \"Enable delete for authenticated users\" ON training_datasets;")

        cur.execute("DROP POLICY IF EXISTS \"Enable read access for all users\" ON training_images;")
        cur.execute("DROP POLICY IF EXISTS \"Enable insert for authenticated users\" ON training_images;")
        cur.execute("DROP POLICY IF EXISTS \"Enable update for authenticated users\" ON training_images;")
        cur.execute("DROP POLICY IF EXISTS \"Enable delete for authenticated users\" ON training_images;")

        # Create new policies
        cur.execute("CREATE POLICY \"Enable read access for all users\" ON training_datasets FOR SELECT USING (true);")
        cur.execute("CREATE POLICY \"Enable insert for authenticated users\" ON training_datasets FOR INSERT WITH CHECK (true);")
        cur.execute("CREATE POLICY \"Enable update for authenticated users\" ON training_datasets FOR UPDATE USING (true);")
        cur.execute("CREATE POLICY \"Enable delete for authenticated users\" ON training_datasets FOR DELETE USING (true);")

        cur.execute("CREATE POLICY \"Enable read access for all users\" ON training_images FOR SELECT USING (true);")
        cur.execute("CREATE POLICY \"Enable insert for authenticated users\" ON training_images FOR INSERT WITH CHECK (true);")
        cur.execute("CREATE POLICY \"Enable update for authenticated users\" ON training_images FOR UPDATE USING (true);")
        cur.execute("CREATE POLICY \"Enable delete for authenticated users\" ON training_images FOR DELETE USING (true);")

        conn.commit()
        print("✅ RLS policies added successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed: {e}")
        raise

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_policies()
