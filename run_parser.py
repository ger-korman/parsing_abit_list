# run_parser.py
import sqlite3
import os
import requests
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_all_program_ids():
    """Получает все ID программ из БД."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM programs")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids

def fetch_program_data(program_id):
    """Загружает данные по программе."""
    url = f"https://abit.itmo.ru/_next/data/NUJ_R0N1JIDBv5iu7R8Lb/ru/rating/master/budget/{program_id}.json"
    params = {"degree": "master", "financing": "budget", "id": program_id}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Ошибка загрузки программы {program_id}: {e}")
        return None

def save_applicants(program_id, data):
    """Сохраняет абитуриентов в БД."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    snapshot_time = datetime.now().isoformat()
    
    try:
        applicants = data.get("pageProps", {}).get("programList", {}).get("general_competition", [])
        
        if not applicants:
            print(f"⚠️ Нет абитуриентов для программы {program_id}")
            return 0
        
        count = 0
        for app in applicants:
            c.execute('''INSERT OR REPLACE INTO applicants 
                         (program_id, sspvo_id, priority, total_scores, exam_scores, ia_scores,
                          diploma_average, is_send_agreement, status, main_top_priority,
                          highest_passageway_priority, position, snapshot_time)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (program_id,
                       app.get('sspvo_id'),
                       app.get('priority'),
                       app.get('total_scores', 0),
                       app.get('exam_scores', 0),
                       app.get('ia_scores', 0),
                       app.get('diploma_average'),
                       app.get('is_send_agreement', False),
                       app.get('status'),
                       app.get('main_top_priority', False),
                       app.get('highest_passageway_priority', False),
                       app.get('position'),
                       snapshot_time))
            count += 1
        
        conn.commit()
        print(f"✅ Сохранено {count} абитуриентов для программы {program_id}")
        return count
    except Exception as e:
        print(f"❌ Ошибка сохранения программы {program_id}: {e}")
        return 0
    finally:
        conn.close()

def main():
    print("=" * 60)
    print("🔄 Запуск парсера конкурсных списков")
    print("=" * 60)
    
    # Получаем ID программ из БД
    program_ids = get_all_program_ids()
    print(f"📋 Найдено {len(program_ids)} программ")
    
    if not program_ids:
        print("❌ Нет программ в БД. Сначала добавьте программы.")
        return
    
    # Загружаем данные по каждой программе
    total = 0
    for prog_id in program_ids:
        print(f"\n📡 Загрузка программы {prog_id}...")
        data = fetch_program_data(prog_id)
        if data:
            count = save_applicants(prog_id, data)
            total += count
    
    print(f"\n🎉 Всего сохранено {total} абитуриентов")

if __name__ == "__main__":
    main()