import sqlite3
import os

DB_PATH = "database.db"

def get_conn():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=10
    )
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash TEXT,
        created_at REAL
    )
    """)

    # JOBS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        user_id TEXT,
        tool TEXT,
        status TEXT,
        params TEXT,
        result_json TEXT,
        result_excel TEXT,
        error TEXT,
        created_at REAL
    )
    """)

    # EVENTS TABLE (analytics)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT,
        tool TEXT,
        user_id TEXT,
        timestamp REAL
    )
    """)

    conn.commit()
    conn.close()


def ensure_dirs():
    os.makedirs("results", exist_ok=True)