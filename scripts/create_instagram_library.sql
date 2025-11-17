-- ============================================================================
-- Instagram Library Schema
-- Store scraped Instagram accounts and posts separately
-- ============================================================================

-- 1. Instagram Accounts Table
CREATE TABLE IF NOT EXISTS instagram_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    full_name TEXT,
    profile_pic_url TEXT,
    bio TEXT,

    -- Stats
    follower_count INTEGER,
    following_count INTEGER,
    post_count INTEGER,

    -- Scraping info
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    total_posts_scraped INTEGER DEFAULT 0,
    scrape_status TEXT DEFAULT 'complete' CHECK (
        scrape_status IN ('pending', 'scraping', 'complete', 'error')
    ),

    -- Organization
    tags TEXT[],
    notes TEXT,
    is_favorite BOOLEAN DEFAULT false,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_instagram_accounts_username ON instagram_accounts(username);
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_favorite ON instagram_accounts(is_favorite);
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_tags ON instagram_accounts USING GIN(tags);


-- 2. Instagram Posts Table
CREATE TABLE IF NOT EXISTS instagram_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES instagram_accounts(id) ON DELETE CASCADE,

    -- Instagram data
    instagram_id TEXT UNIQUE NOT NULL,
    post_type TEXT,                          -- 'Image', 'Video', 'Sidecar'
    short_code TEXT,
    post_url TEXT,

    -- Media
    display_url TEXT,
    media_urls JSONB DEFAULT '[]'::jsonb,    -- Array of image URLs for carousels
    video_url TEXT,

    -- Content
    caption TEXT,
    hashtags TEXT[],

    -- Engagement
    likes_count INTEGER,
    comments_count INTEGER,
    views_count INTEGER,

    -- Timestamps
    posted_at TIMESTAMP WITH TIME ZONE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Extra data
    metadata JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_instagram_posts_account ON instagram_posts(account_id);
CREATE INDEX IF NOT EXISTS idx_instagram_posts_type ON instagram_posts(post_type);
CREATE INDEX IF NOT EXISTS idx_instagram_posts_posted ON instagram_posts(posted_at DESC);


-- Update trigger for instagram_accounts
DROP TRIGGER IF EXISTS update_instagram_accounts_updated_at ON instagram_accounts;
CREATE TRIGGER update_instagram_accounts_updated_at
    BEFORE UPDATE ON instagram_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- Enable RLS
ALTER TABLE instagram_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE instagram_posts ENABLE ROW LEVEL SECURITY;

-- Policies
DROP POLICY IF EXISTS "Enable all access for instagram_accounts" ON instagram_accounts;
CREATE POLICY "Enable all access for instagram_accounts"
    ON instagram_accounts FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Enable all access for instagram_posts" ON instagram_posts;
CREATE POLICY "Enable all access for instagram_posts"
    ON instagram_posts FOR ALL USING (true) WITH CHECK (true);


-- ============================================================================
-- Done! You now have:
--   - instagram_accounts: Store scraped accounts
--   - instagram_posts: Store all posts from accounts
-- ============================================================================
