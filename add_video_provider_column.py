from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the direct connection URL
direct_url = os.getenv('DIRECT_URL')

# Create engine
engine = create_engine(direct_url)

# Add provider column to video_generation_jobs
add_provider_column_sql = """
ALTER TABLE video_generation_jobs
ADD COLUMN IF NOT EXISTS provider VARCHAR(20) NOT NULL DEFAULT 'kling';
"""

# Create index on provider
create_index_sql = """
CREATE INDEX IF NOT EXISTS idx_video_jobs_provider ON video_generation_jobs(provider);
"""

try:
    with engine.connect() as conn:
        # Add provider column
        print("Adding provider column to video_generation_jobs table...")
        conn.execute(text(add_provider_column_sql))
        conn.commit()
        print("✓ Provider column added successfully!")

        # Create index
        print("\nCreating index on provider column...")
        conn.execute(text(create_index_sql))
        conn.commit()
        print("✓ Index created successfully!")

        # Verify the column was added
        result = conn.execute(text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'video_generation_jobs'
            AND column_name = 'provider';
        """))

        columns = result.fetchall()
        if columns:
            print("\n" + "="*60)
            print("Provider column details:")
            print("="*60)
            for col_name, col_type, col_default in columns:
                print(f"  {col_name:20s} {col_type:25s} default: {col_default}")
            print("="*60)

        print("\n✅ Video provider schema update complete!")

except Exception as e:
    print(f"✗ Error updating schema: {e}")
    import traceback
    traceback.print_exc()
