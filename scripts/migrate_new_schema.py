"""
Database Migration: New Model/Dataset Schema
Creates new structure for models with multiple datasets and LoRA tracking
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_migration():
    print("🔄 Starting database migration...")

    # Step 1: Rename old tables if they exist (backup)
    print("\n📦 Step 1: Backing up old tables...")
    backup_queries = [
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'characters') THEN
                ALTER TABLE IF EXISTS characters RENAME TO characters_old_backup;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'training_datasets') THEN
                ALTER TABLE IF EXISTS training_datasets RENAME TO training_datasets_old_backup;
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'training_images') THEN
                ALTER TABLE IF EXISTS training_images RENAME TO training_images_old_backup;
            END IF;
        END $$;
        """
    ]

    for query in backup_queries:
        try:
            supabase.rpc('exec_sql', {'sql': query}).execute()
            print("  ✓ Backup query executed")
        except Exception as e:
            print(f"  ℹ️  Backup note: {str(e)[:100]}")

    # Step 2: Create new models table
    print("\n📋 Step 2: Creating 'models' table...")
    models_table = """
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

    -- Add index for faster lookups
    CREATE INDEX IF NOT EXISTS idx_models_name ON models(name);
    CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active);
    """

    try:
        supabase.rpc('exec_sql', {'sql': models_table}).execute()
        print("  ✓ Models table created")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

    # Step 3: Create new datasets table
    print("\n📁 Step 3: Creating 'datasets' table...")
    datasets_table = """
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
    """

    try:
        supabase.rpc('exec_sql', {'sql': datasets_table}).execute()
        print("  ✓ Datasets table created")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

    # Step 4: Create dataset_images table
    print("\n🖼️  Step 4: Creating 'dataset_images' table...")
    images_table = """
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
    """

    try:
        supabase.rpc('exec_sql', {'sql': images_table}).execute()
        print("  ✓ Dataset images table created")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

    # Step 5: Create update trigger for updated_at
    print("\n⏰ Step 5: Creating timestamp triggers...")
    trigger_sql = """
    -- Function to update updated_at timestamp
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
    """

    try:
        supabase.rpc('exec_sql', {'sql': trigger_sql}).execute()
        print("  ✓ Timestamp triggers created")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

    # Step 6: Enable RLS
    print("\n🔒 Step 6: Enabling Row Level Security...")
    rls_sql = """
    -- Enable RLS
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
    """

    try:
        supabase.rpc('exec_sql', {'sql': rls_sql}).execute()
        print("  ✓ RLS enabled with open policies")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

    print("\n✅ Migration complete!")
    print("\n📊 New schema:")
    print("  - models (id, name, trigger_word, defining_features, huggingface_repo)")
    print("  - datasets (id, model_id, name, type, lora_filename, huggingface_url, training_notes)")
    print("  - dataset_images (id, dataset_id, image_url, caption)")
    print("\n💡 Old tables backed up as: characters_old_backup, training_datasets_old_backup, training_images_old_backup")

if __name__ == "__main__":
    print("=" * 60)
    print("  DATABASE MIGRATION: New Model/Dataset Schema")
    print("=" * 60)

    response = input("\n⚠️  This will restructure your database. Continue? (yes/no): ")

    if response.lower() == 'yes':
        run_migration()
    else:
        print("❌ Migration cancelled")
