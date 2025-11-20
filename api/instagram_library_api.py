"""
Instagram Library API
Manage scraped Instagram accounts and posts
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import os
import sys
import json
import requests as req
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create router
router = APIRouter(prefix="/api/instagram", tags=["instagram"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ScrapeAccountRequest(BaseModel):
    username: str
    num_posts: int = 50

class UpdateAccountRequest(BaseModel):
    full_name: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

def scrape_account_background(username: str, num_posts: int):
    """Background task to scrape Instagram account using Apify"""
    try:
        print(f"\n🔄 Background scraping started for @{username} (using Apify)")

        # Use Apify scraper instead
        scrape_account_background_apify(username, num_posts)

        print(f"✅ Scraping complete for @{username}")
        return

    except Exception as e:
        error_message = str(e)
        print(f"❌ Scraping failed for @{username}: {error_message}")

        # Update account with error status
        try:
            supabase.table('instagram_accounts').update({
                'scrape_status': 'error',
                'notes': f"Scraping failed: {error_message[:200]}"
            }).eq('username', username).execute()
        except:
            pass


def scrape_account_background_apify(username: str, num_posts: int):
    """Background task to scrape Instagram account using Apify (LEGACY - kept as fallback)"""
    try:
        print(f"\n🔄 Background scraping started for @{username} (using Apify)")

        # Update account status to 'scraping'
        supabase.table('instagram_accounts')\
            .update({'scrape_status': 'scraping'})\
            .eq('username', username)\
            .execute()

        # Get Apify token
        apify_token = os.getenv('APIFY_API_TOKEN')
        apify_url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={apify_token}"

        # Step 1: Scrape profile
        print(f"📊 Scraping profile for @{username}...")
        profile_response = req.post(apify_url, json={
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "details",
            "resultsLimit": 1,
            "addParentData": False
        }, timeout=180)

        if profile_response.status_code not in [200, 201]:
            print(f"❌ Profile scrape failed with status {profile_response.status_code}")
            print(f"Response: {profile_response.text[:500]}")
            raise Exception(f"Profile scrape failed: {profile_response.status_code}")

        profile_data = profile_response.json()
        if not profile_data or len(profile_data) == 0:
            print(f"❌ No profile data returned from Apify")
            raise Exception(f"Instagram account @{username} not found or is private")

        profile = profile_data[0]
        print(f"✓ Profile: {profile.get('fullName')}, {profile.get('followersCount'):,} followers")

        # Download profile picture
        profile_pic_url = None
        profile_pic_instagram = profile.get('profilePicUrlHD') or profile.get('profilePicUrl')
        if profile_pic_instagram:
            try:
                img_response = req.get(profile_pic_instagram, timeout=30)
                if img_response.status_code == 200:
                    filename = f"instagram/{username}/profile.jpg"
                    supabase.storage.from_('images').upload(filename, img_response.content, {'content-type': 'image/jpeg', 'upsert': 'true'})
                    profile_pic_url = supabase.storage.from_('images').get_public_url(filename)
            except Exception as e:
                print(f"⚠️  Profile pic failed: {e}")
                profile_pic_url = profile_pic_instagram

        # Step 2: Scrape posts
        print(f"📸 Scraping {num_posts} posts...")
        posts_response = req.post(apify_url, json={
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "posts",
            "resultsLimit": num_posts,
            "addParentData": False
        }, timeout=180)

        if posts_response.status_code not in [200, 201]:
            print(f"❌ Posts scrape failed with status {posts_response.status_code}")
            print(f"Response: {posts_response.text[:500]}")
            raise Exception(f"Posts scrape failed: {posts_response.status_code}")

        posts = posts_response.json()
        if not posts or len(posts) == 0:
            print(f"❌ No posts returned from Apify")
            raise Exception(f"No posts found for @{username} or account is private")

        print(f"✓ Received {len(posts)} posts")

        # Helper function to upload images
        def upload_image(image_url, post_id, index=0):
            try:
                img_response = req.get(image_url, timeout=30)
                if img_response.status_code == 200:
                    filename = f"instagram/{username}/{post_id}_{index}.jpg"
                    supabase.storage.from_('images').upload(filename, img_response.content, {'content-type': 'image/jpeg', 'upsert': 'true'})
                    return supabase.storage.from_('images').get_public_url(filename)
            except:
                pass
            return image_url

        # Get account ID
        account_result = supabase.table('instagram_accounts').select('id').eq('username', username).execute()
        account_id = account_result.data[0]['id']

        # Save posts
        print(f"💾 Saving {len(posts)} posts...")
        for idx, post in enumerate(posts, 1):
            post_id = post.get('id')
            display_url_instagram = post.get('displayUrl')
            media_urls_instagram = post.get('images', []) if post.get('type') == 'Sidecar' else ([display_url_instagram] if display_url_instagram else [])

            # Download images
            display_url = upload_image(display_url_instagram, post_id, 0) if display_url_instagram else None
            media_urls = [upload_image(url, post_id, i) for i, url in enumerate(media_urls_instagram)] if len(media_urls_instagram) > 1 else []

            # Save post
            post_data = {
                'account_id': account_id,
                'instagram_id': post_id,
                'post_type': post.get('type'),
                'short_code': post.get('shortCode'),
                'post_url': post.get('url'),
                'display_url': display_url,
                'media_urls': media_urls,
                'video_url': post.get('videoUrl'),
                'caption': post.get('caption', ''),
                'hashtags': post.get('hashtags', []),
                'likes_count': post.get('likesCount', 0),
                'comments_count': post.get('commentsCount', 0),
                'views_count': post.get('videoViewCount', 0) or post.get('videoPlayCount', 0),
                'posted_at': post.get('timestamp'),
                'metadata': {'product_type': post.get('productType'), 'is_sponsored': post.get('isSponsored', False)}
            }
            try:
                # Check if post already exists
                existing = supabase.table('instagram_posts').select('id').eq('instagram_id', post_id).execute()
                if existing.data:
                    # Update existing post
                    supabase.table('instagram_posts').update(post_data).eq('instagram_id', post_id).execute()
                else:
                    # Insert new post
                    supabase.table('instagram_posts').insert(post_data).execute()
            except Exception as e:
                print(f"❌ Error saving post {idx}: {e}")

        # Update account with final data
        supabase.table('instagram_accounts').update({
            'full_name': profile.get('fullName', username),
            'profile_pic_url': profile_pic_url,
            'bio': profile.get('biography', ''),
            'external_url': profile.get('externalUrl'),
            'followers_count': profile.get('followersCount', 0),
            'following_count': profile.get('followsCount', 0),
            'post_count': profile.get('postsCount', 0),
            'is_verified': profile.get('verified', False),
            'is_business': profile.get('isBusinessAccount', False),
            'total_posts_scraped': len(posts),
            'last_scraped_at': datetime.now().isoformat(),
            'scrape_status': 'complete'
        }).eq('username', username).execute()

        print(f"✅ Scraping complete for @{username}")

    except Exception as e:
        error_message = str(e)
        print(f"❌ Background scraping failed for @{username}: {error_message}")

        # Update account with error status and message
        supabase.table('instagram_accounts').update({
            'scrape_status': 'error',
            'notes': f"Scraping failed: {error_message[:200]}"
        }).eq('username', username).execute()

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/accounts")
async def list_accounts():
    """
    Get all scraped Instagram accounts with linked model info
    """
    try:
        result = supabase.table('instagram_accounts')\
            .select('*, post_count:instagram_posts(count)')\
            .order('created_at', desc=True)\
            .execute()

        accounts = result.data or []

        # Transform to include post count and model name
        for account in accounts:
            post_count_data = account.pop('post_count', [])
            account['posts_count'] = len(post_count_data) if post_count_data else 0

            # Get linked model name if model_id exists
            model_id = account.get('model_id')
            if model_id:
                try:
                    model_result = supabase.table('models')\
                        .select('name')\
                        .eq('id', model_id)\
                        .single()\
                        .execute()

                    if model_result.data:
                        account['model_name'] = model_result.data['name']
                    else:
                        account['model_name'] = None
                except:
                    account['model_name'] = None
            else:
                account['model_name'] = None

        return {
            "success": True,
            "accounts": accounts
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch accounts: {str(e)}")


@router.get("/accounts/{account_id}")
async def get_account_detail(account_id: str):
    """
    Get account details with all posts
    """
    try:
        # Get account
        account_result = supabase.table('instagram_accounts')\
            .select('*')\
            .eq('id', account_id)\
            .single()\
            .execute()

        if not account_result.data:
            raise HTTPException(status_code=404, detail="Account not found")

        # Get posts
        posts_result = supabase.table('instagram_posts')\
            .select('*')\
            .eq('account_id', account_id)\
            .order('posted_at', desc=True)\
            .execute()

        # Parse media_urls from JSON string to array
        posts = posts_result.data or []
        for post in posts:
            if 'media_urls' in post and isinstance(post['media_urls'], str):
                try:
                    post['media_urls'] = json.loads(post['media_urls'])
                except:
                    post['media_urls'] = []

        return {
            "success": True,
            "account": account_result.data,
            "posts": posts
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch account: {str(e)}")


@router.post("/scrape")
async def scrape_account(request: ScrapeAccountRequest, background_tasks: BackgroundTasks):
    """
    Start scraping Instagram account in background
    """
    try:
        # Check if account already exists
        existing = supabase.table('instagram_accounts')\
            .select('id, scrape_status')\
            .eq('username', request.username)\
            .execute()

        if existing.data:
            account_id = existing.data[0]['id']
            # If already scraping, return existing
            if existing.data[0]['scrape_status'] == 'scraping':
                return {
                    "success": True,
                    "account_id": account_id,
                    "username": request.username,
                    "status": "scraping",
                    "message": f"Already scraping @{request.username}"
                }
            # Otherwise, update status and re-scrape
            supabase.table('instagram_accounts')\
                .update({'scrape_status': 'scraping'})\
                .eq('id', account_id)\
                .execute()
        else:
            # Create placeholder account
            account_data = {
                'username': request.username,
                'scrape_status': 'scraping',
                'last_scraped_at': datetime.now().isoformat()
            }
            result = supabase.table('instagram_accounts').insert(account_data).execute()
            account_id = result.data[0]['id']

        # Start background scraping
        background_tasks.add_task(scrape_account_background, request.username, request.num_posts)

        return {
            "success": True,
            "account_id": account_id,
            "username": request.username,
            "status": "scraping",
            "message": f"Started scraping @{request.username}. You can navigate away - it will update when complete."
        }

    except Exception as e:
        print(f"Error starting scrape: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scraping: {str(e)}")

# Keep the old synchronous endpoint as /scrape-sync for testing
@router.post("/scrape-sync")
async def scrape_account_sync(request: ScrapeAccountRequest):
    """
    Scrape Instagram account synchronously (old endpoint for testing)
    """
    try:
        # Get Apify token
        apify_token = os.getenv('APIFY_API_TOKEN')
        if not apify_token:
            raise HTTPException(status_code=500, detail="APIFY_API_TOKEN not configured")

        apify_url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={apify_token}"

        # Step 1: Scrape account profile data
        print(f"📊 Scraping profile for @{request.username}...")
        profile_payload = {
            "directUrls": [f"https://www.instagram.com/{request.username}/"],
            "resultsType": "details",
            "resultsLimit": 1
        }

        profile_response = req.post(apify_url, json=profile_payload, timeout=180)
        print(f"Profile response status: {profile_response.status_code}")

        if profile_response.status_code not in [200, 201]:
            raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {profile_response.status_code}")

        profile_data = profile_response.json()
        if not profile_data or len(profile_data) == 0:
            raise HTTPException(status_code=404, detail="Profile not found or account is private")

        profile = profile_data[0]
        print(f"✓ Profile loaded: {profile.get('fullName', request.username)}")
        print(f"  Followers: {profile.get('followersCount', 0):,}")
        print(f"  Posts: {profile.get('postsCount', 0):,}")

        # Step 2: Scrape posts
        print(f"\n📸 Scraping {request.num_posts} posts from @{request.username}...")
        posts_payload = {
            "directUrls": [f"https://www.instagram.com/{request.username}/"],
            "resultsType": "posts",
            "resultsLimit": request.num_posts
        }

        posts_response = req.post(apify_url, json=posts_payload, timeout=180)
        print(f"Posts response status: {posts_response.status_code}")

        if posts_response.status_code not in [200, 201]:
            print(f"Posts error: {posts_response.text[:500]}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch posts: {posts_response.status_code}")

        posts = posts_response.json()
        print(f"✓ Received {len(posts)} posts from Apify")

        if not posts or len(posts) == 0:
            raise HTTPException(status_code=404, detail="No posts found")

        # Download and upload profile picture
        profile_pic_url = None
        profile_pic_instagram = profile.get('profilePicUrlHD') or profile.get('profilePicUrl')
        if profile_pic_instagram:
            print(f"📥 Downloading profile picture...")
            try:
                img_response = req.get(profile_pic_instagram, timeout=30)
                if img_response.status_code == 200:
                    filename = f"instagram/{request.username}/profile.jpg"
                    supabase.storage.from_('images').upload(
                        filename,
                        img_response.content,
                        {'content-type': 'image/jpeg', 'upsert': 'true'}
                    )
                    profile_pic_url = supabase.storage.from_('images').get_public_url(filename)
                    print(f"✓ Profile picture uploaded")
            except Exception as e:
                print(f"⚠️  Profile pic upload failed: {e}")
                profile_pic_url = profile_pic_instagram  # Fallback

        # Prepare account data with rich profile information
        from datetime import datetime
        account_data = {
            'username': request.username,
            'full_name': profile.get('fullName', request.username),
            'profile_pic_url': profile_pic_url,
            'bio': profile.get('biography', ''),
            'external_url': profile.get('externalUrl'),
            'followers_count': profile.get('followersCount', 0),
            'following_count': profile.get('followsCount', 0),
            'post_count': profile.get('postsCount', 0),
            'is_verified': profile.get('verified', False),
            'is_business': profile.get('isBusinessAccount', False),
            'total_posts_scraped': len(posts),
            'last_scraped_at': datetime.now().isoformat(),
            'scrape_status': 'complete'
        }
        print(f"\n💾 Account data prepared:")

        # Create or update account
        print("Checking if account exists...")
        existing = supabase.table('instagram_accounts')\
            .select('id')\
            .eq('username', request.username)\
            .execute()

        if existing.data:
            # Update existing
            print(f"Updating existing account {existing.data[0]['id']}")
            account_result = supabase.table('instagram_accounts')\
                .update(account_data)\
                .eq('username', request.username)\
                .execute()
            account_id = existing.data[0]['id']
            print(f"✓ Account updated")
        else:
            # Create new
            print("Creating new account...")
            account_result = supabase.table('instagram_accounts')\
                .insert(account_data)\
                .execute()
            account_id = account_result.data[0]['id']
            print(f"✓ Account created with ID: {account_id}")

        # Helper function to download and upload image to Supabase
        def upload_image_to_supabase(image_url: str, post_id: str, index: int = 0) -> str:
            """Download image from Instagram CDN and upload to Supabase storage"""
            try:
                # Download image
                img_response = req.get(image_url, timeout=30)
                if img_response.status_code != 200:
                    print(f"  ⚠️  Failed to download image: {img_response.status_code}")
                    return image_url  # Fallback to original URL

                # Generate filename
                ext = 'jpg'
                filename = f"instagram/{request.username}/{post_id}_{index}.{ext}"

                # Upload to Supabase storage
                upload_result = supabase.storage.from_('images').upload(
                    filename,
                    img_response.content,
                    {
                        'content-type': 'image/jpeg',
                        'upsert': 'true'
                    }
                )

                # Get public URL
                public_url = supabase.storage.from_('images').get_public_url(filename)
                return public_url

            except Exception as e:
                print(f"  ⚠️  Error uploading image: {e}")
                return image_url  # Fallback to original URL

        # Save posts
        print(f"\n💾 Downloading and saving {len(posts)} posts...")
        saved_posts = []
        for idx, post in enumerate(posts, 1):
            post_type = post.get('type')
            post_id = post.get('id')

            # Get media URLs from Instagram
            display_url_instagram = post.get('displayUrl')
            media_urls_instagram = []

            if post_type == 'Sidecar':
                media_urls_instagram = post.get('images', [])
            elif display_url_instagram:
                media_urls_instagram = [display_url_instagram]

            print(f"  [{idx}/{len(posts)}] Post {post.get('shortCode')} ({post_type})")

            # Download and upload images to Supabase
            display_url = None
            media_urls = []

            if display_url_instagram:
                print(f"    📥 Downloading display image...")
                display_url = upload_image_to_supabase(display_url_instagram, post_id, 0)

            if media_urls_instagram and len(media_urls_instagram) > 1:
                print(f"    📥 Downloading {len(media_urls_instagram)} carousel images...")
                for i, img_url in enumerate(media_urls_instagram):
                    uploaded_url = upload_image_to_supabase(img_url, post_id, i)
                    media_urls.append(uploaded_url)

            # Extract hashtags from caption or hashtags array
            hashtags = post.get('hashtags', [])

            post_data = {
                'account_id': account_id,
                'instagram_id': post.get('id'),
                'post_type': post_type,
                'short_code': post.get('shortCode'),
                'post_url': post.get('url'),
                'display_url': display_url,
                'media_urls': media_urls,
                'video_url': post.get('videoUrl'),
                'caption': post.get('caption', ''),
                'hashtags': hashtags,
                'likes_count': post.get('likesCount', 0),
                'comments_count': post.get('commentsCount', 0),
                'views_count': post.get('videoViewCount', 0) or post.get('videoPlayCount', 0),
                'posted_at': post.get('timestamp'),
                'metadata': {
                    'product_type': post.get('productType'),
                    'is_sponsored': post.get('isSponsored', False)
                }
            }

            # Insert or update post
            try:
                # Check if post already exists
                existing = supabase.table('instagram_posts').select('id').eq('instagram_id', post.get('id')).execute()
                if existing.data:
                    # Update existing post
                    result = supabase.table('instagram_posts').update(post_data).eq('instagram_id', post.get('id')).execute()
                else:
                    # Insert new post
                    result = supabase.table('instagram_posts').insert(post_data).execute()
                saved_posts.append(result.data[0] if result.data else post_data)
                print(f"    ✓ Saved post {idx}/{len(posts)}")
            except Exception as e:
                print(f"❌ Error saving post {post.get('id')}: {e}")
                continue

        return {
            "success": True,
            "account_id": account_id,
            "username": request.username,
            "posts_scraped": len(saved_posts),
            "message": f"Successfully scraped {len(saved_posts)} posts from @{request.username}"
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.patch("/accounts/{account_id}")
async def update_account(account_id: str, request: UpdateAccountRequest):
    """
    Update account metadata
    """
    try:
        update_data = {}
        if request.full_name is not None:
            update_data['full_name'] = request.full_name
        if request.notes is not None:
            update_data['notes'] = request.notes
        if request.tags is not None:
            update_data['tags'] = request.tags
        if request.is_favorite is not None:
            update_data['is_favorite'] = request.is_favorite

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = supabase.table('instagram_accounts')\
            .update(update_data)\
            .eq('id', account_id)\
            .execute()

        return {
            "success": True,
            "account": result.data[0] if result.data else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    """
    Delete account and all its posts
    """
    try:
        result = supabase.table('instagram_accounts')\
            .delete()\
            .eq('id', account_id)\
            .execute()

        return {
            "success": True,
            "message": "Account deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
