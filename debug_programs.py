# debug_programs.py
import requests
import json

def debug_fetch_programs():
    url = "https://abit.itmo.ru/_next/data/NUJ_R0N1JIDBv5iu7R8Lb/ru/directions.json"
    params = {"degree": "master"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Сохраняем для анализа
        with open('debug_directions.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("✅ Данные сохранены в debug_directions.json")
        print(f"Ключи верхнего уровня: {list(data.keys())}")
        
        page_props = data.get('pageProps', {})
        print(f"Ключи pageProps: {list(page_props.keys())}")
        
        # Проверяем разные возможные пути
        directions = page_props.get('directions', [])
        print(f"directions: {len(directions)} записей")
        
        if not directions:
            # Может быть другой путь
            program_list = page_props.get('programList', {})
            print(f"programList keys: {list(program_list.keys())}")
            
            # Может быть список программ напрямую
            for key in ['programs', 'items', 'list']:
                if key in page_props:
                    print(f"{key}: {len(page_props[key])} записей")
        
        # Показываем первые 3 программы, если есть
        if directions:
            for i, d in enumerate(directions[:3]):
                print(f"\nНаправление {i+1}: {d.get('title', 'Без названия')}")
                programs = d.get('programs', [])
                for p in programs[:3]:
                    print(f"  - {p.get('code', '')} {p.get('name', '')} (id: {p.get('id')})")
        
        return data
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

if __name__ == "__main__":
    debug_fetch_programs()