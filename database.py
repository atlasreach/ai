"""
SQLite database for tracking image generations
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = "/workspaces/ai/generations.db"

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create generations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            prompt TEXT,
            negative_prompt TEXT,
            parameters JSON,
            s3_output_path TEXT,
            local_output_path TEXT,
            generation_time REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for common queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_model_name ON generations(model_name)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at ON generations(created_at DESC)
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized")

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def insert_generation(
    model_name: str,
    timestamp: str,
    prompt: str,
    negative_prompt: str,
    parameters: Dict[str, Any],
    s3_output_path: Optional[str],
    local_output_path: Optional[str],
    generation_time: float
) -> int:
    """Insert a new generation record and return its ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO generations
            (model_name, timestamp, prompt, negative_prompt, parameters,
             s3_output_path, local_output_path, generation_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_name,
            timestamp,
            prompt,
            negative_prompt,
            json.dumps(parameters),
            s3_output_path,
            local_output_path,
            generation_time
        ))
        return cursor.lastrowid

def get_generations(
    model_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve generations with optional filtering"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if model_name:
            cursor.execute("""
                SELECT id, model_name, timestamp, prompt, negative_prompt,
                       parameters, s3_output_path, local_output_path,
                       generation_time, created_at
                FROM generations
                WHERE model_name = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (model_name, limit, offset))
        else:
            cursor.execute("""
                SELECT id, model_name, timestamp, prompt, negative_prompt,
                       parameters, s3_output_path, local_output_path,
                       generation_time, created_at
                FROM generations
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        rows = cursor.fetchall()

        # Convert to list of dicts and parse JSON parameters
        results = []
        for row in rows:
            result = dict(row)
            result['parameters'] = json.loads(result['parameters'])
            results.append(result)

        return results

def get_generation_count(model_name: Optional[str] = None) -> int:
    """Get total count of generations"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if model_name:
            cursor.execute(
                "SELECT COUNT(*) FROM generations WHERE model_name = ?",
                (model_name,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM generations")

        return cursor.fetchone()[0]
