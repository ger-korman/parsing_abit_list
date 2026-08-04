# main.py
import time
import sqlite3
from datetime import datetime
from config import (
    MY_SSPVO_ID, MY_PROGRAM_ID, MY_SCORE,
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, CHECK_INTERVAL
)
from fetcher import fetch_program_data
from parser import extract_applicants, get_update_time, get_budget_places
from linker import init_db, save_snapshot, get_last_snapshot_time
from analyzer import analyze_threats

def send_telegram(token, chat_id, message):
    """Отправляет уведомление в Telegram."""
    if not token or not chat_id:
        return
    import requests
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except Exception as e:
        print(f"Ошибка Telegram: {e}")

def main():
    conn = init_db()
    
    print(f"🚀 Запуск мониторинга программы {MY_PROGRAM_ID}")
    print(f"👤 Ваш ID: {MY_SSPVO_ID}, балл: {MY_SCORE}")
    print(f"⏳ Интервал проверки: {CHECK_INTERVAL // 60} минут")
    print("-" * 50)
    
    previous_status = None
    
    while True:
        print(f"\n🔄 Проверка в {datetime.now().strftime('%H:%M:%S')}")
        
        # Загружаем данные
        data = fetch_program_data(MY_PROGRAM_ID)
        if not data:
            print("⚠️ Не удалось загрузить данные. Повтор через 30 секунд...")
            time.sleep(30)
            continue
        
        # Парсим
        applicants = extract_applicants(data, MY_PROGRAM_ID)
        if not applicants:
            print("⚠️ Нет данных об абитуриентах")
            continue
        
        update_time = get_update_time(data)
        print(f"📅 Данные обновлены: {update_time}")
        
        # Сохраняем
        save_snapshot(conn, MY_PROGRAM_ID, applicants, update_time)
        
        # Анализируем
        result = analyze_threats(conn, MY_PROGRAM_ID, MY_SSPVO_ID, MY_SCORE)
        
        if result:
            print("\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
            print(f"   Бюджетных мест: {result['places']}")
            print(f"   Выше вас (с согласием): {result['total_above']}")
            print(f"   ⚠️ Реальных конкурентов: {result['real_threats']}")
            print(f"   🚀 Потенциально уйдут: {result['potential_escapees']}")
            print(f"   🎯 Ваше реальное место: {result['your_position']}")
            
            status = "✅ ВЫ ПРОХОДИТЕ!" if result['is_safe'] else "❌ В ЗОНЕ РИСКА"
            print(f"   Статус: {status}")
            
            # Уведомление при изменении статуса
            if previous_status != result['is_safe']:
                message = f"🔄 ИЗМЕНЕНИЕ СТАТУСА!\nПрограмма: {MY_PROGRAM_ID}\nМесто: {result['your_position']} из {result['places']}\n{status}"
                send_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
                previous_status = result['is_safe']
        else:
            print("⚠️ Не удалось выполнить анализ")
        
        # Ждем до следующей проверки
        print(f"\n⏳ Следующая проверка через {CHECK_INTERVAL // 60} минут...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Программа остановлена пользователем")