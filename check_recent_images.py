from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
direct_url = os.getenv('DIRECT_URL')
engine = create_engine(direct_url)

with engine.connect() as conn:
    # Check most recent images
    result = conn.execute(text("""
        SELECT id, created_at, is_deleted, is_starred, model_id, prompt_used
        FROM generated_images
        ORDER BY created_at DESC
        LIMIT 20;
    """))
    
    print("\n" + "="*80)
    print("20 Most Recent Images in Database:")
    print("="*80)
    for row in result:
        print(f"ID: {row[0]}, Created: {row[1]}, Deleted: {row[2]}, Starred: {row[3]}, Model: {row[4]}")
        print(f"  Prompt: {row[5][:80] if row[5] else 'None'}...")
        print()
    
    # Count total images
    result = conn.execute(text("SELECT COUNT(*) FROM generated_images WHERE is_deleted = false;"))
    total = result.fetchone()[0]
    print(f"\nTotal non-deleted images: {total}")
    
    # Count deleted images
    result = conn.execute(text("SELECT COUNT(*) FROM generated_images WHERE is_deleted = true;"))
    deleted = result.fetchone()[0]
    print(f"Total deleted images: {deleted}")
