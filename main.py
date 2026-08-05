# main.py
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

def add_programs_if_empty():
    """Добавляет программы в БД, если таблица programs пуста."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Проверяем, есть ли программы
    count = c.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    conn.close()
    
    if count > 0:
        print(f"📋 В БД уже есть {count} программ")
        return
    
    print("📡 Добавляем программы в БД...")
    
    # Импортируем и запускаем добавление
    try:
        from add_programs_to_db import add_programs
        add_programs()
    except ImportError:
        print("⚠️ Файл add_programs_to_db.py не найден")
        print("   Создаю базовый список программ...")
        add_programs_manually()

def add_programs_manually():
    """Добавляет программы вручную (если нет файла)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Бакалавриат
    bachelor = [
        (2334, "01.03.02", "Прикладная математика и информатика", 180),
        (2335, "02.03.03", "Математическое обеспечение и администрирование ИС", 55),
        (2336, "03.03.02", "Физика", 30),
        (2337, "04.03.01", "Химия", 30),
        (2338, "05.03.06", "Экология и природопользование", 25),
        (2339, "09.03.01", "Информатика и вычислительная техника", 30),
        (2340, "09.03.02", "Информационные системы и технологии", 175),
        (2341, "09.03.03", "Прикладная информатика", 30),
        (2342, "09.03.04", "Программная инженерия", 164),
        (2343, "10.03.01", "Информационная безопасность", 103),
        (2344, "11.03.02", "Инфокоммуникационные технологии и системы связи", 95),
        (2345, "12.03.01", "Приборостроение", 15),
        (2346, "12.03.03 и 12.03.05", "Фотоника и оптоинформатика и Лазерная техника и лазерные технологии", 85),
        (2347, "12.03.04", "Биотехнические системы и технологии", 25),
        (2348, "13.03.02", "Электроэнергетика и электротехника", 15),
        (2349, "15.03.04 и 15.03.06", "Автоматизация технологических процессов и производств и Мехатроника и робототехника", 80),
        (2350, "16.03.01", "Техническая физика", 75),
        (2351, "18.03.01 и 18.03.02", "Химическая технология и Энерго- и ресурсосберегающие процессы", 65),
        (2352, "19.03.01", "Биотехнология", 65),
        (2353, "24.03.02", "Системы управления движением и навигация", 15),
        (2354, "27.03.05", "Инноватика", 74),
        (2355, "27.03.04", "Управление в технических системах", 16),
        (2356, "38.03.05", "Бизнес-информатика", 55),
        (2357, "54.03.01", "Дизайн", 25),
        (2449, "45.03.04", "Интеллектуальные системы в гуманитарной сфере", 35),
    ]
    
    # Магистратура
    master = [
        (2358, "01.04.02", "Big data and machine learning / Большие данные и машинное обучение", 30),
        (2359, "01.04.02", "Bioinformatics and Systems Biology / Биоинформатика и системная биология", 22),
        (2360, "01.04.02", "Глубокое обучение и генеративный искусственный интеллект", 18),
        (2361, "01.04.02", "Математическое и компьютерное моделирование", 36),
        (2362, "01.04.02", "Программное обеспечение высоконагруженных систем", 35),
        (2363, "01.04.02", "Разработка программного обеспечения / Software Engineering", 31),
        (2364, "02.04.03", "Аналитика данных", 50),
        (2365, "02.04.03", "Управление ИИ-продуктами / AI Product", 26),
        (2366, "06.04.01", "Molecular Biology and Biotechnology / Молекулярная биология и биотехнология", 15),
        (2367, "06.04.01", "Прикладная геномика", 20),
        (2368, "07.04.04", "Цифровая урбанистика", 54),
        (2369, "09.04.01", "Искусственный интеллект", 50),
        (2370, "09.04.01", "Компьютерные системы и технологии", 26),
        (2371, "09.04.02", "Искусственный интеллект в промышленности", 40),
        (2372, "09.04.02", "Программирование и интернет-технологии", 36),
        (2373, "09.04.02", "Речевые технологии и машинное обучение", 16),
        (2374, "09.04.02", "Управление ИТ-инфраструктурой бизнеса", 0),
        (2375, "09.04.03", "Информационные системы бизнеса", 17),
        (2376, "09.04.03", "Мобильные и облачные технологии", 50),
        (2377, "09.04.03", "Технологии разработки компьютерных игр", 50),
        (2378, "09.04.03", "Фронтенд и бэкенд разработка", 0),
        (2379, "09.04.04", "Веб-технологии", 59),
        (2380, "09.04.04", "Инструменты разработки и анализа программ", 27),
        (2381, "09.04.04", "Мультимедиа-технологии, дизайн и юзабилити", 47),
        (2382, "09.04.04", "Нейротехнологии и программная инженерия", 26),
        (2383, "09.04.04", "Проектирование и разработка систем больших данных", 26),
        (2384, "09.04.04", "Проектирование и разработка систем искусственного интеллекта", 28),
        (2385, "09.04.04", "Руководитель IT-разработки", 6),
        (2386, "10.04.01", "Безопасность систем искусственного интеллекта и Информационная безопасность", 120),
        (2387, "10.04.01", "Кибербезопасность", 10),
        (2388, "11.04.03", "Безопасность беспилотных систем", 26),
        (2389, "11.04.02", "DevOps-инженер облачных сервисов", 0),
        (2390, "11.04.02", "Искусственный интеллект", 85),
        (2391, "11.04.02", "Разработка и эксплуатация промышленного бэкенда", 89),
        (2392, "11.04.02", "Распределенные веб-сервисы / Web scale systems", 30),
        (2393, "12.04.01", "Инженерия цифровых систем", 15),
        (2394, "12.04.01", "Цифровые технологии в производстве", 25),
        (2395, "12.04.02", "Прикладная оптика / Applied Optics", 15),
        (2396, "12.04.03 и 12.04.05", "Лазерные технологии и нанотехнологии", 37),
        (2397, "12.04.03", "Прикладная фотоника", 15),
        (2398, "12.04.04", "Хемоинформатика и биоинженерия", 20),
        (2399, "12.04.05", "Функциональные материалы и системы передачи данных", 8),
        (2400, "13.04.02", "Электроинженерия / Electrical and Power Engineering", 25),
        (2401, "15.04.06", "Робототехника и искусственный интеллект", 59),
        (2402, "15.04.06", "Системный анализ, управление и робототехника", 10),
        (2403, "15.04.06", "Электроинженерия / Electrical and Power Engineering", 10),
        (2404, "15.04.04", "Роботизированные химические технологии", 16),
        (2405, "15.04.04", "Цифровые технологии в производстве", 30),
        (2406, "15.04.02", "Транспортировка природного газа", 10),
        (2407, "16.04.01", "Advanced Quantum and Nanophotonic Systems", 59),
        (2408, "16.04.01", "Световодная фотоника и программируемая электроника", 16),
        (2409, "16.04.03", "Информационные технологии в теплофизике", 12),
        (2410, "16.04.03", "Транспортировка природного газа", 8),
        (2411, "16.04.03", "Энергоэффективные инженерные системы и технологии СПГ", 50),
        (2412, "18.04.01", "Infochemistry / Инфохимия", 35),
        (2413, "18.04.02", "Chemistry and Artificial Intelligence / Химия и искусственный интеллект", 20),
        (2414, "18.04.02", "Sustainable Chemistry For Energy Technologies", 18),
        (2415, "18.04.02", "Биоэкономика и управление ресурсами", 24),
        (2416, "18.04.02", "Индустриальная экология / Industrial ecology", 45),
        (2417, "19.04.01", "Molecular Biology and Biotechnology", 16),
        (2418, "19.04.01", "Индустриальная биотехнология", 56),
        (2419, "19.04.01", "Передовые пищевые системы", 16),
        (2420, "19.04.01", "Прикладная геномика", 14),
        (2421, "19.04.01", "ФудТех", 44),
        (2422, "20.04.01", "Индустриальная экология / Industrial ecology", 15),
        (2423, "20.04.01", "Устойчивое развитие и экологическое управление", 20),
        (2424, "24.04.02", "Навигационные системы беспилотных аппаратов", 16),
        (2425, "27.04.05", "Дизайн и развитие цифровых продуктов", 0),
        (2426, "27.04.05", "Искусственный интеллект", 80),
        (2427, "27.04.05", "Искусство и наука / Art & Science", 35),
        (2428, "27.04.05", "Технологии и стратегии бизнес-трансформации", 30),
        (2429, "27.04.05", "Управление высокотехнологичным бизнесом", 213),
        (2430, "27.04.05", "Устойчивое развитие и экологическое управление", 15),
        (2431, "27.04.05", "Цифровые финансы", 5),
        (2432, "27.04.04", "Интеллектуальные системы управления", 33),
        (2433, "27.04.03", "Математические технологии системного анализа", 21),
        (2434, "27.04.03", "Системный анализ, управление и робототехника", 10),
        (2435, "27.04.07", "Науки о здоровье / Public Health Sciences", 36),
        (2436, "27.04.07", "Цифровая урбанистика", 22),
        (2437, "27.04.08", "Стратегическое управление интеллектуальной собственностью", 25),
        (2438, "38.04.05", "Технологии и стратегии бизнес-трансформации", 50),
        (2439, "54.04.01", "Мультимедиа-технологии, дизайн и юзабилити", 16),
        (2440, "45.04.04", "Цифровые методы в гуманитарных исследованиях", 50),
        (2441, "09.04.04", "Программное обеспечение радиоэлектронных систем", 22),
        (2442, "01.04.02", "Искусственный интеллект и поведенческая экономика", 20),
        (2443, "09.04.04", "Искусственный интеллект и поведенческая экономика", 20),
        (2444, "09.04.04", "Системное и прикладное программное обеспечение", 67),
        (2445, "01.04.02", "Программирование и компьютерные науки", 45),
        (2446, "09.04.04", "Разработка ассистивных ИТ-решений", 18),
        (2447, "27.04.05", "Научная коммуникация", 25),
        (2448, "27.04.05", "Управление продуктом в цифровом бизнесе", 0),
    ]
    
    all_programs = bachelor + master
    
    for prog in all_programs:
        c.execute('''INSERT OR REPLACE INTO programs (id, code, title, budget_places)
                     VALUES (?, ?, ?, ?)''', prog)
    
    conn.commit()
    conn.close()
    print(f"✅ Добавлено {len(all_programs)} программ в БД")

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
    
    # Конкуренты
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
    
    # Инициализация БД
    init_db()
    
    # Добавляем программы, если их нет
    add_programs_if_empty()
    
    # Первый запуск парсера
    run_parser_first_time()
    
    # Веб-сервер
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    print(f"🌐 http://{WEB_HOST}:{WEB_PORT}")
    try:
        webbrowser.open(f"http://{WEB_HOST}:{WEB_PORT}")
    except:
        pass
    
    # Цикл проверки
    try:
        check_loop()
    except KeyboardInterrupt:
        print("\n👋 Выход")

if __name__ == "__main__":
    main()
