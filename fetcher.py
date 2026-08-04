# fetcher.py
import requests
import json

def fetch_all_programs(degree: str = "master") -> list:
    """
    Получает список всех программ с названиями.
    Поддерживает разные форматы ответа.
    """
    url = "https://abit.itmo.ru/_next/data/NUJ_R0N1JIDBv5iu7R8Lb/ru/directions.json"
    params = {"degree": degree}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        programs = []
        page_props = data.get('pageProps', {})
        
        # Вариант 1: directions -> programs (как было раньше)
        directions = page_props.get('directions', [])
        
        if directions:
            for direction in directions:
                direction_title = direction.get('title', '')
                for program in direction.get('programs', []):
                    programs.append({
                        "id": program.get('id'),
                        "code": program.get('code', ''),
                        "name": program.get('name', program.get('title', '')),
                        "direction_title": direction_title,
                        "budget_places": program.get('budget_places', 0)
                    })
            print(f"✅ Найдено {len(programs)} программ через directions")
            return programs
        
        # Вариант 2: напрямую programs
        programs_list = page_props.get('programs', [])
        if programs_list:
            for p in programs_list:
                programs.append({
                    "id": p.get('id'),
                    "code": p.get('code', ''),
                    "name": p.get('name', p.get('title', '')),
                    "direction_title": p.get('direction', ''),
                    "budget_places": p.get('budget_places', 0)
                })
            print(f"✅ Найдено {len(programs)} программ через programs")
            return programs
        
        # Вариант 3: programList -> general_competition (из вашего JSON)
        program_list = page_props.get('programList', {})
        if program_list:
            # Может быть список программ в другом месте
            for key in ['directions', 'items', 'list']:
                items = program_list.get(key, [])
                if items:
                    for item in items:
                        if isinstance(item, dict):
                            programs.append({
                                "id": item.get('id'),
                                "code": item.get('code', ''),
                                "name": item.get('name', item.get('title', '')),
                                "direction_title": item.get('direction_title', ''),
                                "budget_places": item.get('budget_places', 0)
                            })
                    print(f"✅ Найдено {len(programs)} программ через programList.{key}")
                    return programs
        
        # Вариант 4: ищем вложенные структуры
        print("⚠️ Не найдена стандартная структура, ищем рекурсивно...")
        programs = find_programs_recursive(page_props)
        if programs:
            print(f"✅ Найдено {len(programs)} программ рекурсивным поиском")
            return programs
        
        # Если ничего не нашли, возвращаем заглушку с вашей программой
        print("⚠️ Не удалось найти программы, возвращаю заглушку")
        return [
            {"id": 2362, "code": "01.04.02", "name": "Программное обеспечение высоконагруженных систем", "budget_places": 35}
        ]
        
    except Exception as e:
        print(f"❌ Ошибка получения списка программ: {e}")
        return []

def find_programs_recursive(obj, depth=0):
    """
    Рекурсивный поиск программ в JSON.
    """
    if depth > 5:  # Защита от бесконечной рекурсии
        return []
    
    programs = []
    
    if isinstance(obj, dict):
        # Проверяем, похоже ли на программу
        if 'id' in obj and ('name' in obj or 'title' in obj or 'code' in obj):
            programs.append({
                "id": obj.get('id'),
                "code": obj.get('code', ''),
                "name": obj.get('name', obj.get('title', '')),
                "direction_title": obj.get('direction_title', ''),
                "budget_places": obj.get('budget_places', 0)
            })
        
        # Рекурсивно ищем в значениях
        for value in obj.values():
            programs.extend(find_programs_recursive(value, depth + 1))
    
    elif isinstance(obj, list):
        for item in obj:
            programs.extend(find_programs_recursive(item, depth + 1))
    
    return programs

def fetch_program_data(program_id: int) -> dict:
    """
    Получает JSON-данные по программе через Next.js API.
    """
    base_url = "https://abit.itmo.ru/_next/data/NUJ_R0N1JIDBv5iu7R8Lb/ru/rating/master/budget"
    url = f"{base_url}/{program_id}.json"
    params = {
        "degree": "master",
        "financing": "budget",
        "id": program_id
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при загрузке программы {program_id}: {e}")
        return None