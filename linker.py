# linker.py
import sqlite3
from typing import List, Dict
from config import DB_PATH
from datetime import datetime

def init_db():
    """Инициализирует базу данных."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Таблица программ
    c.execute('''CREATE TABLE IF NOT EXISTS programs (
        id INTEGER PRIMARY KEY,
        budget_places INTEGER,
        update_time TEXT
    )''')
    
    # Таблица абитуриентов (снапшоты)
    c.execute('''CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id INTEGER,
        sspvo_id TEXT,
        priority INTEGER,
        total_scores REAL,
        exam_scores REAL,
        ia_scores REAL,
        diploma_average REAL,
        is_send_agreement BOOLEAN,
        status TEXT,
        main_top_priority BOOLEAN,
        highest_passageway_priority BOOLEAN,
        position INTEGER,
        snapshot_time TEXT,
        FOREIGN KEY (program_id) REFERENCES programs (id)
    )''')
    
    # Индексы для ускорения запросов
    c.execute('CREATE INDEX IF NOT EXISTS idx_sspvo ON applicants (sspvo_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_program_time ON applicants (program_id, snapshot_time)')
    
    conn.commit()
    return conn

def save_snapshot(conn, program_id: int, applicants: List[Dict], update_time: str):
    """Сохраняет снапшот абитуриентов в БД."""
    c = conn.cursor()
    snapshot_time = datetime.now().isoformat()
    
    # Сохраняем программу
    c.execute('''INSERT OR REPLACE INTO programs (id, budget_places, update_time)
                 VALUES (?, ?, ?)''',
              (program_id, len(applicants), update_time))
    
    # Сохраняем абитуриентов
    for app in applicants:
        c.execute('''INSERT INTO applicants 
                     (program_id, sspvo_id, priority, total_scores, exam_scores, ia_scores,
                      diploma_average, is_send_agreement, status, main_top_priority,
                      highest_passageway_priority, position, snapshot_time)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (program_id,
                   app.get("sspvo_id"),
                   app.get("priority"),
                   app.get("total_scores"),
                   app.get("exam_scores"),
                   app.get("ia_scores"),
                   app.get("diploma_average"),
                   app.get("is_send_agreement"),
                   app.get("status"),
                   app.get("main_top_priority"),
                   app.get("highest_passageway_priority"),
                   app.get("position"),
                   snapshot_time))
    
    conn.commit()
    print(f"✅ Сохранен снапшот для программы {program_id} ({len(applicants)} абитуриентов)")

def get_last_snapshot_time(conn, program_id: int) -> str:
    """Возвращает время последнего снапшота."""
    c = conn.cursor()
    c.execute('''SELECT MAX(snapshot_time) FROM applicants WHERE program_id = ?''', (program_id,))
    result = c.fetchone()
    return result[0] if result and result[0] else None