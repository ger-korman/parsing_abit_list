import sqlite3
import json
import requests
import re
from flask import Flask, render_template, jsonify, request, session
from datetime import datetime
import os
from analyzer import analyze_threats, get_competitors_list

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def clean_program_title(title):
    if not title:
        return title
    cleaned = re.sub(r'^\d+\.\d+\.\d+(\s+и\s+\d+\.\d+\.\d+)?\s*', '', title)
    return cleaned

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS programs (
        id INTEGER PRIMARY KEY,
        code TEXT,
        title TEXT,
        budget_places INTEGER,
        update_time TEXT
    )''')
    
    c.execute("PRAGMA table_info(programs)")
    columns = [col[1] for col in c.fetchall()]
    if 'code' not in columns:
        c.execute('ALTER TABLE programs ADD COLUMN code TEXT')
    
    c.execute('''CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id INTEGER,
        sspvo_id TEXT,
        priority INTEGER,
        total_scores REAL,
        exam_scores REAL,
        ia_scores REAL,
        diploma_average REAL,
        is_send_agreement BOOLEAN,
        status TEXT,
        main_top_priority BOOLEAN,
        highest_passageway_priority BOOLEAN,
        position INTEGER,
        snapshot_time TEXT,
        FOREIGN KEY (program_id) REFERENCES programs (id)
    )''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_sspvo ON applicants (sspvo_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_program_time ON applicants (program_id, snapshot_time)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_scores ON applicants (program_id, total_scores, snapshot_time)')
    
    conn.commit()
    conn.close()

def get_all_programs():
    conn = get_db_connection()
    try:
        programs = conn.execute(
            'SELECT id, code, title, budget_places FROM programs ORDER BY code'
        ).fetchall()
        if programs:
            result = []
            for p in programs:
                result.append({
                    'id': p['id'],
                    'code': p['code'],
                    'name': clean_program_title(p['title']),
                    'budget_places': p['budget_places']
                })
            conn.close()
            return result
    except sqlite3.OperationalError:
        pass
    conn.close()
    return []

def will_applicant_stay(conn, applicant_id, current_priority, current_program_id, snapshot_time):
    """
    Проверяет, останется ли абитуриент на текущей программе.
    Возвращает True если останется, False если уйдет на более приоритетную.
    """
    c = conn.cursor()
    
    # Получаем все заявки абитуриента
    c.execute('''SELECT program_id, priority, total_scores, status, position
                 FROM applicants 
                 WHERE sspvo_id = ? AND snapshot_time = ?
                 ORDER BY priority ASC''',
              (applicant_id, snapshot_time))
    
    all_apps = c.fetchall()
    
    for app in all_apps:
        prog_id = app['program_id']
        priority = app['priority']
        position = app['position']
        
        # Если дошли до текущей программы или ниже — дальше не проверяем
        if priority >= current_priority:
            break
        
        # Проверяем, проходит ли он на эту программу
        c.execute('SELECT budget_places FROM programs WHERE id = ?', (prog_id,))
        places_row = c.fetchone()
        places = places_row[0] if places_row else 0
        
        if position <= places:
            return False  # Уйдет на более приоритетную
    
    return True  # Останется здесь

@app.route('/')
def index():
    programs = get_all_programs()
    return render_template('index.html', programs=programs)

@app.route('/api/programs')
def api_programs():
    programs = get_all_programs()
    return jsonify(programs)

@app.route('/api/user_programs')
def user_programs():
    """Находит все программы, где есть данный ID пользователя."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не указан ID'}), 400
    
    conn = get_db_connection()
    
    programs = conn.execute(
        '''SELECT DISTINCT program_id 
           FROM applicants 
           WHERE sspvo_id = ?
           ORDER BY program_id''',
        (user_id,)
    ).fetchall()
    
    if not programs:
        conn.close()
        return jsonify([])
    
    result = []
    
    for p in programs:
        prog_id = p['program_id']
        
        program_info = conn.execute(
            'SELECT code, title, budget_places FROM programs WHERE id = ?',
            (prog_id,)
        ).fetchone()
        
        if not program_info:
            continue
        
        latest = conn.execute(
            'SELECT MAX(snapshot_time) as latest FROM applicants WHERE program_id = ?',
            (prog_id,)
        ).fetchone()
        
        if not latest or not latest['latest']:
            continue
        
        latest_time = latest['latest']
        
        user_data = conn.execute(
            '''SELECT total_scores, position, is_send_agreement, priority
               FROM applicants 
               WHERE program_id = ? AND snapshot_time = ? AND sspvo_id = ?''',
            (prog_id, latest_time, user_id)
        ).fetchone()
        
        if not user_data:
            continue
        
        my_score = user_data['total_scores']
        my_position = user_data['position']
        my_priority = user_data['priority']
        places = program_info['budget_places'] or 0
        
        # ===== ОДИН ЗАПРОС ДЛЯ КОНКУРЕНТОВ =====
        competitors = conn.execute(
            '''SELECT COUNT(*) as cnt
               FROM applicants 
               WHERE program_id = ? 
                 AND snapshot_time = ?
                 AND is_send_agreement = 1
                 AND position < ?
                 AND total_scores >= ?''',
            (prog_id, latest_time, my_position, my_score)
        ).fetchone()
        
        competitors_count = competitors['cnt'] if competitors else 0
        
        # ===== РЕАЛЬНОЕ МЕСТО = ПРОСТО КОНКУРЕНТЫ + 1 =====
        real_position = competitors_count + 1
        
        total_above = conn.execute(
            '''SELECT COUNT(*) as cnt
               FROM applicants 
               WHERE program_id = ? 
                 AND snapshot_time = ?
                 AND position < ?''',
            (prog_id, latest_time, my_position)
        ).fetchone()
        total_above = total_above['cnt'] if total_above else 0
        
        is_safe_by_position = real_position <= places
        
        result.append({
            'program_id': prog_id,
            'code': program_info['code'] or '',
            'title': clean_program_title(program_info['title']),
            'budget_places': places,
            'my_score': my_score,
            'your_position': my_position,
            'real_position': real_position,
            'my_priority': my_priority,
            'is_safe_by_position': is_safe_by_position,
            'competitors_count': competitors_count,
            'total_above': total_above,
            'user_id': user_id,
            'latest_snapshot': latest_time
        })
    
    conn.close()
    
    result.sort(key=lambda x: x['my_priority'] if x['my_priority'] else 999)
    
    return jsonify(result)
    
@app.route('/api/current_status')
def current_status():
    """API: текущий статус."""
    user_id = request.args.get('user_id') or session.get('user_id')
    program_id = request.args.get('program_id') or session.get('program_id')
    
    if not user_id:
        return jsonify({'error': 'Не указан ID пользователя'}), 400
    if not program_id:
        return jsonify({'error': 'Не указана программа'}), 400
    
    try:
        program_id = int(program_id)
    except ValueError:
        return jsonify({'error': 'Неверный формат ID программы'}), 400
    
    conn = get_db_connection()
    
    latest = conn.execute(
        'SELECT MAX(snapshot_time) as latest FROM applicants WHERE program_id = ?',
        (program_id,)
    ).fetchone()
    
    if not latest or not latest['latest']:
        conn.close()
        return jsonify({'error': 'Нет данных по этой программе'})
    
    latest_time = latest['latest']
    
    user_data = conn.execute(
        '''SELECT total_scores, position, is_send_agreement, priority
           FROM applicants 
           WHERE program_id = ? AND snapshot_time = ? AND sspvo_id = ?''',
        (program_id, latest_time, user_id)
    ).fetchone()
    
    if not user_data:
        conn.close()
        return jsonify({'error': f'Пользователь {user_id} не найден в списке'})
    
    my_score = user_data['total_scores']
    my_position = user_data['position']
    my_priority = user_data['priority']
    
    places = conn.execute(
        'SELECT budget_places FROM programs WHERE id = ?', (program_id,)
    ).fetchone()
    places = places['budget_places'] if places else 0
    
    program_info = conn.execute(
        'SELECT code, title FROM programs WHERE id = ?', (program_id,)
    ).fetchone()
    
    # ===== ИСПОЛЬЗУЕМ analyze_threats() ДЛЯ ВСЕХ РАСЧЕТОВ =====
    from analyzer import analyze_threats
    threat = analyze_threats(conn, program_id, user_id, my_score)
    
    if threat:
        real_position = threat.get('real_position', my_position)
        competitors_count = threat.get('competitors_count', 0)
        real_threats = threat.get('real_threats', 0)
        potential_escapees = threat.get('potential_escapees', 0)
        is_safe = threat.get('is_safe_by_position', real_position <= places)
        needs_to_leave = threat.get('needs_to_leave', max(0, real_position - places))
    else:
        # Если analyze_threats вернул None — считаем вручную
        competitors = conn.execute(
            '''SELECT COUNT(*) as cnt
               FROM applicants 
               WHERE program_id = ? 
                 AND snapshot_time = ?
                 AND is_send_agreement = 1
                 AND position < ?
                 AND total_scores >= ?''',
            (program_id, latest_time, my_position, my_score)
        ).fetchone()
        competitors_count = competitors['cnt'] if competitors else 0
        real_position = competitors_count + 1
        real_threats = 0
        potential_escapees = 0
        is_safe = real_position <= places
        needs_to_leave = max(0, real_position - places)
    
    # ===== ВСЕ АБИТУРИЕНТЫ =====
    all_applicants = conn.execute(
        '''SELECT sspvo_id, total_scores, priority, status, position,
                  diploma_average, is_send_agreement
           FROM applicants 
           WHERE program_id = ? AND snapshot_time = ?
           ORDER BY position ASC''',
        (program_id, latest_time)
    ).fetchall()
    
    # ===== КОНКУРЕНТЫ ДЛЯ ТАБЛИЦЫ =====
    competitors_list = conn.execute(
        '''SELECT sspvo_id, priority, total_scores, status, position
           FROM applicants 
           WHERE program_id = ? 
             AND snapshot_time = ?
             AND is_send_agreement = 1
             AND position < ?
             AND total_scores >= ?
           ORDER BY position ASC
           LIMIT 50''',
        (program_id, latest_time, my_position, my_score)
    ).fetchall()
    
    conn.close()
    
    return jsonify({
        'user_id': user_id,
        'program_id': program_id,
        'program_title': f"{program_info['code']} - {clean_program_title(program_info['title'])}" if program_info else str(program_id),
        'my_score': my_score,
        'my_priority': my_priority,
        'your_position': my_position,
        'real_position': real_position,
        'budget_places': places,
        'competitors_count': competitors_count,
        'total_above': threat.get('total_above', 0) if threat else 0,
        'real_threats': real_threats,
        'potential_escapees': potential_escapees,
        'is_safe': is_safe,
        'needs_to_leave': needs_to_leave,
        'latest_snapshot': latest_time,
        'all_applicants': [dict(row) for row in all_applicants],
        'competitors': [dict(row) for row in competitors_list]
    })
@app.route('/api/history')
def history():
    """API: история позиции (по списку и реальной)."""
    user_id = request.args.get('user_id') or session.get('user_id')
    program_id = request.args.get('program_id') or session.get('program_id')
    
    if not user_id or not program_id:
        return jsonify({'error': 'Не указаны данные'}), 400
    
    try:
        program_id = int(program_id)
    except ValueError:
        return jsonify({'error': 'Неверный формат ID программы'}), 400
    
    conn = get_db_connection()
    
    # Получаем все снапшоты по порядку
    history_data = conn.execute(
        '''SELECT snapshot_time, position, total_scores
           FROM applicants
           WHERE program_id = ? AND sspvo_id = ?
           ORDER BY snapshot_time''',
        (program_id, user_id)
    ).fetchall()
    
    if not history_data:
        conn.close()
        return jsonify({'times': [], 'positions': [], 'real_positions': []})
    
    times = []
    positions = []
    real_positions = []
    
    for row in history_data:
        snap_time = row['snapshot_time']
        position = row['position']
        score = row['total_scores']
        
        # Реальное место = все с баллом выше И с согласием И балл >= 60
        real_pos = conn.execute(
            '''SELECT COUNT(*)  as real_pos
               FROM applicants s2
               WHERE program_id = ? 
                 AND snapshot_time = ?
                 AND is_send_agreement = 1
                 AND total_scores > ?
                 AND total_scores >= 60''',  # Минимальный балл
            (program_id, snap_time, score)
        ).fetchone()
        
        real_position = real_pos['real_pos'] if real_pos else position
        
        times.append(snap_time)
        positions.append(position)
        real_positions.append(real_position)
    
    conn.close()
    
    return jsonify({
        'times': times,
        'positions': positions,
        'real_positions': real_positions
    })

@app.route('/api/delete_user_program', methods=['POST'])
def delete_user_program():
    """Удаляет программу из просмотра (не из БД, просто скрывает)."""
    # Просто возвращаем OK — мы не удаляем данные из БД
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)