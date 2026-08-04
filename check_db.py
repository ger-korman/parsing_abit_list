# check_db.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def check_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Проверяем программы
    c.execute("SELECT COUNT(*) FROM programs")
    prog_count = c.fetchone()[0]
    print(f"📊 Программ в БД: {prog_count}")
    
    # Проверяем абитуриентов
    c.execute("SELECT COUNT(*) FROM applicants")
    app_count = c.fetchone()[0]
    print(f"📊 Абитуриентов в БД: {app_count}")
    
    if app_count == 0:
        print("\n⚠️ Нет данных об абитуриентах!")
        print("   Нужно запустить парсер для сбора данных.")
    
    # Проверяем конкретную программу
    program_id = 2362  # Ваша программа
    c.execute("SELECT COUNT(*) FROM applicants WHERE program_id = ?", (program_id,))
    prog_app_count = c.fetchone()[0]
    print(f"📊 Абитуриентов для программы {program_id}: {prog_app_count}")
    
    conn.close()

if __name__ == "__main__":
    check_db()