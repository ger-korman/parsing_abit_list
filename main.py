import os
import sys
import time
import threading
import webbrowser
from datetime import datetime
import sqlite3

from config import USER_ID, CHECK_INTERVAL, WEB_HOST, WEB_PORT, DB_PATH
from linker import init_db
from notifier import notify_position_change, notify_status_change

last_positions = {}
last_statuses = {}

def check_all_programs():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        programs = c.execute(
            "SELECT DISTINCT program_id FROM applicants WHERE sspvo_id = ?",
            (USER_ID,)
        ).fetchall()
        conn.close()
        if not programs:
            print("⚠️ Пользователь не найден")
            return
        for prog in programs:
            check_program(prog[0], USER_ID)
            time.sleep(0.5)
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def check_program(program_id, user_id):
    global last_positions, last_statuses
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    latest = conn.execute(
        'SELECT MAX(snapshot_time) as latest FROM applicants WHERE program_id = ?',
        (program_id,)
    ).fetchone()
    if not latest or not latest['latest']:
        conn.close()
        return
    latest_time = latest['latest']
    user_data = conn.execute(
        '''SELECT total_scores, position, is_send_agreement, priority
           FROM applicants WHERE program_id = ? AND snapshot_time = ? AND sspvo_id = ?''',
        (program_id, latest_time, user_id)
    ).fetchone()
    if not user_data:
        conn.close()
        return
    competitors = conn.execute(
        '''SELECT COUNT(*) as cnt FROM applicants 
           WHERE program_id = ? AND snapshot_time = ?
           AND is_send_agreement = 1 AND position < ? AND total_scores >= ?''',
        (program_id, latest_time, user_data['position'], user_data['total_scores'])
    ).fetchone()
    competitors_count = competitors['cnt'] if competitors else 0
    real_position = competitors_count + 1
    places = conn.execute(
        'SELECT budget_places FROM programs WHERE id = ?', (program_id,)
    ).fetchone()
    places = places['budget_places'] if places else 0
    is_safe = real_position <= places
    program_info = conn.execute(
        'SELECT code, title FROM programs WHERE id = ?', (program_id,)
    ).fetchone()
    program_title = f"{program_info['code']} - {program_info['title']}" if program_info else str(program_id)
    conn.close()
    key = str(program_id)
    if key in last_positions:
        old_pos = last_positions[key].get('position')
        old_real = last_positions[key].get('real_position')
        old_safe = last_statuses.get(key)
        if old_pos != user_data['position'] or old_real != real_position:
            notify_position_change(program_title, old_pos or user_data['position'],
                                   user_data['position'], old_real or real_position, real_position)
        if old_safe != is_safe:
            notify_status_change(program_title, is_safe, real_position, places)
    last_positions[key] = {
        'position': user_data['position'],
        'real_position': real_position,
        'score': user_data['total_scores']
    }
    last_statuses[key] = is_safe

def check_loop():
    print(f"🔄 Интервал: {CHECK_INTERVAL} мин.")
    check_all_programs()
    while True:
        time.sleep(CHECK_INTERVAL * 60)
        print(f"\n📡 Проверка в {datetime.now().strftime('%H:%M:%S')}")
        check_all_programs()

def run_parser_first_time():
    print("📡 Первый запуск...")
    try:
        from fetcher import fetch_all_programs_data
        fetch_all_programs_data()
        print("✅ Данные загружены")
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")

def start_web_server():
    try:
        from web_app import app
        app.run(host=WEB_HOST, port=WEB_PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"⚠️ Ошибка веб-сервера: {e}")

def main():
    print("=" * 60)
    print("🎯 ITMO Tracker")
    print("=" * 60)
    if not USER_ID or USER_ID == "1871234":
        print("⚠️ Укажите USER_ID в config.py")
        input()
    init_db()
    run_parser_first_time()
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    print(f"🌐 http://{WEB_HOST}:{WEB_PORT}")
    try:
        webbrowser.open(f"http://{WEB_HOST}:{WEB_PORT}")
    except:
        pass
    try:
        check_loop()
    except KeyboardInterrupt:
        print("\n👋 Выход")

if __name__ == "__main__":
    main()