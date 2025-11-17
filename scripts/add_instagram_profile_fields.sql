-- Add missing Instagram profile fields

-- Add new columns if they don't exist
ALTER TABLE instagram_accounts
ADD COLUMN IF NOT EXISTS external_url TEXT,
ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_business BOOLEAN DEFAULT false;

-- Rename follower_count to followers_count for consistency
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'instagram_accounts' AND column_name = 'follower_count'
    ) THEN
        ALTER TABLE instagram_accounts RENAME COLUMN follower_count TO followers_count;
    END IF;
END $$;
