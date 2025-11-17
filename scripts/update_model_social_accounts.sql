-- Add social account fields to models table (for scraping training data)
ALTER TABLE models
ADD COLUMN IF NOT EXISTS instagram_username VARCHAR(255),
ADD COLUMN IF NOT EXISTS tiktok_username VARCHAR(255),
ADD COLUMN IF NOT EXISTS onlyfans_username VARCHAR(255);

-- Add social account fields to personas table (for posting generated content)
ALTER TABLE personas
ADD COLUMN IF NOT EXISTS tiktok_username VARCHAR(255),
ADD COLUMN IF NOT EXISTS onlyfans_username VARCHAR(255);

-- Update persona table to make target_face_url NOT NULL constraint more flexible
-- (We'll handle this in the app logic for now)

-- Add comments
COMMENT ON COLUMN models.instagram_username IS 'Instagram account to scrape training data from';
COMMENT ON COLUMN models.tiktok_username IS 'TikTok account to scrape training data from';
COMMENT ON COLUMN models.onlyfans_username IS 'OnlyFans account to scrape training data from';

COMMENT ON COLUMN personas.instagram_username IS 'Instagram account to post generated content to';
COMMENT ON COLUMN personas.tiktok_username IS 'TikTok account to post generated content to';
COMMENT ON COLUMN personas.onlyfans_username IS 'OnlyFans account to post generated content to';
