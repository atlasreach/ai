-- ============================================================
-- MULTI-PERSONA CONTENT FACTORY - DATABASE SCHEMA
-- Option B: Face Swapping for Unique Personas
-- ============================================================

-- ============================================================
-- MODELS (Trained LoRAs)
-- One model = one trained face (e.g., "Skyler", "Emily")
-- ============================================================
CREATE TABLE IF NOT EXISTS models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Basic info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    thumbnail_url TEXT,

    -- Training info
    training_status VARCHAR(50) DEFAULT 'not_started', -- 'not_started', 'training', 'complete'
    lora_url TEXT, -- Hugging Face URL or local path after training
    lora_trigger_word VARCHAR(100), -- e.g., "skyler_face" - used in prompts
    training_notes TEXT, -- User notes about training params, date, etc.

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- REFERENCE LIBRARIES (Shared by Niche)
-- Organized by niche (Gaming, Fitness, Yoga, etc.)
-- Reusable across all models and personas
-- ============================================================
CREATE TABLE IF NOT EXISTS reference_libraries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    name VARCHAR(255) NOT NULL, -- "Gaming Poses Library", "Fitness Influencer Library"
    niche VARCHAR(100) NOT NULL, -- 'Gaming', 'Fitness', 'Yoga', 'Fashion', 'Travel'
    description TEXT,
    thumbnail_url TEXT,

    -- Stats (auto-updated)
    image_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- REFERENCE IMAGES
-- Individual images in reference libraries
-- Used as img2img references for generation
-- ============================================================
CREATE TABLE IF NOT EXISTS reference_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    library_id UUID NOT NULL REFERENCES reference_libraries(id) ON DELETE CASCADE,

    -- Image data
    image_url TEXT NOT NULL, -- Supabase storage URL
    thumbnail_url TEXT,
    caption TEXT, -- Grok-generated caption or manual description

    -- Metadata
    width INTEGER,
    height INTEGER,
    source VARCHAR(50), -- 'instagram', 'upload', 'playground'
    source_url TEXT, -- Original Instagram post URL if scraped
    source_instagram_username VARCHAR(255), -- Where it was scraped from

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- PERSONAS (Model + Target Face + Niche + Instagram)
-- THE CORE OF OPTION B
-- Each persona = unique Instagram identity with face-swapped content
-- ============================================================
CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    name VARCHAR(255) NOT NULL, -- 'SkylerGamerGirl', 'EmilyFitness'
    description TEXT,
    niche VARCHAR(100), -- Duplicate from library for quick filtering
    thumbnail_url TEXT,

    -- Core relationships
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE, -- Base model for generation
    reference_library_id UUID REFERENCES reference_libraries(id) ON DELETE SET NULL, -- Poses to use

    -- FACE SWAPPING (Option B)
    target_face_url TEXT NOT NULL, -- The face to swap to (REQUIRED!)
    target_face_thumbnail TEXT,
    target_face_name VARCHAR(255), -- e.g., "Edgy Gamer Face", "Athletic Fitness Face"

    -- Instagram integration
    instagram_username VARCHAR(255), -- @skyler_gamer
    instagram_bio TEXT,
    instagram_connected BOOLEAN DEFAULT false,

    -- Generation defaults (used as starting point for this persona)
    default_prompt_prefix TEXT, -- e.g., "gaming setup, RGB lighting, "
    default_negative_prompt TEXT,
    default_strength DECIMAL(3,2) DEFAULT 0.75, -- img2img strength

    -- Stats (auto-updated)
    total_generated INTEGER DEFAULT 0,
    total_posted INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TRAINING DATASETS (For training models)
-- Images used to train the base LoRAs
-- Separate from reference libraries
-- ============================================================
CREATE TABLE IF NOT EXISTS training_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Stats
    image_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TRAINING IMAGES
-- Individual images in training datasets
-- ============================================================
CREATE TABLE IF NOT EXISTS training_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES training_datasets(id) ON DELETE CASCADE,

    -- Image data
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    caption TEXT, -- Grok-generated caption for training

    -- Metadata
    width INTEGER,
    height INTEGER,
    source VARCHAR(50), -- 'instagram', 'upload'

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- GENERATED CONTENT
-- All images generated by the system
-- Stores BOTH base generation and face-swapped result
-- ============================================================
CREATE TABLE IF NOT EXISTS generated_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,

    -- Reference used
    reference_image_id UUID REFERENCES reference_images(id) ON DELETE SET NULL,

    -- Generation results (Option B: stores both steps)
    base_image_url TEXT, -- Generated with base model (before face swap)
    final_image_url TEXT NOT NULL, -- After face swap (what gets posted)
    thumbnail_url TEXT,

    -- Generation parameters
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    strength DECIMAL(3,2), -- img2img strength
    seed INTEGER,
    steps INTEGER,
    cfg_scale DECIMAL(4,2),

    -- Publishing workflow
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'scheduled', 'posted', 'deleted'
    scheduled_at TIMESTAMP,
    posted_at TIMESTAMP,
    instagram_post_id VARCHAR(255), -- ID after posting
    instagram_caption TEXT,
    instagram_hashtags TEXT, -- Space-separated hashtags

    -- Metadata
    width INTEGER,
    height INTEGER,
    generation_time_ms INTEGER,
    face_swap_time_ms INTEGER,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- UPDATE EXISTING TABLES
-- Link instagram_accounts to personas
-- ============================================================
ALTER TABLE instagram_accounts
ADD COLUMN IF NOT EXISTS persona_id UUID REFERENCES personas(id) ON DELETE SET NULL;

-- Add comment for clarity
COMMENT ON COLUMN instagram_accounts.persona_id IS 'Links scraped Instagram account to a persona for reference library building';

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

-- Models
CREATE INDEX IF NOT EXISTS idx_models_training_status ON models(training_status);

-- Reference libraries
CREATE INDEX IF NOT EXISTS idx_reference_libraries_niche ON reference_libraries(niche);

-- Reference images
CREATE INDEX IF NOT EXISTS idx_reference_images_library_id ON reference_images(library_id);
CREATE INDEX IF NOT EXISTS idx_reference_images_source ON reference_images(source);

-- Personas
CREATE INDEX IF NOT EXISTS idx_personas_model_id ON personas(model_id);
CREATE INDEX IF NOT EXISTS idx_personas_library_id ON personas(reference_library_id);
CREATE INDEX IF NOT EXISTS idx_personas_niche ON personas(niche);
CREATE INDEX IF NOT EXISTS idx_personas_instagram_username ON personas(instagram_username);

-- Training datasets
CREATE INDEX IF NOT EXISTS idx_training_datasets_model_id ON training_datasets(model_id);

-- Training images
CREATE INDEX IF NOT EXISTS idx_training_images_dataset_id ON training_images(dataset_id);

-- Generated content
CREATE INDEX IF NOT EXISTS idx_generated_content_persona_id ON generated_content(persona_id);
CREATE INDEX IF NOT EXISTS idx_generated_content_status ON generated_content(status);
CREATE INDEX IF NOT EXISTS idx_generated_content_scheduled_at ON generated_content(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_generated_content_created_at ON generated_content(created_at);

-- Instagram accounts
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_persona_id ON instagram_accounts(persona_id);

-- ============================================================
-- FUNCTIONS FOR AUTO-UPDATING STATS
-- ============================================================

-- Update reference library image count
CREATE OR REPLACE FUNCTION update_reference_library_image_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE reference_libraries
        SET image_count = image_count + 1
        WHERE id = NEW.library_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE reference_libraries
        SET image_count = image_count - 1
        WHERE id = OLD.library_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_reference_library_image_count
AFTER INSERT OR DELETE ON reference_images
FOR EACH ROW EXECUTE FUNCTION update_reference_library_image_count();

-- Update training dataset image count
CREATE OR REPLACE FUNCTION update_training_dataset_image_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE training_datasets
        SET image_count = image_count + 1
        WHERE id = NEW.dataset_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE training_datasets
        SET image_count = image_count - 1
        WHERE id = OLD.dataset_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_training_dataset_image_count
AFTER INSERT OR DELETE ON training_images
FOR EACH ROW EXECUTE FUNCTION update_training_dataset_image_count();

-- Update persona stats when content is generated
CREATE OR REPLACE FUNCTION update_persona_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE personas
        SET total_generated = total_generated + 1
        WHERE id = NEW.persona_id;

        IF NEW.status = 'posted' THEN
            UPDATE personas
            SET total_posted = total_posted + 1
            WHERE id = NEW.persona_id;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status != 'posted' AND NEW.status = 'posted' THEN
            UPDATE personas
            SET total_posted = total_posted + 1
            WHERE id = NEW.persona_id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE personas
        SET total_generated = total_generated - 1
        WHERE id = OLD.persona_id;

        IF OLD.status = 'posted' THEN
            UPDATE personas
            SET total_posted = total_posted - 1
            WHERE id = OLD.persona_id;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_persona_stats
AFTER INSERT OR UPDATE OR DELETE ON generated_content
FOR EACH ROW EXECUTE FUNCTION update_persona_stats();

-- ============================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================

COMMENT ON TABLE models IS 'Trained LoRA models - one per person/face';
COMMENT ON TABLE reference_libraries IS 'Shared collections of reference images organized by niche';
COMMENT ON TABLE reference_images IS 'Individual reference images used for img2img generation';
COMMENT ON TABLE personas IS 'Unique Instagram identities - links model + target face + niche + account';
COMMENT ON TABLE training_datasets IS 'Image collections used to train LoRA models';
COMMENT ON TABLE training_images IS 'Individual images in training datasets';
COMMENT ON TABLE generated_content IS 'All generated images with both base and face-swapped results';

COMMENT ON COLUMN personas.target_face_url IS 'CRITICAL: The face to swap to after generation (Option B)';
COMMENT ON COLUMN generated_content.base_image_url IS 'Image generated with base model before face swap';
COMMENT ON COLUMN generated_content.final_image_url IS 'Image after face swap - this is what gets posted';
