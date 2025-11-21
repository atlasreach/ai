from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the direct connection URL
direct_url = os.getenv('DIRECT_URL')

# Create engine
engine = create_engine(direct_url)

# Create a test table
create_table_sql = """
CREATE TABLE IF NOT EXISTS test_table (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);
"""

try:
    with engine.connect() as conn:
        # Create the table
        conn.execute(text(create_table_sql))
        conn.commit()
        print("✓ Test table 'test_table' created successfully!")

        # Verify the table was created
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'test_table'
            ORDER BY ordinal_position;
        """))

        columns = result.fetchall()
        print("\nTable structure:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")

except Exception as e:
    print(f"✗ Error creating table: {e}")
    import traceback
    traceback.print_exc()
