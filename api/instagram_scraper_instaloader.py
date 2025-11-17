"""
Instagram Scraper using Instaloader
Alternative to Apify for more reliable scraping
"""
import instaloader
import os
import io
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

class InstagramScraperInstaloader:
    def __init__(self):
        self.loader = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            download_pictures=True,
            quiet=True
        )

        # Initialize Supabase
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )

    def scrape_profile(self, username, num_posts=0):
        """
        Scrape Instagram profile and save to Supabase
        num_posts: Number of posts to scrape (0 or negative = ALL posts)
        Returns: (account_id, posts_scraped)
        """
        print(f"📊 Scraping profile for @{username} using Instaloader...")

        try:
            # Load profile
            profile = instaloader.Profile.from_username(self.loader.context, username)

            print(f"✓ Profile loaded: {profile.full_name}")
            print(f"  Followers: {profile.followers:,}")
            print(f"  Posts: {profile.mediacount:,}")

            # Check if account exists in database
            existing = self.supabase.table('instagram_accounts')\
                .select('id')\
                .eq('username', username)\
                .execute()

            # Prepare account data
            account_data = {
                'username': username,
                'full_name': profile.full_name or username,
                'bio': profile.biography or '',
                'external_url': profile.external_url or None,
                'followers_count': profile.followers,
                'following_count': profile.followees,
                'post_count': profile.mediacount,
                'is_verified': profile.is_verified,
                'is_business': profile.is_business_account,
                'scrape_status': 'scraping',
                'last_scraped_at': datetime.now().isoformat()
            }

            # Create or update account
            if existing.data:
                account_id = existing.data[0]['id']
                self.supabase.table('instagram_accounts')\
                    .update(account_data)\
                    .eq('id', account_id)\
                    .execute()
                print(f"✓ Updated existing account {account_id}")
            else:
                result = self.supabase.table('instagram_accounts')\
                    .insert(account_data)\
                    .execute()
                account_id = result.data[0]['id']
                print(f"✓ Created new account {account_id}")

            # Download profile picture
            profile_pic_url = None
            try:
                print(f"📥 Downloading profile picture...")
                self.loader.download_profilepic(profile)

                # Find the downloaded profile pic
                pic_path = f"{username}/{username}_*.jpg"
                import glob
                pics = glob.glob(pic_path)

                if pics:
                    with open(pics[0], 'rb') as f:
                        pic_data = f.read()

                    # Upload to Supabase storage
                    filename = f"instagram/{username}/profile.jpg"
                    self.supabase.storage.from_('images').upload(
                        filename,
                        pic_data,
                        {'content-type': 'image/jpeg', 'upsert': 'true'}
                    )
                    profile_pic_url = self.supabase.storage.from_('images').get_public_url(filename)
                    print(f"✓ Profile picture uploaded")

                    # Clean up downloaded file
                    os.remove(pics[0])
                    os.rmdir(username)
            except Exception as e:
                print(f"⚠️  Profile pic failed: {e}")
                profile_pic_url = profile.profile_pic_url

            # Update account with profile pic
            if profile_pic_url:
                self.supabase.table('instagram_accounts')\
                    .update({'profile_pic_url': profile_pic_url})\
                    .eq('id', account_id)\
                    .execute()

            # Scrape posts
            scrape_all = num_posts <= 0
            if scrape_all:
                print(f"📸 Scraping ALL posts from profile...")
            else:
                print(f"📸 Scraping {num_posts} posts...")

            posts_scraped = 0

            for idx, post in enumerate(profile.get_posts()):
                # If num_posts is 0 or negative, scrape all posts
                if not scrape_all and idx >= num_posts:
                    break

                try:
                    self.save_post(post, account_id, username)
                    posts_scraped += 1

                    if (idx + 1) % 10 == 0:
                        if scrape_all:
                            print(f"  Scraped {idx + 1} posts so far...")
                        else:
                            print(f"  Scraped {idx + 1}/{num_posts} posts...")

                except Exception as e:
                    print(f"  ⚠️  Error saving post {idx + 1}: {e}")
                    continue

            # Update account with final status
            self.supabase.table('instagram_accounts').update({
                'total_posts_scraped': posts_scraped,
                'scrape_status': 'complete',
                'last_scraped_at': datetime.now().isoformat()
            }).eq('id', account_id).execute()

            print(f"✅ Scraping complete for @{username}")
            print(f"   Total posts scraped: {posts_scraped}")

            return account_id, posts_scraped

        except instaloader.exceptions.ProfileNotExistsException:
            print(f"❌ Profile @{username} does not exist")
            raise Exception(f"Instagram account @{username} not found")
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            print(f"❌ Profile @{username} is private")
            raise Exception(f"Instagram account @{username} is private")
        except Exception as e:
            print(f"❌ Error scraping profile: {e}")
            raise

    def save_post(self, post, account_id, username):
        """Save a single post to Supabase"""
        # Download post image
        display_url = None

        try:
            # Get the image URL directly from post
            display_url_instagram = post.url

            # Download and upload to Supabase
            import requests
            img_response = requests.get(display_url_instagram, timeout=30)

            if img_response.status_code == 200:
                filename = f"instagram/{username}/{post.shortcode}.jpg"
                self.supabase.storage.from_('images').upload(
                    filename,
                    img_response.content,
                    {'content-type': 'image/jpeg', 'upsert': 'true'}
                )
                display_url = self.supabase.storage.from_('images').get_public_url(filename)
        except Exception as e:
            print(f"    ⚠️  Image download failed: {e}")
            display_url = post.url  # Fallback to Instagram URL

        # Prepare post data
        post_data = {
            'account_id': account_id,
            'instagram_id': str(post.mediaid),
            'post_type': 'Video' if post.is_video else 'Image',
            'short_code': post.shortcode,
            'post_url': f"https://www.instagram.com/p/{post.shortcode}/",
            'display_url': display_url,
            'media_urls': [],
            'video_url': post.video_url if post.is_video else None,
            'caption': post.caption if post.caption else '',
            'hashtags': post.caption_hashtags if post.caption_hashtags else [],
            'likes_count': post.likes,
            'comments_count': post.comments,
            'views_count': post.video_view_count if post.is_video else 0,
            'posted_at': post.date_utc.isoformat(),
            'metadata': {
                'is_sponsored': post.is_sponsored,
                'typename': post.typename
            }
        }

        # Check if post already exists
        existing = self.supabase.table('instagram_posts')\
            .select('id')\
            .eq('instagram_id', str(post.mediaid))\
            .execute()

        if existing.data:
            # Update existing post
            self.supabase.table('instagram_posts')\
                .update(post_data)\
                .eq('instagram_id', str(post.mediaid))\
                .execute()
        else:
            # Insert new post
            self.supabase.table('instagram_posts')\
                .insert(post_data)\
                .execute()


def scrape_instagram_account(username, num_posts=0):
    """
    Helper function to scrape Instagram account
    num_posts: Number of posts to scrape (0 or negative = ALL posts)
    """
    scraper = InstagramScraperInstaloader()
    return scraper.scrape_profile(username, num_posts)
