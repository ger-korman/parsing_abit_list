# fetch_programs_selenium.py
import re
import sqlite3
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


def fetch_programs():
    """Загружает страницу и парсит программы с помощью Selenium."""
    
    # Настройки Chrome
    options = Options()
    options.add_argument('--headless')  # Без графического интерфейса
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    print("📡 Запускаю браузер...")
    
    # Используем webdriver-manager для автоматической установки драйвера
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print("📡 Загружаю страницу...")
        driver.get("https://abit.itmo.ru/ratings/master?title=")
        
        # Ждем загрузки карточек
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/rating/master/budget/"]'))
            )
            print("✅ Карточки программ загружены")
        except:
            print("⚠️ Не дождался карточек, пробую через 2 секунды...")
            time.sleep(2)
        
        # Парсим программы
        programs = []
        cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/rating/master/budget/"]')
        
        print(f"🔍 Найдено {len(cards)} карточек")
        
        for card in cards:
            href = card.get_attribute('href') or ''
            match = re.search(r'/budget/(\d+)', href)
            if not match:
                continue
            
            prog_id = int(match.group(1))
            
            # Ищем название
            try:
                name_tag = card.find_element(By.CSS_SELECTOR, 'p')
                name = name_tag.text.strip()
            except:
                try:
                    name_tag = card.find_element(By.CSS_SELECTOR, 'h5')
                    name = name_tag.text.strip()
                except:
                    name = ''
            
            # Если не нашли название, берем весь текст
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
        
    finally:
        driver.quit()


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
    print("🕷️  Парсер программ ИТМО (Selenium)")
    print("=" * 60)
    
    programs = fetch_programs()
    
    if not programs:
        print("❌ Не найдено программ")
        print("   Возможно, страница загрузилась не полностью")
    else:
        print(f"\n📋 Найдено {len(programs)} программ")
        print("-" * 60)
        count = save_programs_to_db(programs)
        print("-" * 60)
        print(f"🎉 Сохранено {count} программ в БД!")