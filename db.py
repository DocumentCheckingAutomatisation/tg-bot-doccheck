import sqlite3
from datetime import datetime, timezone, timedelta

DB_NAME = "roles.db"

STUDENT_ROLE = "student"
REVIEWER_ROLE = "reviewer"

TIMEDELTA_FOR_LAST_ACTIVE = 10


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                username TEXT,
                registered_at TEXT,
                last_active TEXT
            )
        ''')
        conn.commit()


def get_user_role(user_id: int, username: str = None) -> str:
    now_utc = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT role, last_active FROM roles WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result:
            role, last_active = result

            # Обновляем last_active, если прошло более 10 минут
            if last_active:
                last_dt = datetime.fromisoformat(last_active)
                if datetime.now(timezone.utc) - last_dt > timedelta(minutes=TIMEDELTA_FOR_LAST_ACTIVE):
                    cursor.execute(
                        "UPDATE roles SET last_active = ? WHERE user_id = ?",
                        (now_utc, user_id)
                    )
            else:
                cursor.execute(
                    "UPDATE roles SET last_active = ? WHERE user_id = ?",
                    (now_utc, user_id)
                )

            conn.commit()
            return role
        else:
            # Если пользователь не найден, добавим как студента
            cursor.execute('''
                INSERT INTO roles (user_id, role, username, registered_at, last_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, STUDENT_ROLE, username, now_utc, now_utc))
            conn.commit()
            return STUDENT_ROLE


def set_user_role(user_id: int, role: str):
    now_utc = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO roles (user_id, role, last_active)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role = excluded.role, last_active = excluded.last_active
        ''', (user_id, role, now_utc))
        conn.commit()
