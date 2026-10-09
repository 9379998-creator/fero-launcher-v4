import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
import time

RUNTIME_DIR = Path("runtime")
DB_DIR = RUNTIME_DIR / "db"
DB_PATH = DB_DIR / "launcher.sqlite"

def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS roots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_id INTEGER NOT NULL,
            rel_path TEXT NOT NULL,
            name TEXT NOT NULL,
            ext TEXT NOT NULL,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            content_hash TEXT,
            FOREIGN KEY (root_id) REFERENCES roots(id) ON DELETE CASCADE,
            UNIQUE (root_id, rel_path)
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
            UNIQUE (document_id, type)
        );
        """)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH.absolute())
