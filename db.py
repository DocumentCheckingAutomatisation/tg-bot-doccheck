import sqlite3

conn = sqlite3.connect("bot_users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    role TEXT DEFAULT 'student'
)
""")
conn.commit()

def get_user_role(user_id: int) -> str:
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else "student"

def set_user_role(user_id: int, role: str):
    cursor.execute("""
    INSERT INTO users (user_id, role) VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET role = excluded.role
    """, (user_id, role))
    conn.commit()
