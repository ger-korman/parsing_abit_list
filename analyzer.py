# analyzer.py
import sqlite3
from config import DB_PATH, MY_SSPVO_ID, MY_PROGRAM_ID, MY_SCORE


def get_applicant_applications(conn, applicant_id: str, snapshot_time: str):
    """
    Получает все заявки абитуриента на разные программы в текущем снапшоте.
    """
    c = conn.cursor()
    c.execute('''SELECT program_id, priority, total_scores, status, position
                 FROM applicants 
                 WHERE sspvo_id = ? AND snapshot_time = ?
                 ORDER BY priority ASC''',
              (applicant_id, snapshot_time))
    return c.fetchall()


def get_program_budget_places(conn, program_id: int):
    """Возвращает количество бюджетных мест на программе."""
    c = conn.cursor()
    c.execute('SELECT budget_places FROM programs WHERE id = ?', (program_id,))
    row = c.fetchone()
    return row[0] if row else 0


def get_applicant_rank_on_program(conn, applicant_id: str, program_id: int, snapshot_time: str):
    """
    Возвращает позицию абитуриента на конкретной программе.
    """
    c = conn.cursor()
    c.execute('''SELECT position 
                 FROM applicants 
                 WHERE sspvo_id = ? AND program_id = ? AND snapshot_time = ?
                 ORDER BY snapshot_time DESC LIMIT 1''',
              (applicant_id, program_id, snapshot_time))
    row = c.fetchone()
    return row[0] if row else None


def is_applicant_passing(conn, applicant_id: str, program_id: int, snapshot_time: str):
    """
    Проверяет, проходит ли абитуриент на программу.
    Условие: его позиция на программе <= количество бюджетных мест.
    """
    rank = get_applicant_rank_on_program(conn, applicant_id, program_id, snapshot_time)
    if rank is None:
        return False
    
    places = get_program_budget_places(conn, program_id)
    return rank <= places


def will_applicant_stay(conn, applicant_id: str, current_priority: int, current_program_id: int, snapshot_time: str):
    """
    Проверяет, останется ли абитуриент на текущей программе.
    Возвращает:
        - True: останется (это конкурент)
        - False: уйдет на более приоритетную программу (не конкурент)
    """
    # Получаем все заявки абитуриента, отсортированные по приоритету
    all_apps = get_applicant_applications(conn, applicant_id, snapshot_time)
    
    # Проходим по всем его заявкам с приоритетом выше текущего
    for app in all_apps:
        prog_id, priority, total_scores, status, position = app
        
        # Если дошли до текущей программы или ниже — проверяем только выше
        if priority >= current_priority:
            break
        
        # Проверяем, проходит ли он на эту более приоритетную программу
        if is_applicant_passing(conn, applicant_id, prog_id, snapshot_time):
            # Он проходит на более приоритетную программу — уйдет от вас
            return False
    
    # Если не прошел ни на одну из более приоритетных программ
    # ИЛИ у него нет других заявок с более высоким приоритетом
    return True


def analyze_threats(conn, program_id: int, my_sspvo_id: str, my_score: float):
    """
    Анализирует угрозы для вашей программы.
    Возвращает словарь с результатами анализа.
    """
    c = conn.cursor()
    
    # Получаем последний снапшот
    c.execute('SELECT MAX(snapshot_time) FROM applicants WHERE program_id = ?', (program_id,))
    result = c.fetchone()
    if not result or not result[0]:
        return None
    
    latest_time = result[0]
    
    # 1. Получаем всех абитуриентов с баллом выше вашего
    c.execute('''SELECT sspvo_id, priority, total_scores, status, position,
                        is_send_agreement, diploma_average
                 FROM applicants 
                 WHERE program_id = ? 
                   AND snapshot_time = ? 
                   AND total_scores > ?
                 ORDER BY total_scores DESC''',
              (program_id, latest_time, my_score))
    
    above_me = c.fetchall()
    
    real_threats = 0       # Останутся здесь (конкуренты)
    potential_escapees = 0 # Уйдут на другие программы
    no_consent = 0         # Нет согласия на зачисление
    total_above = len(above_me)
    
    for applicant in above_me:
        sspvo_id, priority, score, status, position, has_consent, avg_grade = applicant
        
        # Если нет согласия — не конкурент
        if not has_consent:
            no_consent += 1
            continue
        
        # Если статус "pass_another" — уже проходит на другую программу
        if status == "pass_another" or status == "recommended_other":
            potential_escapees += 1
            continue
        
        # Если приоритет == 1 — это его главная цель, останется
        if priority == 1:
            real_threats += 1
            continue
        
        # Если приоритет > 1 — проверяем, не уйдет ли он на более приоритетную программу
        if will_applicant_stay(conn, sspvo_id, priority, program_id, latest_time):
            # Не проходит на более приоритетные — останется здесь
            real_threats += 1
        else:
            # Проходит на более приоритетную — уйдет
            potential_escapees += 1
    
    # Получаем количество бюджетных мест
    places = get_program_budget_places(conn, program_id)
    
    # Ваша позиция среди всех (с учетом согласия)
    c.execute('''SELECT COUNT(*) + 1 FROM applicants 
                 WHERE program_id = ? AND snapshot_time = ? 
                   AND total_scores > ?''',
              (program_id, latest_time, my_score))
    your_position = c.fetchone()[0]
    
    # Ваша позиция среди реальных конкурентов (без тех, кто уйдет)
    real_position = real_threats + 1
    
    return {
        "snapshot_time": latest_time,
        "places": places,
        "total_above": total_above,
        "real_threats": real_threats,
        "potential_escapees": potential_escapees,
        "no_consent": no_consent,
        "your_position": your_position,
        "real_position": real_position,
        "is_safe": real_position <= places,
        "needs_to_leave": max(0, real_position - places)  # Сколько должно уйти
    }


def get_competitors_list(conn, program_id: int, my_sspvo_id: str, my_score: float, limit: int = 20):
    """
    Возвращает список конкурентов с анализом для каждого.
    """
    c = conn.cursor()
    
    # Последний снапшот
    c.execute('SELECT MAX(snapshot_time) FROM applicants WHERE program_id = ?', (program_id,))
    result = c.fetchone()
    if not result or not result[0]:
        return []
    
    latest_time = result[0]
    
    # Получаем всех абитуриентов с баллом выше вашего
    c.execute('''SELECT sspvo_id, priority, total_scores, status, position,
                        is_send_agreement, diploma_average
                 FROM applicants 
                 WHERE program_id = ? 
                   AND snapshot_time = ? 
                   AND total_scores > ?
                 ORDER BY position ASC
                 LIMIT ?''',
              (program_id, latest_time, my_score, limit))
    
    above_me = c.fetchall()
    
    competitors = []
    for applicant in above_me:
        sspvo_id, priority, score, status, position, has_consent, avg_grade = applicant
        
        # Определяем, останется ли абитуриент
        if not has_consent:
            will_stay = False
            reason = "Нет согласия на зачисление"
        elif status == "pass_another" or status == "recommended_other":
            will_stay = False
            reason = "Проходит на другую программу"
        elif priority == 1:
            will_stay = True
            reason = "Главный приоритет"
        else:
            will_stay = will_applicant_stay(conn, sspvo_id, priority, program_id, latest_time)
            reason = "Останется здесь" if will_stay else "Уйдет на более приоритетную"
        
        competitors.append({
            "sspvo_id": sspvo_id,
            "total_scores": score,
            "priority": priority,
            "status": status,
            "position": position,
            "is_send_agreement": has_consent,
            "diploma_average": avg_grade,
            "will_stay": will_stay,
            "reason": reason
        })
    
    return competitors


if __name__ == "__main__":
    # Тестовый запуск
    conn = sqlite3.connect(DB_PATH)
    
    result = analyze_threats(conn, MY_PROGRAM_ID, MY_SSPVO_ID, MY_SCORE)
    if result:
        print("📊 АНАЛИЗ УГРОЗ:")
        print(f"  Бюджетных мест: {result['places']}")
        print(f"  Всего выше вас: {result['total_above']}")
        print(f"  Реально останутся: {result['real_threats']}")
        print(f"  Уйдут на другие: {result['potential_escapees']}")
        print(f"  Без согласия: {result['no_consent']}")
        print(f"  Ваше реальное место: {result['real_position']}")
        print(f"  Статус: {'✅ ПРОХОДИТЕ!' if result['is_safe'] else '❌ В ЗОНЕ РИСКА'}")
        if not result['is_safe']:
            print(f"  Должно уйти: {result['needs_to_leave']} человек")
    
    conn.close()