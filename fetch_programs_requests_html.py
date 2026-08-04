# fetch_programs_requests_html.py
from requests_html import HTMLSession
import re
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


def fetch_programs():
    """Загружает страницу и парсит программы с помощью requests-html."""
    session = HTMLSession()
    
    print("📡 Загружаю страницу...")
    response = session.get("https://abit.itmo.ru/ratings/master?title=")
    
    # Ждем, пока JavaScript выполнится
    try:
        response.html.render(timeout=15, sleep=2)
    except Exception as e:
        print(f"⚠️ Ошибка рендеринга: {e}")
        print("Пробую без рендеринга...")
    
    print("✅ Страница загружена")
    
    programs = []
    
    # Ищем карточки через CSS-селектор
    cards = response.html.find('a[href*="/rating/master/budget/"]')
    
    print(f"🔍 Найдено {len(cards)} карточек")
    
    for card in cards:
        href = card.attrs.get('href', '')
        match = re.search(r'/budget/(\d+)', href)
        if not match:
            continue
        
        prog_id = int(match.group(1))
        
        # Ищем название
        name_tag = card.find('p', first=True)
        name = name_tag.text.strip() if name_tag else ''
        
        # Если не нашли через p, ищем через h5
        if not name:
            name_tag = card.find('h5', first=True)
            name = name_tag.text.strip() if name_tag else ''
        
        # Если всё ещё нет, берем весь текст и извлекаем код
        if not name:
            text = card.text
            code_match = re.search(r'(\d+\.\d+\.\d+\s*[«"][^»"]+[»"])', text)
            if code_match:
                name = code_match.group(1).strip()
        
        # Ищем КЦП
        text = card.text
        kcp_match = re.search(r'КЦП:\s*(\d+)', text)
        budget_places = int(kcp_match.group(1)) if kcp_match else 0
        
        # Извлекаем код специальности
        code_match = re.match(r'^(\d+\.\d+\.\d+)', name)
        code = code_match.group(1) if code_match else ''
        
        if prog_id and name:
            programs.append({
                'id': prog_id,
                'code': code,
                'name': name,
                'budget_places': budget_places
            })
    
    return programs


def save_programs_to_db(programs):
    """Сохраняет программы в БД."""
    if not programs:
        print("❌ Нет программ для сохранения")
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Очищаем таблицу
    c.execute("DELETE FROM programs")
    
    count = 0
    for p in programs:
        c.execute('''INSERT OR REPLACE INTO programs (id, code, title, budget_places) 
                     VALUES (?, ?, ?, ?)''',
                  (p['id'], p['code'], p['name'], p['budget_places']))
        count += 1
        print(f"  {count:2d}. ID {p['id']} → {p['code']} {p['name'][:45]}... (КЦП: {p['budget_places']})")
    
    conn.commit()
    conn.close()
    
    return count


if __name__ == "__main__":
    print("=" * 60)
    print("🕷️  Парсер программ ИТМО (requests-html)")
    print("=" * 60)
    
    programs = fetch_programs()
    
    if not programs:
        print("❌ Не найдено программ")
    else:
        print(f"\n📋 Найдено {len(programs)} программ")
        print("-" * 60)
        count = save_programs_to_db(programs)
        print("-" * 60)
        print(f"🎉 Сохранено {count} программ в БД!")