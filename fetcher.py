import requests
import time
import random
import sqlite3
from datetime import datetime
from config import DB_PATH

BACHELOR_IDS = list(range(2334, 2358)) + [2449]
MASTER_IDS = list(range(2358, 2449))

def get_all_program_ids():
    return BACHELOR_IDS + MASTER_IDS

def get_degree(program_id):
    if program_id in BACHELOR_IDS:
        return "bachelor"
    return "master"

def fetch_program_data(program_id):
    degree = get_degree(program_id)
    url = f"https://abit.itmo.ru/_next/data/NUJ_R0N1JIDBv5iu7R8Lb/ru/rating/{degree}/budget/{program_id}.json"
    params = {"degree": degree, "financing": "budget", "id": program_id}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        time.sleep(random.uniform(1.0, 2.5))
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Ошибка {program_id}: {e}")
        return None

def save_applicants(program_id, data):
    if not data:
        return 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    snapshot_time = datetime.now().isoformat()
    try:
        applicants = data.get("pageProps", {}).get("programList", {}).get("general_competition", [])
        if not applicants:
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
                      (program_id, sspvo_id, app.get('priority'), app.get('total_scores', 0),
                       app.get('exam_scores', 0), app.get('ia_scores', 0),
                       app.get('diploma_average'), 1 if app.get('is_send_agreement') else 0,
                       app.get('status'), 1 if app.get('main_top_priority') else 0,
                       1 if app.get('highest_passageway_priority') else 0,
                       app.get('position'), snapshot_time))
            count += 1
        conn.commit()
        print(f"✅ Сохранено {count} для программы {program_id}")
        return count
    except Exception as e:
        print(f"❌ Ошибка {program_id}: {e}")
        return 0
    finally:
        conn.close()

def fetch_all_programs_data():
    program_ids = get_all_program_ids()
    total, success = 0, 0
    for i, prog_id in enumerate(program_ids):
        degree = get_degree(prog_id)
        print(f"[{i+1}/{len(program_ids)}] {degree} {prog_id}")
        data = fetch_program_data(prog_id)
        if data:
            count = save_applicants(prog_id, data)
            if count > 0:
                success += 1
                total += count
        if i < len(program_ids) - 1:
            time.sleep(random.uniform(1.0, 3.0))
    print(f"✅ {success} программ, {total} абитуриентов")