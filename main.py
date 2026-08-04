import os
import sys
import time
import threading
import webbrowser
from datetime import datetime
import sqlite3

from config import (
    USER_ID, CHECK_INTERVAL, WEB_HOST, WEB_PORT,
    DB_PATH
)
from analyzer import analyze_threats
from linker import init_db
from notifier import notify_position_change, notify_status_change


# ===== СОСТОЯНИЕ ПОСЛЕДНЕГО ИЗВЕСТНОГО ПОЛОЖЕНИЯ =====
last_positions = {}
last_statuses = {}


def check_program(program_id, user_id):
    """Проверяет одну программу и отправляет уведомления при изменениях."""
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
           FROM applicants 
           WHERE program_id = ? AND snapshot_time = ? AND sspvo_id = ?''',
        (program_id, latest_time, user_id)
    ).fetchone()
    
    if not user_data:
        conn.close()
        return
    
    # Конкуренты
    competitors = conn.execute(
        '''SELECT COUNT(*) as cnt
           FROM applicants 
           WHERE program_id = ? 
             AND snapshot_time = ?
             AND is_send_agreement = 1
             AND position < ?
             AND total_scores >= ?''',
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
            notify_position_change(
                program_title,
                old_pos or user_data['position'],
                user_data['position'],
                old_real or real_position,
                real_position
            )
        
        if old_safe != is_safe:
            notify_status_change(program_title, is_safe, real_position, places)
    
    last_positions[key] = {
        'position': user_data['position'],
        'real_position': real_position,
        'score': user_data['total_scores']
    }
    last_statuses[key] = is_safe


def check_loop():
    """Основной цикл проверки."""
    print(f"🔄 Парсер запущен. Интервал: {CHECK_INTERVAL} мин.")
    print(f"📊 Отслеживаем программы пользователя {USER_ID}")
    print("📌 Уведомления будут приходить при изменении позиции или статуса")
    
    # Первая проверка сразу
    print("\n⏳ Первая проверка...")
    
    while True:
        try:
            print(f"\n📡 Проверка в {datetime.now().strftime('%H:%M:%S')}")
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            programs = c.execute(
                "SELECT DISTINCT program_id FROM applicants WHERE sspvo_id = ?",
                (USER_ID,)
            ).fetchall()
            conn.close()
            
            if not programs:
                print("⚠️ Пользователь не найден ни в одной программе")
            else:
                print(f"📋 Найдено {len(programs)} программ")
                for prog in programs:
                    check_program(prog[0], USER_ID)
                    time.sleep(0.5)  # Небольшая пауза между программами
            
        except Exception as e:
            print(f"❌ Ошибка в цикле проверки: {e}")
        
        print(f"⏳ Следующая проверка через {CHECK_INTERVAL} минут...")
        time.sleep(CHECK_INTERVAL * 60)


def run_parser_first_time():
    """Первый запуск парсера — загружаем все данные."""
    print("📡 Первый запуск: загрузка всех данных...")
    try:
        from fetcher import fetch_all_programs_data
        fetch_all_programs_data()
        print("✅ Данные загружены")
    except Exception as e:
        print(f"⚠️ Ошибка при первой загрузке: {e}")
        print("   Парсер будет пытаться загрузить данные в фоне...")


def start_web_server():
    """Запускает веб-сервер в отдельном потоке."""
    try:
        from web_app import app
        app.run(host=WEB_HOST, port=WEB_PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"⚠️ Ошибка веб-сервера: {e}")


def main():
    """Главная функция."""
    print("=" * 60)
    print("🎯 ITMO Tracker — Отслеживание позиции в конкурсных списках")
    print("=" * 60)
    
    # Проверяем конфиг
    if not USER_ID or USER_ID == "1871234":
        print("⚠️ ВНИМАНИЕ: Не указан USER_ID в config.py")
        print("   Отредактируйте config.py и укажите ваш sspvo_id")
        print("   Нажмите Enter для продолжения...")
        input()
    
    # Инициализируем БД
    init_db()
    
    # Первый запуск парсера
    run_parser_first_time()
    
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    print(f"🌐 Веб-интерфейс: http://{WEB_HOST}:{WEB_PORT}")
    print(f"🔄 Интервал проверки: {CHECK_INTERVAL} минут")
    
    # Открываем браузер
    try:
        webbrowser.open(f"http://{WEB_HOST}:{WEB_PORT}")
    except:
        pass
    
    print("\n⏳ Ожидание первого обновления...")
    
    # Запускаем цикл проверки
    try:
        check_loop()
    except KeyboardInterrupt:
        print("\n👋 Программа остановлена пользователем")


if __name__ == "__main__":
    main()