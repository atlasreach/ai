from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the direct connection URL
direct_url = os.getenv('DIRECT_URL')

# Create engine
engine = create_engine(direct_url)

# Create video generation jobs table
create_table_sql = """
CREATE TABLE IF NOT EXISTS video_generation_jobs (
    id SERIAL PRIMARY KEY,
    start_image_id INTEGER REFERENCES generated_images(id),
    end_image_id INTEGER REFERENCES generated_images(id),
    model_id INTEGER REFERENCES models(id),
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT DEFAULT '',
    duration INTEGER NOT NULL DEFAULT 5,
    mode VARCHAR(20) NOT NULL DEFAULT 'standard',
    replicate_id TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    video_url TEXT,
    error TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

# Create indexes
create_indexes_sql = """
CREATE INDEX IF NOT EXISTS idx_video_jobs_status ON video_generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_video_jobs_created_at ON video_generation_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_video_jobs_model_id ON video_generation_jobs(model_id);
CREATE INDEX IF NOT EXISTS idx_video_jobs_replicate_id ON video_generation_jobs(replicate_id);
"""

# Create update trigger function
create_trigger_function_sql = """
CREATE OR REPLACE FUNCTION update_video_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Create trigger
create_trigger_sql = """
DROP TRIGGER IF EXISTS trigger_update_video_jobs_updated_at ON video_generation_jobs;
CREATE TRIGGER trigger_update_video_jobs_updated_at
    BEFORE UPDATE ON video_generation_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_video_jobs_updated_at();
"""

try:
    with engine.connect() as conn:
        # Create the table
        print("Creating video_generation_jobs table...")
        conn.execute(text(create_table_sql))
        conn.commit()
        print("✓ Table 'video_generation_jobs' created successfully!")

        # Create indexes
        print("\nCreating indexes...")
        conn.execute(text(create_indexes_sql))
        conn.commit()
        print("✓ Indexes created successfully!")

        # Create trigger function
        print("\nCreating update trigger function...")
        conn.execute(text(create_trigger_function_sql))
        conn.commit()
        print("✓ Trigger function created successfully!")

        # Create trigger
        print("\nCreating update trigger...")
        conn.execute(text(create_trigger_sql))
        conn.commit()
        print("✓ Trigger created successfully!")

        # Verify the table was created
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'video_generation_jobs'
            ORDER BY ordinal_position;
        """))

        columns = result.fetchall()
        print("\n" + "="*60)
        print("Table structure for 'video_generation_jobs':")
        print("="*60)
        for col_name, col_type, nullable in columns:
            null_str = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"  {col_name:20s} {col_type:25s} {null_str}")
        print("="*60)

        # Check indexes
        result = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'video_generation_jobs';
        """))

        indexes = result.fetchall()
        print("\nIndexes:")
        for idx_name, idx_def in indexes:
            print(f"  ✓ {idx_name}")

        print("\n✅ Video generation schema setup complete!")

except Exception as e:
    print(f"✗ Error setting up schema: {e}")
    import traceback
    traceback.print_exc()
