-- Create sub-models, content types, and face swap tables

-- Sub-models table (e.g., Hazel Ray for Milan)
-- Each main model can have multiple sub-models with different faces
CREATE TABLE IF NOT EXISTS sub_models (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    face_image_url TEXT,  -- Face image for Replicate face swap API
    fanhub_account VARCHAR(100),  -- Single FanVue account for this sub-model
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Content types table (e.g., Bikini, Lingerie, Fitness)
-- Each sub-model can have multiple content types, each with its own Instagram
CREATE TABLE IF NOT EXISTS content_types (
    id SERIAL PRIMARY KEY,
    sub_model_id INTEGER REFERENCES sub_models(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,  -- Bikini, Lingerie, Fitness, etc.
    instagram_account VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Face swap tracking table
-- Tracks when a generated image gets face-swapped using Replicate API
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

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sub_models_model ON sub_models(model_id);
CREATE INDEX IF NOT EXISTS idx_content_types_sub_model ON content_types(sub_model_id);
CREATE INDEX IF NOT EXISTS idx_face_swaps_job ON face_swaps(original_job_id);
CREATE INDEX IF NOT EXISTS idx_face_swaps_status ON face_swaps(status);

-- Example data (commented out - run manually if needed)
-- INSERT INTO sub_models (model_id, name, face_image_url, fanhub_account, description)
-- VALUES (1, 'Hazel Ray', 'https://example.com/hazel-face.jpg', '@hazelray', 'Milan sub-model 1');
--
-- INSERT INTO content_types (sub_model_id, name, instagram_account, description)
-- VALUES
--   (1, 'Bikini', '@hazelray_bikini', 'Beach and bikini content'),
--   (1, 'Lingerie', '@hazelray_lingerie', 'Intimate apparel content'),
--   (1, 'Fitness', '@hazelray_fitness', 'Workout and gym content');
