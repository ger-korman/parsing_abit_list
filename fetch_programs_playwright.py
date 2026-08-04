# fetch_programs_playwright.py
import asyncio
import re
import sqlite3
import os
from playwright.async_api import async_playwright

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


async def fetch_programs():
    """Загружает страницу и парсит программы с помощью Playwright."""
    async with async_playwright() as p:
        # Запускаем браузер
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("📡 Загружаю страницу...")
        await page.goto("https://abit.itmo.ru/ratings/master", wait_until="networkidle")
        
        # Ждем появления карточек
        try:
            await page.wait_for_selector('.DirectionsList_card__5AVa5', timeout=10000)
        except:
            print("⚠️ Не дождался карточек, пробую другой селектор...")
            await page.wait_for_selector('a[href*="/rating/master/budget/"]', timeout=10000)
        
        print("✅ Страница загружена")
        
        # Получаем HTML
        html = await page.content()
        
        # Парсим программы напрямую через JavaScript
        programs = await page.evaluate('''
            () => {
                const programs = [];
                const cards = document.querySelectorAll('a[href*="/rating/master/budget/"]');
                
                cards.forEach(card => {
                    const href = card.getAttribute('href');
                    const match = href.match(/\\/budget\\/(\\d+)/);
                    if (!match) return;
                    
                    const id = parseInt(match[1]);
                    
                    // Ищем название
                    const nameTag = card.querySelector('p');
                    const name = nameTag ? nameTag.textContent.trim() : '';
                    
                    // Ищем КЦП
                    const text = card.textContent;
                    const kcpMatch = text.match(/КЦП:\\s*(\\d+)/);
                    const budget_places = kcpMatch ? parseInt(kcpMatch[1]) : 0;
                    
                    // Извлекаем код специальности
                    const codeMatch = name.match(/^(\\d+\\.\\d+\\.\\d+)/);
                    const code = codeMatch ? codeMatch[1] : '';
                    
                    programs.push({ id, code, name, budget_places });
                });
                
                return programs;
            }
        ''')
        
        await browser.close()
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
        print(f"  {count:2d}. ID {p['id']} → {p['code']} {p['name'][:40]}... (КЦП: {p['budget_places']})")
    
    conn.commit()
    conn.close()
    
    return count


async def main():
    """Основная функция."""
    print("=" * 60)
    print("🕷️  Парсер программ ИТМО (Playwright)")
    print("=" * 60)
    
    programs = await fetch_programs()
    
    if not programs:
        print("❌ Не найдено программ")
        return
    
    print(f"\n📋 Найдено {len(programs)} программ:")
    print("-" * 60)
    
    count = save_programs_to_db(programs)
    
    print("-" * 60)
    print(f"🎉 Успешно сохранено {count} программ в БД!")


if __name__ == "__main__":
    asyncio.run(main())
    