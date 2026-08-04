# parser.py
import json
from datetime import datetime
from typing import List, Dict

def extract_applicants(data: dict, program_id: int) -> List[Dict]:
    """
    Извлекает список абитуриентов из JSON-ответа.
    """
    try:
        program_list = data.get("pageProps", {}).get("programList", {})
        applicants = program_list.get("general_competition", [])
        
        result = []
        for app in applicants:
            result.append({
                "program_id": program_id,
                "sspvo_id": app.get("sspvo_id"),
                "priority": app.get("priority"),
                "total_scores": app.get("total_scores", 0),
                "exam_scores": app.get("exam_scores", 0),
                "ia_scores": app.get("ia_scores", 0),
                "diploma_average": app.get("diploma_average"),
                "is_send_agreement": app.get("is_send_agreement", False),
                "status": app.get("status"),
                "main_top_priority": app.get("main_top_priority", False),
                "highest_passageway_priority": app.get("highest_passageway_priority", False),
                "position": app.get("position"),
                "contest": app.get("contest"),
                "exam_type": app.get("exam_type"),
            })
        
        return result
    except (KeyError, TypeError) as e:
        print(f"Ошибка парсинга данных: {e}")
        return []

def get_update_time(data: dict) -> str:
    """
    Возвращает время обновления данных.
    """
    try:
        return data.get("pageProps", {}).get("programList", {}).get("update_time", "")
    except (KeyError, TypeError):
        return ""

def get_budget_places(data: dict) -> int:
    """
    Возвращает количество бюджетных мест.
    """
    try:
        direction = data.get("pageProps", {}).get("programList", {}).get("direction", {})
        return direction.get("budget_min", 0)
    except (KeyError, TypeError):
        return 0