-- Create storage bucket for Instagram images
-- Note: This needs to be run as a Supabase SQL query or through the dashboard

-- Insert the bucket into storage.buckets
INSERT INTO storage.buckets (id, name, public)
VALUES ('images', 'images', true)
ON CONFLICT (id) DO NOTHING;

-- Create policy to allow public access
CREATE POLICY "Public Access" ON storage.objects FOR SELECT USING (bucket_id = 'images');

-- Create policy to allow service role to upload
CREATE POLICY "Service role can upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'images');
