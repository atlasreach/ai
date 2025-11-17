-- ============================================================================
-- Database Migration: New Model/Dataset Schema
-- Creates new structure for models with multiple datasets and LoRA tracking
-- ============================================================================

-- Step 1: Backup existing tables (if they exist)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'characters') THEN
        DROP TABLE IF EXISTS characters_old_backup CASCADE;
        ALTER TABLE characters RENAME TO characters_old_backup;
        RAISE NOTICE 'Backed up characters → characters_old_backup';
    END IF;

    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'training_datasets') THEN
        DROP TABLE IF EXISTS training_datasets_old_backup CASCADE;
        ALTER TABLE training_datasets RENAME TO training_datasets_old_backup;
        RAISE NOTICE 'Backed up training_datasets → training_datasets_old_backup';
    END IF;

    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'training_images') THEN
        DROP TABLE IF EXISTS training_images_old_backup CASCADE;
        ALTER TABLE training_images RENAME TO training_images_old_backup;
        RAISE NOTICE 'Backed up training_images → training_images_old_backup';
    END IF;
END $$;

-- Step 2: Create new models table
CREATE TABLE IF NOT EXISTS models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    trigger_word TEXT NOT NULL,
    defining_features JSONB DEFAULT '{}'::jsonb,
    huggingface_repo TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_models_name ON models(name);
CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active);

-- Step 3: Create new datasets table
CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES models(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    dataset_type TEXT CHECK (dataset_type IN ('SFW', 'NSFW')),
    description TEXT,
    image_count INTEGER DEFAULT 0,

    -- Training info (filled after manual training)
    lora_filename TEXT,
    huggingface_url TEXT,
    training_notes TEXT,
    training_status TEXT DEFAULT 'preparing' CHECK (
        training_status IN ('preparing', 'ready_to_train', 'training', 'trained')
    ),

    -- Metadata
    storage_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(model_id, name)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_datasets_model ON datasets(model_id);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(training_status);
CREATE INDEX IF NOT EXISTS idx_datasets_lora ON datasets(lora_filename);

-- Step 4: Create dataset_images table
CREATE TABLE IF NOT EXISTS dataset_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    caption TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    display_order INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(dataset_id, display_order)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_dataset_images_dataset ON dataset_images(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dataset_images_order ON dataset_images(dataset_id, display_order);

-- Step 5: Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for models
DROP TRIGGER IF EXISTS update_models_updated_at ON models;
CREATE TRIGGER update_models_updated_at
    BEFORE UPDATE ON models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for datasets
DROP TRIGGER IF EXISTS update_datasets_updated_at ON datasets;
CREATE TRIGGER update_datasets_updated_at
    BEFORE UPDATE ON datasets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Step 6: Enable Row Level Security
ALTER TABLE models ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dataset_images ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for now, can be restricted later)
DROP POLICY IF EXISTS "Enable all access for models" ON models;
CREATE POLICY "Enable all access for models" ON models FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Enable all access for datasets" ON datasets;
CREATE POLICY "Enable all access for datasets" ON datasets FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Enable all access for dataset_images" ON dataset_images;
CREATE POLICY "Enable all access for dataset_images" ON dataset_images FOR ALL USING (true) WITH CHECK (true);

-- ============================================================================
-- Migration complete!
-- New schema:
--   - models (id, name, trigger_word, defining_features, huggingface_repo)
--   - datasets (id, model_id, name, type, lora_filename, huggingface_url, training_notes)
--   - dataset_images (id, dataset_id, image_url, caption)
--
-- Old tables backed up as:
--   - characters_old_backup
--   - training_datasets_old_backup
--   - training_images_old_backup
-- ============================================================================
