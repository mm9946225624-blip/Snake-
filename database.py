import os
import re
import sqlite3
import secrets
import hashlib
import hmac

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

def init_db():
    with sqlite3.connect(DB_PATH, timeout=15) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

def create_user(email, password):
    email = (email or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Please enter a valid email address."
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 300_000)
    try:
        with sqlite3.connect(DB_PATH, timeout=15) as con:
            con.execute(
                "INSERT INTO users(email, salt, password_hash) VALUES (?, ?, ?)",
                (email, salt, password_hash),
            )
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    except sqlite3.Error:
        return False, "Database error while creating account. Check app logs."

def verify_user(email, password):
    email = (email or "").strip().lower()
    try:
        with sqlite3.connect(DB_PATH, timeout=15) as con:
            row = con.execute(
                "SELECT salt, password_hash FROM users WHERE email = ?", (email,)
            ).fetchone()
        if not row:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), row[0], 300_000)
        return hmac.compare_digest(candidate, row[1])
    except sqlite3.Error:
        return False
