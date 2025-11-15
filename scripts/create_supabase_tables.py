#!/usr/bin/env python3
"""
Create training_datasets and training_images tables in Supabase
"""
import os
from supabase import create_client

# Get Supabase credentials from environment
SUPABASE_URL = "https://yiriqesejsbzmzxdxiqt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlpcmlxZXNlanNiem16eGR4aXF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzE1MDYyNSwiZXhwIjoyMDc4NzI2NjI1fQ.LLah2N2LWA-yktnKRyVRi_JZLuL-frIWXJPQDdkEQdI"

print("📊 Creating tables in Supabase...")

sql = """
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_training_datasets_character_id ON training_datasets(character_id);
CREATE INDEX IF NOT EXISTS idx_training_images_dataset_id ON training_images(dataset_id);

-- Enable RLS
ALTER TABLE training_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_images ENABLE ROW LEVEL SECURITY;

-- Create policies
DROP POLICY IF EXISTS "Enable read access for all users" ON training_datasets;
CREATE POLICY "Enable read access for all users" ON training_datasets FOR SELECT USING (true);

DROP POLICY IF EXISTS "Enable insert for authenticated users" ON training_datasets;
CREATE POLICY "Enable insert for authenticated users" ON training_datasets FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Enable update for authenticated users" ON training_datasets;
CREATE POLICY "Enable update for authenticated users" ON training_datasets FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Enable delete for authenticated users" ON training_datasets;
CREATE POLICY "Enable delete for authenticated users" ON training_datasets FOR DELETE USING (true);

DROP POLICY IF EXISTS "Enable read access for all users" ON training_images;
CREATE POLICY "Enable read access for all users" ON training_images FOR SELECT USING (true);

DROP POLICY IF EXISTS "Enable insert for authenticated users" ON training_images;
CREATE POLICY "Enable insert for authenticated users" ON training_images FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Enable update for authenticated users" ON training_images;
CREATE POLICY "Enable update for authenticated users" ON training_images FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Enable delete for authenticated users" ON training_images;
CREATE POLICY "Enable delete for authenticated users" ON training_images FOR DELETE USING (true);
"""

print("⚠️  Supabase Python client doesn't support raw SQL execution.")
print("📋 Please copy the SQL from scripts/create_supabase_tables.sql")
print("🌐 And paste it in your Supabase SQL Editor:")
print(f"   {SUPABASE_URL}/project/yiriqesejsbzmzxdxiqt/sql")
print("\nOr use psql if you have the database connection string.")
