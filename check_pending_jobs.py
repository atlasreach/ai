from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
direct_url = os.getenv('DIRECT_URL')
engine = create_engine(direct_url)

with engine.connect() as conn:
    # Check pending/processing jobs
    result = conn.execute(text("""
        SELECT id, status, created_at, runpod_job_id, model_id
        FROM generation_jobs
        WHERE status IN ('pending', 'processing')
        ORDER BY created_at DESC
        LIMIT 20;
    """))
    
    print("\n" + "="*80)
    print("Pending/Processing Jobs:")
    print("="*80)
    rows = result.fetchall()
    if not rows:
        print("No pending or processing jobs found!")
    for row in rows:
        print(f"ID: {row[0]}, Status: {row[1]}, Created: {row[2]}, RunPod ID: {row[3]}, Model: {row[4]}")
    
    # Check recent completed jobs without gallery images
    result = conn.execute(text("""
        SELECT gj.id, gj.status, gj.created_at, gj.completed_at, 
               gi.id as gallery_image_id
        FROM generation_jobs gj
        LEFT JOIN generated_images gi ON gj.id = gi.job_id
        WHERE gj.status = 'completed'
        ORDER BY gj.completed_at DESC NULLS LAST
        LIMIT 10;
    """))
    
    print("\n" + "="*80)
    print("Recent Completed Jobs (with gallery status):")
    print("="*80)
    for row in result:
        gallery_status = "✓ In Gallery" if row[4] else "✗ NOT in Gallery"
        print(f"Job ID: {row[0]}, Completed: {row[3]}, {gallery_status}")
