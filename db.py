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
        if result:
            return result[0]
        else:
            # Если пользователь не найден, добавим как студента
            cursor.execute("INSERT INTO roles (user_id, role) VALUES (?, ?)", (user_id, STUDENT_ROLE))
            conn.commit()
            return STUDENT_ROLE


def set_user_role(user_id: int, role: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO roles (user_id, role) VALUES (?, ?)", (user_id, role))
        conn.commit()

