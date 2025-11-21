import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import axios from 'axios'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

console.log('🚀 Running database migration...\n')

// Use Supabase Management API to run SQL
const SUPABASE_PROJECT_REF = process.env.SUPABASE_URL.match(/https:\/\/(.+?)\.supabase\.co/)[1]
const SUPABASE_ACCESS_TOKEN = process.env.SUPABASE_SERVICE_ROLE_KEY

const sql = `
-- Sub-models table
CREATE TABLE IF NOT EXISTS sub_models (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    face_image_url TEXT,
    fanhub_account VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Content types table
CREATE TABLE IF NOT EXISTS content_types (
    id SERIAL PRIMARY KEY,
    sub_model_id INTEGER REFERENCES sub_models(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    instagram_account VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Face swap tracking table
CREATE TABLE IF NOT EXISTS face_swaps (
    id SERIAL PRIMARY KEY,
    original_job_id INTEGER REFERENCES generation_jobs(id) ON DELETE CASCADE,
    sub_model_id INTEGER REFERENCES sub_models(id),
    replicate_job_id VARCHAR(200),
    swapped_image_url TEXT,
    status VARCHAR(50) DEFAULT 'processing',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Add new columns to generation_jobs table
ALTER TABLE generation_jobs
ADD COLUMN IF NOT EXISTS face_swap_id INTEGER REFERENCES face_swaps(id),
ADD COLUMN IF NOT EXISTS content_type_id INTEGER REFERENCES content_types(id);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_sub_models_model ON sub_models(model_id);
CREATE INDEX IF NOT EXISTS idx_content_types_sub_model ON content_types(sub_model_id);
CREATE INDEX IF NOT EXISTS idx_face_swaps_job ON face_swaps(original_job_id);
CREATE INDEX IF NOT EXISTS idx_face_swaps_status ON face_swaps(status);
`

try {
  const response = await axios.post(
    `https://${SUPABASE_PROJECT_REF}.supabase.co/rest/v1/rpc/sql`,
    { query: sql },
    {
      headers: {
        'apikey': SUPABASE_ACCESS_TOKEN,
        'Authorization': `Bearer ${SUPABASE_ACCESS_TOKEN}`,
        'Content-Type': 'application/json'
      }
    }
  )

  console.log('✅ Migration successful!')
} catch (error) {
  console.error('❌ Migration failed:', error.response?.data || error.message)
  console.log('\n📝 Fallback: Copy SQL from /workspaces/ai/sql/02_sub_models_schema.sql and run it manually in Supabase SQL Editor')
}

// Create storage bucket
console.log('\n📦 Creating Supabase Storage bucket for face images...')

try {
  const { data: buckets } = await supabase.storage.listBuckets()
  const bucketExists = buckets?.some(b => b.name === 'face-images')

  if (!bucketExists) {
    const { data, error } = await supabase.storage.createBucket('face-images', {
      public: true,
      fileSizeLimit: 52428800 // 50MB
    })

    if (error) {
      console.log('⚠️  Bucket creation failed:', error.message)
    } else {
      console.log('✅ Created face-images bucket')
    }
  } else {
    console.log('✅ face-images bucket already exists')
  }
} catch (bucketError) {
  console.log('⚠️  Bucket check failed:', bucketError.message)
}

console.log('\n✨ Migration complete!')
