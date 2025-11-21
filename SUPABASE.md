# Creating Tables in Supabase Programmatically

This guide explains how to create tables in your Supabase database using Python and direct database connections.

## Prerequisites

1. **Database Connection Strings** from Supabase
2. **Python** with pip installed
3. Required Python packages

## Step 1: Get Your Database Connection Strings

From your Supabase dashboard, navigate to:
**Project Settings → Database → Connection String**

You'll need two connection strings:

```env
# Connect to Supabase via connection pooling
DATABASE_URL="postgresql://postgres.yiriqesejsbzmzxdxiqt:[YOUR-PASSWORD]@aws-1-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true"

# Direct connection to the database. Used for migrations
DIRECT_URL="postgresql://postgres.yiriqesejsbzmzxdxiqt:[YOUR-PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
```

- **DATABASE_URL** (port 6543): For regular queries via PgBouncer connection pooling
- **DIRECT_URL** (port 5432): For schema changes like creating tables

Store these in a `.env` file in your project root.

## Step 2: Install Required Python Packages

```bash
pip install sqlalchemy python-dotenv psycopg2-binary
```

- **sqlalchemy**: Database toolkit and ORM
- **python-dotenv**: Load environment variables from .env file
- **psycopg2-binary**: PostgreSQL adapter for Python

## Step 3: Create the Python Script

Create a file called `create_test_table.py`:

```python
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get the direct connection URL
direct_url = os.getenv('DIRECT_URL')

# Create engine
engine = create_engine(direct_url)

# Create a test table
create_table_sql = """
CREATE TABLE IF NOT EXISTS test_table (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);
"""

try:
    with engine.connect() as conn:
        # Create the table
        conn.execute(text(create_table_sql))
        conn.commit()
        print("✓ Test table 'test_table' created successfully!")

        # Verify the table was created
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'test_table'
            ORDER BY ordinal_position;
        """))

        columns = result.fetchall()
        print("\nTable structure:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")

except Exception as e:
    print(f"✗ Error creating table: {e}")
    import traceback
    traceback.print_exc()
```

## Step 4: Run the Script

```bash
python create_test_table.py
```

You should see output like:

```
✓ Test table 'test_table' created successfully!

Table structure:
  - id: integer
  - name: text
  - email: text
  - created_at: timestamp without time zone
  - is_active: boolean
```

## How It Works

1. **Load Environment Variables**: `load_dotenv()` reads your `.env` file
2. **Create Engine**: SQLAlchemy creates a connection engine using `DIRECT_URL`
3. **Execute SQL**: The `CREATE TABLE` statement is executed with `conn.execute(text(...))`
4. **Commit Changes**: `conn.commit()` saves the changes to the database
5. **Verify**: Query `information_schema.columns` to confirm the table was created

## Key Points

- **Use DIRECT_URL** for schema changes (CREATE, ALTER, DROP)
- **Use DATABASE_URL** for regular queries (SELECT, INSERT, UPDATE, DELETE)
- **CREATE TABLE IF NOT EXISTS** prevents errors if the table already exists
- **SQLAlchemy handles connection management** and prevents common connection issues

## Common Data Types in PostgreSQL

- `SERIAL`: Auto-incrementing integer
- `TEXT`: Variable-length string
- `VARCHAR(n)`: Variable-length string with limit
- `INTEGER`: Whole numbers
- `BOOLEAN`: true/false
- `TIMESTAMP`: Date and time
- `TIMESTAMPTZ`: Date and time with timezone
- `UUID`: Universally unique identifier
- `JSONB`: Binary JSON data
- `NUMERIC`: Exact decimal numbers

## Example: Creating a Custom Table

```python
create_table_sql = """
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    stock INTEGER DEFAULT 0,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""
```

## Troubleshooting

### Error: "duplicate SASL authentication request"
- Use SQLAlchemy instead of psycopg2 directly
- Ensure you're using the DIRECT_URL (port 5432) not DATABASE_URL (port 6543)

### Error: "relation already exists"
- The table already exists in your database
- Use `CREATE TABLE IF NOT EXISTS` or drop the existing table first

### Error: "connection refused"
- Check your internet connection
- Verify your database password is correct
- Ensure your IP is allowed in Supabase network restrictions

## Verifying in Supabase Dashboard

After running the script:
1. Open your Supabase dashboard
2. Go to **Table Editor**
3. You should see your new table listed
4. Click on it to view the structure and data

## Next Steps

- Add Row Level Security (RLS) policies
- Create indexes for better query performance
- Set up foreign keys for relationships
- Add triggers for automatic timestamp updates
