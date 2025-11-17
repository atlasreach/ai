-- ============================================================
-- SAFE MIGRATION: Update existing schema for persona system
-- ============================================================

-- ============================================================
-- UPDATE EXISTING MODELS TABLE
-- Add new columns needed for persona system
-- ============================================================

ALTER TABLE models
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT,
ADD COLUMN IF NOT EXISTS training_status VARCHAR(50) DEFAULT 'complete', -- Existing models are complete
ADD COLUMN IF NOT EXISTS lora_url TEXT,
ADD COLUMN IF NOT EXISTS lora_trigger_word VARCHAR(100),
ADD COLUMN IF NOT EXISTS training_notes TEXT;

-- Populate lora_url from existing huggingface_repo
UPDATE models
SET lora_url = huggingface_repo
WHERE lora_url IS NULL AND huggingface_repo IS NOT NULL;

-- Populate lora_trigger_word from existing trigger_word
UPDATE models
SET lora_trigger_word = trigger_word
WHERE lora_trigger_word IS NULL AND trigger_word IS NOT NULL;

-- ============================================================
-- REFERENCE LIBRARIES (New)
-- ============================================================
CREATE TABLE IF NOT EXISTS reference_libraries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    niche VARCHAR(100) NOT NULL,
    description TEXT,
    thumbnail_url TEXT,
    image_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- REFERENCE IMAGES (New)
-- ============================================================
CREATE TABLE IF NOT EXISTS reference_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    library_id UUID NOT NULL REFERENCES reference_libraries(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    caption TEXT,
    width INTEGER,
    height INTEGER,
    source VARCHAR(50),
    source_url TEXT,
    source_instagram_username VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- PERSONAS (New)
-- ============================================================
CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    niche VARCHAR(100),
    thumbnail_url TEXT,

    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    reference_library_id UUID REFERENCES reference_libraries(id) ON DELETE SET NULL,

    -- Face swapping (Option B)
    target_face_url TEXT NOT NULL,
    target_face_thumbnail TEXT,
    target_face_name VARCHAR(255),

    -- Instagram integration
    instagram_username VARCHAR(255),
    instagram_bio TEXT,
    instagram_connected BOOLEAN DEFAULT false,

    -- Generation defaults
    default_prompt_prefix TEXT,
    default_negative_prompt TEXT,
    default_strength DECIMAL(3,2) DEFAULT 0.75,

    -- Stats
    total_generated INTEGER DEFAULT 0,
    total_posted INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TRAINING DATASETS (New)
-- ============================================================
CREATE TABLE IF NOT EXISTS training_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TRAINING IMAGES (New)
-- ============================================================
CREATE TABLE IF NOT EXISTS training_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES training_datasets(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    caption TEXT,
    width INTEGER,
    height INTEGER,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- GENERATED CONTENT (New)
-- ============================================================
CREATE TABLE IF NOT EXISTS generated_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,

    reference_image_id UUID REFERENCES reference_images(id) ON DELETE SET NULL,

    base_image_url TEXT,
    final_image_url TEXT NOT NULL,
    thumbnail_url TEXT,

    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    strength DECIMAL(3,2),
    seed INTEGER,
    steps INTEGER,
    cfg_scale DECIMAL(4,2),

    status VARCHAR(50) DEFAULT 'draft',
    scheduled_at TIMESTAMP,
    posted_at TIMESTAMP,
    instagram_post_id VARCHAR(255),
    instagram_caption TEXT,
    instagram_hashtags TEXT,

    width INTEGER,
    height INTEGER,
    generation_time_ms INTEGER,
    face_swap_time_ms INTEGER,

    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- UPDATE EXISTING INSTAGRAM_ACCOUNTS TABLE
-- ============================================================
ALTER TABLE instagram_accounts
ADD COLUMN IF NOT EXISTS persona_id UUID REFERENCES personas(id) ON DELETE SET NULL;

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_models_training_status ON models(training_status);

CREATE INDEX IF NOT EXISTS idx_reference_libraries_niche ON reference_libraries(niche);

CREATE INDEX IF NOT EXISTS idx_reference_images_library_id ON reference_images(library_id);
CREATE INDEX IF NOT EXISTS idx_reference_images_source ON reference_images(source);

CREATE INDEX IF NOT EXISTS idx_personas_model_id ON personas(model_id);
CREATE INDEX IF NOT EXISTS idx_personas_library_id ON personas(reference_library_id);
CREATE INDEX IF NOT EXISTS idx_personas_niche ON personas(niche);
CREATE INDEX IF NOT EXISTS idx_personas_instagram_username ON personas(instagram_username);

CREATE INDEX IF NOT EXISTS idx_training_datasets_model_id ON training_datasets(model_id);
CREATE INDEX IF NOT EXISTS idx_training_images_dataset_id ON training_images(dataset_id);

CREATE INDEX IF NOT EXISTS idx_generated_content_persona_id ON generated_content(persona_id);
CREATE INDEX IF NOT EXISTS idx_generated_content_status ON generated_content(status);
CREATE INDEX IF NOT EXISTS idx_generated_content_scheduled_at ON generated_content(scheduled_at);

CREATE INDEX IF NOT EXISTS idx_instagram_accounts_persona_id ON instagram_accounts(persona_id);

-- ============================================================
-- TRIGGERS FOR AUTO-UPDATING STATS
-- ============================================================

-- Reference library image count
CREATE OR REPLACE FUNCTION update_reference_library_image_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE reference_libraries SET image_count = image_count + 1 WHERE id = NEW.library_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE reference_libraries SET image_count = image_count - 1 WHERE id = OLD.library_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_reference_library_image_count ON reference_images;
CREATE TRIGGER trigger_update_reference_library_image_count
AFTER INSERT OR DELETE ON reference_images
FOR EACH ROW EXECUTE FUNCTION update_reference_library_image_count();

-- Training dataset image count
CREATE OR REPLACE FUNCTION update_training_dataset_image_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE training_datasets SET image_count = image_count + 1 WHERE id = NEW.dataset_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE training_datasets SET image_count = image_count - 1 WHERE id = OLD.dataset_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_training_dataset_image_count ON training_images;
CREATE TRIGGER trigger_update_training_dataset_image_count
AFTER INSERT OR DELETE ON training_images
FOR EACH ROW EXECUTE FUNCTION update_training_dataset_image_count();

-- Persona stats
CREATE OR REPLACE FUNCTION update_persona_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE personas SET total_generated = total_generated + 1 WHERE id = NEW.persona_id;
        IF NEW.status = 'posted' THEN
            UPDATE personas SET total_posted = total_posted + 1 WHERE id = NEW.persona_id;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status != 'posted' AND NEW.status = 'posted' THEN
            UPDATE personas SET total_posted = total_posted + 1 WHERE id = NEW.persona_id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE personas SET total_generated = total_generated - 1 WHERE id = OLD.persona_id;
        IF OLD.status = 'posted' THEN
            UPDATE personas SET total_posted = total_posted - 1 WHERE id = OLD.persona_id;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_persona_stats ON generated_content;
CREATE TRIGGER trigger_update_persona_stats
AFTER INSERT OR UPDATE OR DELETE ON generated_content
FOR EACH ROW EXECUTE FUNCTION update_persona_stats();
