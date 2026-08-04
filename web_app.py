# web_app.py
import sqlite3
import json
import requests
import re
from flask import Flask, render_template, jsonify, request, session
from datetime import datetime
import os
from analyzer import analyze_threats, get_competitors_list  # <-- Добавляем импорт

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def clean_program_title(title):
    """Убирает код специальности из начала названия."""
    if not title:
        return title
    cleaned = re.sub(r'^\d+\.\d+\.\d+(\s+и\s+\d+\.\d+\.\d+)?\s*', '', title)
    return cleaned

def init_db():
    """Создает таблицы с правильной структурой."""
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY,
        program_id INTEGER,
        updated_at TEXT
    )''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_sspvo ON applicants (sspvo_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_program_time ON applicants (program_id, snapshot_time)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_scores ON applicants (program_id, total_scores, snapshot_time)')
    
    conn.commit()
    conn.close()

def get_all_programs():
    """Получает список программ из БД."""
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

@app.route('/')
def index():
    """Главная страница."""
    programs = get_all_programs()
    return render_template('index.html', programs=programs)

@app.route('/api/programs')
def api_programs():
    """API: список всех программ."""
    programs = get_all_programs()
    return jsonify(programs)

@app.route('/api/save_user', methods=['POST'])
def save_user():
    """Сохраняет/обновляет данные пользователя."""
    data = request.json
    user_id = data.get('user_id')
    program_id = data.get('program_id')
    
    if not user_id or not program_id:
        return jsonify({'error': 'Не указан ID или программа'}), 400
    
    session['user_id'] = user_id
    session['program_id'] = program_id
    
    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO user_settings (user_id, program_id, updated_at) 
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET 
               program_id = excluded.program_id,
               updated_at = excluded.updated_at''',
        (user_id, program_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok', 'user_id': user_id, 'program_id': program_id})

@app.route('/api/current_status')
def current_status():
    """API: текущий статус с полным анализом."""
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
    
    # 1. Проверяем наличие данных
    latest = conn.execute(
        'SELECT MAX(snapshot_time) as latest FROM applicants WHERE program_id = ?',
        (program_id,)
    ).fetchone()
    
    if not latest or not latest['latest']:
        conn.close()
        return jsonify({'error': 'Нет данных по этой программе. Запустите парсер.'})
    
    latest_time = latest['latest']
    
    # 2. Получаем данные пользователя
    user_data = conn.execute(
        '''SELECT total_scores, position, is_send_agreement 
           FROM applicants 
           WHERE program_id = ? AND snapshot_time = ? AND sspvo_id = ?''',
        (program_id, latest_time, user_id)
    ).fetchone()
    
    if not user_data:
        conn.close()
        return jsonify({'error': f'Пользователь {user_id} не найден в списке'})
    
    my_score = user_data['total_scores']
    my_position = user_data['position']
    has_agreement = user_data['is_send_agreement']
    
    # 3. Получаем количество бюджетных мест
    places = conn.execute(
        'SELECT budget_places FROM programs WHERE id = ?', (program_id,)
    ).fetchone()
    places = places['budget_places'] if places else 0
    
    # 4. Получаем информацию о программе
    program_info = conn.execute(
        'SELECT code, title FROM programs WHERE id = ?', (program_id,)
    ).fetchone()
    
    # 5. АНАЛИЗ УГРОЗ (новая функция из analyzer.py)
    threat_analysis = analyze_threats(conn, program_id, user_id, my_score)
    
    # 6. СПИСОК КОНКУРЕНТОВ С АНАЛИЗОМ (новая функция из analyzer.py)
    competitors_list = get_competitors_list(conn, program_id, user_id, my_score, limit=20)
    
    conn.close()
    
    # Формируем ответ
    response = {
        'user_id': user_id,
        'program_id': program_id,
        'program_title': f"{program_info['code']} - {clean_program_title(program_info['title'])}" if program_info else str(program_id),
        'my_score': my_score,
        'my_position': my_position,
        'has_agreement': has_agreement,
        'latest_snapshot': latest_time,
        'budget_places': places,
        'total_applicants': threat_analysis.get('total_above', 0) + 1 if threat_analysis else 0,
        'is_safe': threat_analysis.get('is_safe', False) if threat_analysis else (my_position <= places),
    }
    
    # Добавляем данные анализа, если они есть
    if threat_analysis:
        response.update({
            'your_position': my_position,
            'real_position': threat_analysis.get('real_position', my_position),
            'real_threats': threat_analysis.get('real_threats', 0),
            'potential_escapees': threat_analysis.get('potential_escapees', 0),
            'no_consent': threat_analysis.get('no_consent', 0),
            'needs_to_leave': threat_analysis.get('needs_to_leave', 0),
            'total_above': threat_analysis.get('total_above', 0),
            'is_safe': threat_analysis.get('is_safe', False),
        })
    else:
        response.update({
            'real_position': my_position,
            'real_threats': 0,
            'potential_escapees': 0,
            'no_consent': 0,
            'needs_to_leave': 0,
            'total_above': 0,
        })
    
    # Добавляем список конкурентов с анализом
    response['competitors'] = competitors_list
    
    return jsonify(response)

@app.route('/api/history')
def history():
    """API: история позиции."""
    user_id = request.args.get('user_id') or session.get('user_id')
    program_id = request.args.get('program_id') or session.get('program_id')
    
    if not user_id or not program_id:
        return jsonify({'error': 'Не указаны данные'}), 400
    
    try:
        program_id = int(program_id)
    except ValueError:
        return jsonify({'error': 'Неверный формат ID программы'}), 400
    
    conn = get_db_connection()
    
    history_data = conn.execute(
        '''SELECT snapshot_time, position
           FROM applicants
           WHERE program_id = ? AND sspvo_id = ?
           ORDER BY snapshot_time''',
        (program_id, user_id)
    ).fetchall()
    
    conn.close()
    
    return jsonify({
        'times': [row['snapshot_time'] for row in history_data],
        'positions': [row['position'] for row in history_data]
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)