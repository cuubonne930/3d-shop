import sqlite3
from datetime import datetime

DB_NAME = "shop.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price INTEGER NOT NULL,
            photo_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_model(title: str, description: str, price: int, photo_path: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO models (title, description, price, photo_path, created_at) VALUES (?, ?, ?, ?, ?)",
        (title, description, price, photo_path, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_models():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, price, photo_path FROM models ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"id": r[0], "title": r[1], "description": r[2], "price": r[3], "photo": r[4]}
        for r in rows
    ]

init_db()