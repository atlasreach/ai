#!/usr/bin/env python3
import os
import sys
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Read SQL file
sql_file = os.path.join(os.path.dirname(__file__), 'create_instagram_library.sql')
with open(sql_file, 'r') as f:
    sql = f.read()

# Get DB URL
db_url = os.getenv('DIRECT_DATABASE_URL')

if not db_url:
    print('❌ ERROR: DIRECT_DATABASE_URL not found in .env')
    sys.exit(1)

print('🔄 Connecting to Supabase database...')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print('📋 Executing Instagram library migration...')
try:
    cur.execute(sql)
    conn.commit()
    print('✅ Migration executed successfully!')

    # Verify
    print('\n🔍 Verifying tables...')
    cur.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = 'instagram_accounts')")
    print(f'  ✓ instagram_accounts: {cur.fetchone()[0]}')

    cur.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = 'instagram_posts')")
    print(f'  ✓ instagram_posts: {cur.fetchone()[0]}')

    print('\n✅ Instagram Library is ready!')
    print('🚀 Open http://localhost:5173/instagrams to use it!')

except Exception as e:
    print(f'❌ Error: {e}')
    conn.rollback()
    sys.exit(1)
finally:
    cur.close()
    conn.close()
