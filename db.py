import sqlite3

DB_NAME = "roles.db"

STUDENT_ROLE = "student"
REVIEWER_ROLE = "reviewer"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL
            )
        ''')
        conn.commit()

def get_user_role(user_id: int) -> str:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM roles WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else STUDENT_ROLE

def set_user_role(user_id: int, role: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO roles (user_id, role) VALUES (?, ?)", (user_id, role))
        conn.commit()


# import sqlite3
#
# conn = sqlite3.connect("bot_users.db")
# cursor = conn.cursor()
#
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS users (
#     user_id INTEGER PRIMARY KEY,
#     role TEXT DEFAULT 'student'
# )
# """)
# conn.commit()
#
# def get_user_role(user_id: int) -> str:
#     cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
#     result = cursor.fetchone()
#     return result[0] if result else "student"
#
# def set_user_role(user_id: int, role: str):
#     cursor.execute("""
#     INSERT INTO users (user_id, role) VALUES (?, ?)
#     ON CONFLICT(user_id) DO UPDATE SET role = excluded.role
#     """, (user_id, role))
#     conn.commit()
