from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the direct connection URL
direct_url = os.getenv('DIRECT_URL')

if not direct_url:
    print("❌ DIRECT_URL not found in .env file!")
    print("Add it from Supabase Dashboard → Settings → Database → Connection String (port 5432)")
    exit(1)

# Create engine
engine = create_engine(direct_url)

print('🚀 Creating generated_images table...\n')

# Drop and recreate table
create_table_sql = """
-- Drop existing table if needed
DROP TABLE IF EXISTS generated_images CASCADE;

-- Create generated_images table for final gallery catalog
CREATE TABLE generated_images (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES generation_jobs(id) ON DELETE CASCADE,
    model_id INTEGER REFERENCES models(id),
    reference_image_id INTEGER REFERENCES reference_images(id),

    -- Image storage
    image_url TEXT NOT NULL,
    storage_path TEXT,

    -- Generation metadata (embedded for fast queries)
    prompt_used TEXT,
    negative_prompt_used TEXT,
    parameters JSONB,

    -- Model info (denormalized for Gallery performance)
    model_name TEXT,
    model_slug TEXT,

    -- Reference image info (denormalized)
    reference_filename TEXT,
    reference_caption TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    generated_at TIMESTAMP,

    -- Optional face swap reference
    face_swap_id INTEGER REFERENCES face_swaps(id)
);

-- Indexes for performance
CREATE INDEX idx_generated_images_model ON generated_images(model_id);
CREATE INDEX idx_generated_images_reference ON generated_images(reference_image_id);
CREATE INDEX idx_generated_images_created ON generated_images(created_at DESC);
CREATE INDEX idx_generated_images_job ON generated_images(job_id);
"""

backfill_sql = """
-- Backfill existing completed jobs
INSERT INTO generated_images (
    job_id,
    model_id,
    reference_image_id,
    image_url,
    storage_path,
    prompt_used,
    negative_prompt_used,
    parameters,
    model_name,
    model_slug,
    reference_filename,
    reference_caption,
    generated_at,
    created_at
)
SELECT
    j.id as job_id,
    j.model_id,
    j.reference_image_id,
    j.result_image_url as image_url,
    SUBSTRING(j.result_image_url FROM '.*/([^/]+)$') as storage_path,
    j.prompt_used,
    j.negative_prompt_used,
    j.parameters,
    m.name as model_name,
    m.slug as model_slug,
    r.filename as reference_filename,
    r.vision_description as reference_caption,
    j.completed_at as generated_at,
    j.created_at
FROM generation_jobs j
LEFT JOIN models m ON j.model_id = m.id
LEFT JOIN reference_images r ON j.reference_image_id = r.id
WHERE j.status = 'completed'
  AND j.result_image_url IS NOT NULL;
"""

try:
    with engine.connect() as conn:
        # Create the table
        print('Step 1: Creating table structure...')
        conn.execute(text(create_table_sql))
        conn.commit()
        print('✅ Table created successfully!')

        # Backfill existing data
        print('\nStep 2: Backfilling existing completed jobs...')
        result = conn.execute(text(backfill_sql))
        conn.commit()
        row_count = result.rowcount
        print(f'✅ Inserted {row_count} existing images')

        # Verify the table
        print('\nStep 3: Verifying table structure...')
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'generated_images'
            ORDER BY ordinal_position;
        """))

        columns = result.fetchall()
        print('\nTable columns:')
        for col_name, col_type in columns:
            print(f'  - {col_name}: {col_type}')

        # Count rows
        result = conn.execute(text("SELECT COUNT(*) FROM generated_images"))
        count = result.scalar()
        print(f'\n✨ Total images in gallery: {count}')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
