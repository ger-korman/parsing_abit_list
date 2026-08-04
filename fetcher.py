# fetcher.py
import requests
import time
import random
import sqlite3
from datetime import datetime
from config import DB_PATH

# ID программ по степеням
BACHELOR_IDS = list(range(2334, 2358)) + [2449]  # 2334-2357, 2449
MASTER_IDS = list(range(2358, 2449))  # 2358-2448


def get_all_program_ids():
    """Возвращает ID всех программ (бакалавриат + магистратура)."""
    return BACHELOR_IDS + MASTER_IDS


def get_degree_for_program(program_id):
    """Определяет степень по ID программы."""
    if program_id in BACHELOR_IDS:
        return "bachelor"
    elif program_id in MASTER_IDS:
        return "master"
    else:
        return "master"  # fallback


def fetch_program_data(program_id):
    """Загружает данные по программе (автоматически определяет степень)."""
    degree = get_degree_for_program(program_id)
    
    url = f"https://abit.itmo.ru/_next/data/NUJ_R0N1JIDBv5iu7R8Lb/ru/rating/{degree}/budget/{program_id}.json"
    params = {
        "degree": degree,
        "financing": "budget",
        "id": program_id
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache"
    }
    
    try:
        time.sleep(random.uniform(1.0, 2.5))
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"  ⚠️ Программа {program_id} не найдена (404)")
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
        page_props = data.get("pageProps", {})
        program_list = page_props.get("programList", {})
        applicants = program_list.get("general_competition", [])
        
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


def fetch_all_programs_data():
    """Загружает данные по всем программам (бакалавриат + магистратура)."""
    program_ids = get_all_program_ids()
    total = 0
    success = 0
    
    print(f"📋 Всего программ: {len(program_ids)}")
    print(f"   Бакалавриат: {len(BACHELOR_IDS)}")
    print(f"   Магистратура: {len(MASTER_IDS)}")
    print("-" * 50)
    
    for i, prog_id in enumerate(program_ids):
        degree = get_degree_for_program(prog_id)
        print(f"\n[{i+1}/{len(program_ids)}] 📡 Загрузка {degree} {prog_id}...")
        
        data = fetch_program_data(prog_id)
        if data:
            count = save_applicants(prog_id, data)
            if count > 0:
                success += 1
                total += count
        
        if i < len(program_ids) - 1:
            time.sleep(random.uniform(1.0, 3.0))
    
    print("\n" + "=" * 50)
    print(f"📊 ИТОГИ:")
    print(f"  ✅ Успешно: {success} программ")
    print(f"  👥 Всего абитуриентов: {total}")
    print("=" * 50)