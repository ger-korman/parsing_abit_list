# fetch_programs_from_page.py
import requests
import re
import sqlite3
import os
from bs4 import BeautifulSoup
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def fetch_programs_page():
    """
    Загружает страницу с программами и парсит их.
    """
    url = "https://abit.itmo.ru/ratings/master"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    
    try:
        print("📡 Загружаю страницу с программами...")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        print(f"✅ Страница загружена, размер: {len(response.text)} символов")
        return response.text
    except Exception as e:
        print(f"❌ Ошибка загрузки страницы: {e}")
        return None


def parse_programs_from_html(html):
    """
    Парсит программы из HTML-кода страницы.
    Ищет карточки с классом DirectionsList_card__5AVa5.
    """
    soup = BeautifulSoup(html, 'html.parser')
    programs = []

    # Ищем все карточки программ
    cards = soup.find_all('a', class_=re.compile(r'DirectionsList_cards__'))
    
    # Если не нашли по классу, ищем по href
    if not cards:
        cards = soup.find_all('a', href=re.compile(r'/rating/master/budget/\d+'))
    
    print(f"🔍 Найдено {len(cards)} карточек программ")
    
    for card in cards:
        href = card.get('href', '')
        
        # Извлекаем ID из href
        match_id = re.search(r'/budget/(\d+)', href)
        if not match_id:
            continue
        prog_id = int(match_id.group(1))
        
        # Ищем название в тегах <p> или <h5>
        name_tag = card.find('p')
        if not name_tag:
            name_tag = card.find('h5')
        if not name_tag:
            # Ищем любой текстовый узел с кодом специальности
            text = card.get_text()
            match_code = re.search(r'\d+\.\d+\.\d+\s*[«"]([^»"]+)[»"]', text)
            if match_code:
                name = match_code.group(0).strip()
            else:
                continue
        else:
            name = name_tag.text.strip()
        
        # Извлекаем КЦП
        # Ищем div или span с текстом "КЦП:"
        all_text = card.get_text()
        match_kcp = re.search(r'КЦП:\s*(\d+)', all_text)
        budget_places = int(match_kcp.group(1)) if match_kcp else 0
        
        # Извлекаем код специальности
        code_match = re.match(r'^(\d+\.\d+\.\d+)', name)
        code = code_match.group(1) if code_match else ""
        
        programs.append({
            'id': prog_id,
            'code': code,
            'name': name,
            'budget_places': budget_places
        })
    
    return programs


def find_programs_in_next_data(html):
    """
    Альтернативный способ: ищем программы в __NEXT_DATA__ (JSON).
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Ищем скрипт с __NEXT_DATA__
    script_tag = soup.find('script', id='__NEXT_DATA__')
    if not script_tag:
        return []
    
    try:
        import json
        data = json.loads(script_tag.string)
        # В этом JSON нет списка программ, только переводы
        # Поэтому этот способ не подходит для ИТМО
        return []
    except:
        return []


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
        print(f"  {count:2d}. ID {p['id']} → {p['code']} {p['name'][:40]}... (КЦП: {p['budget_places']})")
    
    conn.commit()
    conn.close()
    
    return count


def main():
    """Основная функция."""
    print("=" * 60)
    print("🕷️  Парсер программ ИТМО")
    print("=" * 60)
    
    # 1. Загружаем страницу
    html = fetch_programs_page()
    if not html:
        print("❌ Не удалось загрузить страницу")
        return
    
    # 2. Парсим программы
    programs = parse_programs_from_html(html)
    
    if not programs:
        print("⚠️ Не удалось найти программы в HTML.")
        print("   Возможно, данные подгружаются через JavaScript.")
        print("   Попробуйте запустить позже или проверьте структуру страницы.")
        return
    
    # 3. Показываем найденные программы
    print(f"\n📋 Найдено {len(programs)} программ:")
    print("-" * 60)
    
    # 4. Сохраняем в БД
    count = save_programs_to_db(programs)
    
    print("-" * 60)
    print(f"🎉 Успешно сохранено {count} программ в БД!")
    
    # 5. Проверяем, что в БД
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM programs")
    db_count = c.fetchone()[0]
    conn.close()
    print(f"📊 В БД сейчас {db_count} программ")


if __name__ == "__main__":
    main()