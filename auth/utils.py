import bcrypt
import uuid
import time
from analytics.db import get_conn

def create_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = str(uuid.uuid4())
    # Hash the password so it's unreadable in the DB
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cur.execute("""
        INSERT INTO users (user_id, username, password_hash, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, password_hash, time.time()))

    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    user_id, stored_hash = row
    # Compare the provided password with the hashed version
    if bcrypt.checkpw(password.encode(), stored_hash.encode()):
        return user_id
    return None