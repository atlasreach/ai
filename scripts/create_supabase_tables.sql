-- Create training_datasets table
CREATE TABLE IF NOT EXISTS training_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    dataset_type TEXT NOT NULL CHECK (dataset_type IN ('SFW', 'NSFW')),
    description TEXT,
    dataset_constraints JSONB DEFAULT '{}',
    image_count INTEGER DEFAULT 0,
    storage_url TEXT,
    lora_file TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create training_images table
CREATE TABLE IF NOT EXISTS training_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES training_datasets(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    caption TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_training_datasets_character_id ON training_datasets(character_id);
CREATE INDEX IF NOT EXISTS idx_training_images_dataset_id ON training_images(dataset_id);

-- Enable RLS (Row Level Security)
ALTER TABLE training_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_images ENABLE ROW LEVEL SECURITY;

-- Create policies for public access (adjust as needed)
CREATE POLICY "Enable read access for all users" ON training_datasets FOR SELECT USING (true);
CREATE POLICY "Enable insert for authenticated users" ON training_datasets FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for authenticated users" ON training_datasets FOR UPDATE USING (true);
CREATE POLICY "Enable delete for authenticated users" ON training_datasets FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON training_images FOR SELECT USING (true);
CREATE POLICY "Enable insert for authenticated users" ON training_images FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for authenticated users" ON training_images FOR UPDATE USING (true);
CREATE POLICY "Enable delete for authenticated users" ON training_images FOR DELETE USING (true);
