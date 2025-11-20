#!/usr/bin/env python3
"""
Setup fresh database schema for multi-model generation system
"""
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
conn.autocommit = True
cur = conn.cursor()

print("Dropping existing tables if they exist...")
cur.execute("DROP TABLE IF EXISTS generated_images CASCADE")
cur.execute("DROP TABLE IF EXISTS reference_images CASCADE")
cur.execute("DROP TABLE IF EXISTS models CASCADE")

print("Creating database schema...")

# Models table
cur.execute("""
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    skin_tone VARCHAR(50),
    hair_color VARCHAR(50),
    hair_style VARCHAR(200),
    lora_file VARCHAR(200),
    trigger_word VARCHAR(100),
    negative_prompt TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
""")
print("✓ Created models table")

# Reference images table (the 120 bikini pics)
cur.execute("""
CREATE TABLE reference_images (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,
    vision_description TEXT,
    analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
)
""")
print("✓ Created reference_images table")

# Generated images table
cur.execute("""
CREATE TABLE generated_images (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    reference_image_id INTEGER REFERENCES reference_images(id),
    storage_path VARCHAR(1000),
    prompt_used TEXT,
    negative_prompt_used TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
)
""")
print("✓ Created generated_images table")

# Insert models from config
models_data = [
    ('Milan', 'milan', 'tan', 'brunette', 'long brunette hair', 'milan_000002000.safetensors', 'milan', 'blonde hair, light hair, pale skin'),
    ('Skyler', 'skyler', 'tan', 'brown', 'long brown hair', 'skyler_000002000.safetensors', 'skyler', 'blonde hair, light hair, pale skin'),
    ('Sky', 'sky', 'tan', 'brunette', 'long brunette hair', 'sky_000002000.safetensors', 'sky', 'blonde hair, light hair, pale skin'),
    ('Cam', 'cam', 'tan', 'blonde', 'long blonde hair', 'cam_000002000.safetensors', 'cam', 'dark hair, brunette hair, brown hair, pale skin')
]

for model_data in models_data:
    cur.execute("""
        INSERT INTO models (name, slug, skin_tone, hair_color, hair_style, lora_file, trigger_word, negative_prompt)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, model_data)

print(f"✓ Inserted {len(models_data)} models")

print("\n✓ Database setup complete!")

cur.close()
conn.close()
