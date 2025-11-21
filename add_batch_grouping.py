from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the direct connection URL
direct_url = os.getenv('DIRECT_URL')

if not direct_url:
    print("❌ DIRECT_URL not found in .env file!")
    exit(1)

# Create engine
engine = create_engine(direct_url)

print('🚀 Adding batch_id columns for grouping variations...\n')

migration_sql = """
-- Add batch_id to generation_jobs
ALTER TABLE generation_jobs
ADD COLUMN IF NOT EXISTS batch_id TEXT;

-- Add batch_id to generated_images
ALTER TABLE generated_images
ADD COLUMN IF NOT EXISTS batch_id TEXT;

-- Create index for batch queries
CREATE INDEX IF NOT EXISTS idx_generation_jobs_batch ON generation_jobs(batch_id);
CREATE INDEX IF NOT EXISTS idx_generated_images_batch ON generated_images(batch_id);
"""

try:
    with engine.connect() as conn:
        print('Adding batch_id columns...')
        conn.execute(text(migration_sql))
        conn.commit()
        print('✅ Migration completed successfully!')

        # Verify columns were added
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'generation_jobs' AND column_name = 'batch_id';
        """))

        if result.fetchone():
            print('✅ batch_id column added to generation_jobs')

        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'generated_images' AND column_name = 'batch_id';
        """))

        if result.fetchone():
            print('✅ batch_id column added to generated_images')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
