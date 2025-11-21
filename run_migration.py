import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

with open('sql/02_sub_models_schema.sql', 'r') as f:
    sql = f.read()

# Execute via RPC
supabase.rpc('exec_sql', {'sql': sql}).execute()
print("Migration completed successfully!")
