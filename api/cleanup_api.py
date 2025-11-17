"""
Cleanup API - Delete all data
"""
from fastapi import APIRouter, HTTPException
from api.database import get_supabase

router = APIRouter(prefix="/cleanup", tags=["cleanup"])
supabase = get_supabase()

@router.delete("/all")
async def cleanup_all_data():
    """Delete ALL data from the database - USE WITH CAUTION"""
    try:
        print("🗑️  Deleting all Instagram posts...")
        supabase.table('instagram_posts').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

        print("🗑️  Deleting all Instagram accounts...")
        supabase.table('instagram_accounts').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

        print("🗑️  Deleting all dataset images...")
        supabase.table('dataset_images').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

        print("🗑️  Deleting all datasets...")
        supabase.table('datasets').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

        print("🗑️  Deleting all models...")
        supabase.table('models').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

        print("✅ All data cleaned up successfully!")

        return {
            "success": True,
            "message": "All data has been deleted successfully"
        }

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
