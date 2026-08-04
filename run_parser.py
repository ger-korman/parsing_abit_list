# run_parser.py — ТОЛЬКО МАГИСТРАТУРА
import sqlite3
import os
import requests
from datetime import datetime
import time
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

# ID магистратуры: от 2358 до 2448 (исключая 2449)
MASTER_IDS = list(range(2358, 2449))  # 2358-2448

def get_master_program_ids():
    """Получает ID программ магистратуры из БД."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Только магистерские ID
    c.execute(f"SELECT id FROM programs WHERE id BETWEEN 2358 AND 2448 ORDER BY id")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids

def fetch_program_data(program_id):
    """Загружает данные по программе магистратуры."""
    url = f"https://abit.itmo.ru/_next/data/NUJ_R0N1JIDBv5iu7R8Lb/ru/rating/master/budget/{program_id}.json"
    params = {"degree": "master", "financing": "budget", "id": program_id}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
    }
    
    try:
        time.sleep(random.uniform(1.0, 2.0))
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"  ⚠️ Программа {program_id} не найдена (404) — возможно, это бакалавриат")
        else:
            print(f"  ❌ HTTP ошибка {program_id}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Ошибка {program_id}: {e}")
        return None

def save_applicants(program_id, data):
    """Сохраняет абитуриентов в БД."""
    if not data:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    snapshot_time = datetime.now().isoformat()
    
    try:
        applicants = data.get("pageProps", {}).get("programList", {}).get("general_competition", [])
        if not applicants:
            print(f"  ⚠️ Нет абитуриентов для программы {program_id}")
            return 0
        
        count = 0
        for app in applicants:
            sspvo_id = app.get('sspvo_id')
            if not sspvo_id:
                continue
                
            c.execute('''INSERT OR REPLACE INTO applicants 
                         (program_id, sspvo_id, priority, total_scores, exam_scores, ia_scores,
                          diploma_average, is_send_agreement, status, main_top_priority,
                          highest_passageway_priority, position, snapshot_time)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (program_id,
                       sspvo_id,
                       app.get('priority'),
                       app.get('total_scores', 0),
                       app.get('exam_scores', 0),
                       app.get('ia_scores', 0),
                       app.get('diploma_average'),
                       1 if app.get('is_send_agreement') else 0,
                       app.get('status'),
                       1 if app.get('main_top_priority') else 0,
                       1 if app.get('highest_passageway_priority') else 0,
                       app.get('position'),
                       snapshot_time))
            count += 1
        
        conn.commit()
        print(f"  ✅ Сохранено {count} абитуриентов для программы {program_id}")
        return count
    except Exception as e:
        print(f"  ❌ Ошибка сохранения программы {program_id}: {e}")
        return 0
    finally:
        conn.close()

def main():
    print("=" * 60)
    print("🔄 Запуск парсера МАГИСТРАТУРЫ")
    print("=" * 60)
    
    program_ids = get_master_program_ids()
    print(f"📋 Найдено {len(program_ids)} программ магистратуры")
    
    if not program_ids:
        print("❌ Нет программ в БД. Сначала добавьте программы.")
        return
    
    total = 0
    success = 0
    failed = []
    
    for i, prog_id in enumerate(program_ids):
        print(f"\n[{i+1}/{len(program_ids)}] 📡 Загрузка программы {prog_id}...")
        data = fetch_program_data(prog_id)
        if data:
            count = save_applicants(prog_id, data)
            if count > 0:
                success += 1
                total += count
            else:
                failed.append(prog_id)
        else:
            failed.append(prog_id)
        
        if i < len(program_ids) - 1:
            time.sleep(random.uniform(1.0, 3.0))
    
    print("\n" + "=" * 60)
    print(f"📊 ИТОГИ ПАРСИНГА МАГИСТРАТУРЫ:")
    print(f"  ✅ Успешно: {success} программ")
    print(f"  ❌ Не загружено: {len(failed)} программ")
    print(f"  👥 Всего абитуриентов: {total}")
    print("=" * 60)

if __name__ == "__main__":
    main()