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

print('🚀 Adding gallery action columns...\n')

migration_sql = """
-- Add action and tracking columns to generated_images
ALTER TABLE generated_images
ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS parent_image_id INTEGER REFERENCES generated_images(id),
ADD COLUMN IF NOT EXISTS edit_type TEXT,
ADD COLUMN IF NOT EXISTS face_swap_source TEXT;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_generated_images_starred ON generated_images(is_starred) WHERE is_starred = true;
CREATE INDEX IF NOT EXISTS idx_generated_images_deleted ON generated_images(is_deleted) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_generated_images_parent ON generated_images(parent_image_id);

-- Add comment to describe edit_type values
COMMENT ON COLUMN generated_images.edit_type IS 'Type of edit: original, face_swap, seed_dream_edit';
"""

try:
    with engine.connect() as conn:
        print('Adding columns...')
        conn.execute(text(migration_sql))
        conn.commit()
        print('✅ Migration completed successfully!')

        # Verify columns were added
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'generated_images'
            AND column_name IN ('is_starred', 'is_deleted', 'parent_image_id', 'edit_type', 'face_swap_source')
            ORDER BY column_name;
        """))

        columns = result.fetchall()
        print('\n✅ Columns added:')
        for col_name, col_type, nullable in columns:
            print(f'  - {col_name}: {col_type} (nullable: {nullable})')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
