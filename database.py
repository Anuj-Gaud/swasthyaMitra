# database.py
import sqlite3
import logging
from typing import List, Tuple

DB_FILE = "health_bot.db"
logger = logging.getLogger(__name__)

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS symptoms (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, symptom TEXT NOT NULL, severity TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, medication TEXT NOT NULL, time TEXT NOT NULL, job_name TEXT UNIQUE NOT NULL)")
    conn.commit()
    conn.close()
    logger.info("Database setup complete.")

def log_symptom(user_id: int, symptom: str, severity: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute("INSERT INTO symptoms (user_id, symptom, severity) VALUES (?, ?, ?)", (user_id, symptom, severity))
        conn.commit()

def get_symptom_summary(user_id: int) -> List[Tuple]:
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.cursor().execute("SELECT symptom, severity, strftime('%Y-%m-%d %H:%M', timestamp) FROM symptoms WHERE user_id = ? ORDER BY timestamp DESC LIMIT 7", (user_id,)).fetchall()
        return rows

def add_reminder(chat_id: int, medication: str, time_str: str, job_name: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.cursor().execute("INSERT OR REPLACE INTO reminders (chat_id, medication, time, job_name) VALUES (?, ?, ?, ?)", (chat_id, medication, time_str, job_name))
        conn.commit()

def get_all_reminders() -> List[Tuple]:
    with sqlite3.connect(DB_FILE) as conn:
        return conn.cursor().execute("SELECT chat_id, medication, time, job_name FROM reminders").fetchall()