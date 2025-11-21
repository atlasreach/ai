from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the direct connection URL
direct_url = os.getenv('DIRECT_URL')

# Create engine
engine = create_engine(direct_url)

# Add group_id column to generated_images table
add_column_sql = """
-- Add group_id column for manual grouping
ALTER TABLE generated_images
ADD COLUMN IF NOT EXISTS group_id TEXT;

-- Add index for faster grouping queries
CREATE INDEX IF NOT EXISTS idx_generated_images_group_id ON generated_images(group_id);
"""

try:
    with engine.connect() as conn:
        # Execute the migration
        conn.execute(text(add_column_sql))
        conn.commit()
        print("✓ Added 'group_id' column to generated_images table successfully!")

        # Verify the column was added
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'generated_images' AND column_name = 'group_id'
            ORDER BY ordinal_position;
        """))

        columns = result.fetchall()
        if columns:
            print("\nColumn added:")
            for col_name, col_type, nullable in columns:
                print(f"  - {col_name}: {col_type} (nullable: {nullable})")
        else:
            print("\n⚠️ Column not found after creation (might already exist)")

        # Verify the index was created
        result_idx = conn.execute(text("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE tablename = 'generated_images' AND indexname = 'idx_generated_images_group_id';
        """))

        indexes = result_idx.fetchall()
        if indexes:
            print("\nIndex created:")
            for idx_name, table_name in indexes:
                print(f"  - {idx_name} on {table_name}")

except Exception as e:
    print(f"✗ Error adding column: {e}")
    import traceback
    traceback.print_exc()
