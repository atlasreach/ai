# Supabase Connection Guide for AI Agents

## Environment Setup

Your `.env` file contains the following Supabase credentials:

```bash
SUPABASE_URL=https://yiriqesejsbzmzxdxiqt.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres.yiriqesejsbzmzxdxiqt:jHdJLJ5gRt5blPin@aws-1-us-east-1.pooler.supabase.com:6543/postgres
```

## Two Ways to Connect

### Method 1: Supabase Python Client (Recommended for CRUD operations)

Use this for reading/writing data from tables via the REST API.

```python
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Connect
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Query data
result = supabase.table('models').select('*').execute()
print(result.data)

# Insert data
supabase.table('models').insert({'name': 'New Model'}).execute()

# Update data
supabase.table('models').update({'name': 'Updated'}).eq('id', model_id).execute()

# Delete data
supabase.table('models').delete().eq('id', model_id).execute()
```

### Method 2: Direct PostgreSQL Connection (For DDL/Schema changes)

Use this for creating/altering tables, running raw SQL, and database management.

```python
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Connect with autocommit enabled (IMPORTANT!)
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
conn.autocommit = True  # Required for DDL operations
cur = conn.cursor()

# Create table
cur.execute("""
    CREATE TABLE IF NOT EXISTS public.my_table (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(255),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
""")

# Run any SQL
cur.execute("SELECT * FROM public.models;")
rows = cur.fetchall()

cur.close()
conn.close()
```

## Key Points

1. **Use Supabase client** (Method 1) for all CRUD operations - it's simpler and matches existing code in `api/persona_api.py`
2. **Use psycopg2** (Method 2) only when you need to:
   - Create or alter tables
   - Run raw SQL queries
   - Manage database schema
3. **Always use `autocommit = True`** with psycopg2 to avoid connection errors
4. **The DATABASE_URL uses the pooler** (port 6543) which is required for external connections like GitHub Codespaces

## Existing Tables

Run this to see all tables:
```python
result = supabase.rpc('exec_sql', {'sql': 'SELECT table_name FROM information_schema.tables WHERE table_schema = \'public\';'}).execute()
```

Main tables in this project:
- `public.models`
- `public.personas`
- `public.generated_content`
- `public.instagram_accounts`
- `public.instagram_posts`
- `public.reference_images`
- `public.reference_libraries`
