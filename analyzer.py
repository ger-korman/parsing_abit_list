import sqlite3
from config import DB_PATH

def get_program_budget_places(conn, program_id):
    c = conn.cursor()
    c.execute('SELECT budget_places FROM programs WHERE id = ?', (program_id,))
    row = c.fetchone()
    return row[0] if row else 0

def will_applicant_stay_optimized(conn, applicant_id, max_priority, snapshot_time):
    """
    Оптимизированная проверка: проходит ли абитуриент на программы с приоритетом < max_priority.
    Возвращает False (уйдет), если находит хотя бы одну программу выше по приоритету, куда он проходит.
    """
    c = conn.cursor()
    
    # Получаем все программы абитуриента с приоритетом строго ВЫШЕ (меньше число), чем текущий
    c.execute('''SELECT program_id, priority, position
                 FROM applicants 
                 WHERE sspvo_id = ? AND snapshot_time = ? AND priority < ?
                 ORDER BY priority ASC''',
              (applicant_id, snapshot_time, max_priority))
    
    higher_priority_apps = c.fetchall()
    
    for prog_id, priority, position in higher_priority_apps:
        places = get_program_budget_places(conn, prog_id)
        
        # Если он проходит на более приоритетную программу по месту в списке
        if position <= places:
            return False # Он уйдет
            
    return True # Не уходит (остается конкурентом)

def analyze_threats(conn, program_id, my_sspvo_id, my_score):
    """
    Анализирует угрозы для выбранной программы.
    Учитываются ТОЛЬКО люди, стоящие выше по списку!
    """
    c = conn.cursor()
    
    # 1. Последний снапшот
    c.execute('SELECT MAX(snapshot_time) FROM applicants WHERE program_id = ?', (program_id,))
    result = c.fetchone()
    if not result or not result[0]:
        return None
    
    latest_time = result[0]
    
    # 2. Позиция пользователя
    c.execute('''SELECT position FROM applicants 
                 WHERE program_id = ? AND snapshot_time = ? AND sspvo_id = ?''',
              (program_id, latest_time, my_sspvo_id))
    user_pos = c.fetchone()
    if not user_pos:
        return None
    
    my_position = user_pos[0]
    
    # ===== ВЫБОРКА ВСЕХ ВОЗМОЖНЫХ КОНКУРЕНТОВ (СТРОГО ВЫШЕ ПО СПИСКУ) =====
    # Жесткий фильтр по позиции: position < my_position
    c.execute('''SELECT sspvo_id, priority
                 FROM applicants 
                 WHERE program_id = ? 
                   AND snapshot_time = ?
                   AND position < ?       -- Обязательно ВЫШЕ по списку
                   AND sspvo_id != ?      -- Не я
                   AND is_send_agreement = 1 -- Обязательно есть согласие
                 ORDER BY position ASC''',
              (program_id, latest_time, my_position, my_sspvo_id))
    
    higher_applicants = c.fetchall()
    
    real_competitors = 0
    potential_escapees = 0
    
    # Анализируем каждого абитуриента выше по списку
    for app in higher_applicants:
        sspvo_id, priority = app
        
        # Если у него приоритет равен 1, он автоматически остается (некуда уходить)
        if priority == 1:
            real_competitors += 1
            continue
            
        # Если приоритет больше 1, проверяем, уходит ли он наверх
        # Передаем max_priority = priority (будет проверять только программы с приоритетом меньше этого числа)
        stays_here = will_applicant_stay_optimized(conn, sspvo_id, priority, latest_time)
        
        if stays_here:
            real_competitors += 1     # Останется здесь - КОНКУРЕНТ
        else:
            potential_escapees += 1   # Уйдет наверх

    real_position = real_competitors + 1
    places = get_program_budget_places(conn, program_id)
    
    return {
        "snapshot_time": latest_time,
        "places": places,
        "competitors_count": real_competitors,
        "real_position": real_position,
        "is_safe_by_position": real_position <= places,
        "needs_to_leave": max(0, real_position - places),
        "my_position": my_position,
        "my_score": my_score
    }

def get_competitors_list(conn, program_id, my_sspvo_id, my_score, limit=50):
    """
    Возвращает список ВСЕХ, кто стоит выше по списку (с детальным анализом).
    """
    c = conn.cursor()
    
    c.execute('SELECT MAX(snapshot_time) FROM applicants WHERE program_id = ?', (program_id,))
    result = c.fetchone()
    if not result or not result[0]:
        return []
    
    latest_time = result[0]
    
    c.execute('''SELECT position FROM applicants 
                 WHERE program_id = ? AND snapshot_time = ? AND sspvo_id = ?''',
              (program_id, latest_time, my_sspvo_id))
    user_pos = c.fetchone()
    if not user_pos:
        return []
    
    my_position = user_pos[0]
    
    # ВАЖНО: Сначала фильтруем ТОЛЬКО тех, кто ВЫШЕ по списку (position < my_position)
    c.execute('''SELECT sspvo_id, priority, total_scores, status, position,
                        is_send_agreement
                 FROM applicants 
                 WHERE program_id = ? 
                   AND snapshot_time = ? 
                   AND position < ? -- Только те, кто ВЫШЕ!
                 ORDER BY position ASC
                 LIMIT ?''',
              (program_id, latest_time, my_position, limit))
    
    applicants = c.fetchall()
    
    result_list = []
    for app in applicants:
        sspvo_id, priority, score, status, position, has_consent = app
        
        # 1. Если нет согласия - сразу статус "не претендует"
        if not has_consent:
            result_list.append({
                "sspvo_id": sspvo_id,
                "total_scores": score,
                "priority": priority,
                "position": position,
                "is_send_agreement": has_consent,
                "will_stay": False,
                "reason": "❌ Не претендует (нет согласия)",
                "badge_type": "без согласия"
            })
            continue
            
        # 2. Если есть согласие и приоритет 1 - гарантированно остается
        if priority == 1:
            result_list.append({
                "sspvo_id": sspvo_id,
                "total_scores": score,
                "priority": priority,
                "position": position,
                "is_send_agreement": has_consent,
                "will_stay": True,
                "reason": "⚠️ Останется (приоритет 1)",
                "badge_type": "останется"
            })
            continue
            
        # 3. Если приоритет > 1, проверяем уход наверх
        stays_here = will_applicant_stay_optimized(conn, sspvo_id, priority, latest_time)
            
        if stays_here:
            result_list.append({
                "sspvo_id": sspvo_id,
                "total_scores": score,
                "priority": priority,
                "position": position,
                "is_send_agreement": has_consent,
                "will_stay": True,
                "reason": "⚠️ Останется (не проходит на более высокий приоритет)",
                "badge_type": "останется"
            })
        else:
            result_list.append({
                "sspvo_id": sspvo_id,
                "total_scores": score,
                "priority": priority,
                "position": position,
                "is_send_agreement": has_consent,
                "will_stay": False,
                "reason": "✅ Уходит на более приоритетную программу",
                "badge_type": "уйдет"
            })
    
    return result_list