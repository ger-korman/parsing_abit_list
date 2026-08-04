# add_bachelor_programs.py
import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

# HTML с программами бакалавриата (из вашего сообщения)
HTML_DATA = """<div class="DirectionsList_cards__NWRcz"><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2334"><div><p>01.03.02 «Прикладная математика и информатика»</p></div><div>КЦП: 180</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2335"><div><p>02.03.03 «Математическое обеспечение и администрирование информационных систем»</p></div><div>КЦП: 55</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2336"><div><p>03.03.02 «Физика»</p></div><div>КЦП: 30</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2337"><div><p>04.03.01 «Химия»</p></div><div>КЦП: 30</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2338"><div><p>05.03.06 «Экология и природопользование»</p></div><div>КЦП: 25</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2339"><div><p>09.03.01 «Информатика и вычислительная техника»</p></div><div>КЦП: 30</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2340"><div><p>09.03.02 «Информационные системы и технологии»</p></div><div>КЦП: 175</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2341"><div><p>09.03.03 «Прикладная информатика»</p></div><div>КЦП: 30</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2342"><div><p>09.03.04 «Программная инженерия»</p></div><div>КЦП: 164</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2343"><div><p>10.03.01 «Информационная безопасность»</p></div><div>КЦП: 103</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2344"><div><p>11.03.02 «Инфокоммуникационные технологии и системы связи»</p></div><div>КЦП: 95</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2345"><div><p>12.03.01 «Приборостроение»</p></div><div>КЦП: 15</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2346"><div><p>12.03.03 и 12.03.05 «Фотоника и оптоинформатика и Лазерная техника и лазерные технологии»</p></div><div>КЦП: 85</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2347"><div><p>12.03.04 «Биотехнические системы и технологии»</p></div><div>КЦП: 25</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2348"><div><p>13.03.02 «Электроэнергетика и электротехника»</p></div><div>КЦП: 15</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2349"><div><p>15.03.04 и 15.03.06 «Автоматизация технологических процессов и производств и Мехатроника и робототехника»</p></div><div>КЦП: 80</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2350"><div><p>16.03.01 «Техническая физика»</p></div><div>КЦП: 75</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2351"><div><p>18.03.01 и 18.03.02 «Химическая технология и Энерго- и ресурсосберегающие процессы в химической технологии, нефтехимии и биотехнологии»</p></div><div>КЦП: 65</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2352"><div><p>19.03.01 «Биотехнология»</p></div><div>КЦП: 65</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2353"><div><p>24.03.02 «Системы управления движением и навигация»</p></div><div>КЦП: 15</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2355"><div><p>27.03.04 «Управление в технических системах»</p></div><div>КЦП: 16</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2354"><div><p>27.03.05 «Инноватика»</p></div><div>КЦП: 74</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2356"><div><p>38.03.05 «Бизнес-информатика»</p></div><div>КЦП: 55</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2449"><div><p>45.03.04 «Интеллектуальные системы в гуманитарной сфере»</p></div><div>КЦП: 35</div></a><a class="DirectionsList_card__5AVa5" href="/rating/bachelor/budget/2357"><div><p>54.03.01 «Дизайн»</p></div><div>КЦП: 25</div></a></div>"""


def parse_bachelor_programs(html):
    """Парсит программы бакалавриата из HTML."""
    programs = []
    
    # Ищем все ссылки с программами
    import re
    pattern = r'href="/rating/bachelor/budget/(\d+)".*?<p>(.*?)</p>.*?КЦП:\s*(\d+)'
    matches = re.findall(pattern, html, re.DOTALL)
    
    for prog_id, name, kcp in matches:
        # Извлекаем код специальности
        code_match = re.match(r'^(\d+\.\d+\.\d+)', name)
        code = code_match.group(1) if code_match else ""
        
        programs.append({
            'id': int(prog_id),
            'code': code,
            'name': name.strip(),
            'budget_places': int(kcp)
        })
    
    return programs


def save_bachelor_programs(programs):
    """Сохраняет программы бакалавриата в БД."""
    if not programs:
        print("❌ Нет программ для сохранения")
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Проверяем, есть ли таблица programs
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='programs'")
    if not c.fetchone():
        print("❌ Таблица programs не найдена. Сначала создайте таблицу.")
        conn.close()
        return 0
    
    count = 0
    for p in programs:
        c.execute('''INSERT OR REPLACE INTO programs (id, code, title, budget_places) 
                     VALUES (?, ?, ?, ?)''',
                  (p['id'], p['code'], p['name'], p['budget_places']))
        count += 1
        print(f"  {count:2d}. ID {p['id']} → {p['code']} {p['name'][:50]}... (КЦП: {p['budget_places']})")
    
    conn.commit()
    conn.close()
    
    return count


def main():
    print("=" * 60)
    print("📥 Добавление программ БАКАЛАВРИАТА в БД")
    print("=" * 60)
    
    programs = parse_bachelor_programs(HTML_DATA)
    print(f"📋 Найдено {len(programs)} программ")
    print("-" * 60)
    
    count = save_bachelor_programs(programs)
    
    print("-" * 60)
    print(f"🎉 Успешно добавлено {count} программ бакалавриата в БД!")
    print("📊 Всего программ в БД будет: 24")

if __name__ == "__main__":
    main()