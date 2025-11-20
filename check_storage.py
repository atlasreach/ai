import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('host'),
    port=int(os.getenv('port')),
    dbname=os.getenv('dbname'),
    user=os.getenv('user'),
    password=os.getenv('password')
)
cur = conn.cursor()

cur.execute("SELECT id, filename, storage_path FROM reference_images LIMIT 3")
for row in cur.fetchall():
    print(f"ID: {row[0]}")
    print(f"Filename: {row[1]}")
    print(f"Path: {row[2]}")
    print()

cur.close()
conn.close()
