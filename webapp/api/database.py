"""
database.py
Minimal SQLite user store. Uses only Python's built-in sqlite3 module --
no extra pip install required.
"""
import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(BASE_DIR, "webapp", "api", "users.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            age INTEGER,
            occupation TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def create_user(name, email, password_hash, age=None, occupation=None):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, age, occupation) VALUES (?, ?, ?, ?, ?)",
        (name, email, password_hash, age, occupation),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_profile(user_id, name, age, occupation):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET name = ?, age = ?, occupation = ? WHERE id = ?",
        (name, age, occupation, user_id),
    )
    conn.commit()
    conn.close()


def update_password_by_email(email, new_password_hash):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (new_password_hash, email),
    )
    conn.commit()
    conn.close()
