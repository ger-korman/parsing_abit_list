# config.py
import os

# Базовый URL для API
BASE_URL = "https://abit.itmo.ru/_next/data/NUJ_R0N1JIDBv5iu7R8Lb/ru/rating/master/budget"
DEGREE = "master"
FINANCING = "budget"

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

# Ваши данные для анализа (замените на свои)
MY_SSPVO_ID = "2384002"  # Ваш sspvo_id (из JSON)
MY_PROGRAM_ID = 2362     # ID вашей программы
MY_SCORE = 100.0         # Ваш балл total_scores

# Настройки уведомлений
TELEGRAM_TOKEN = None    # Если есть бот
TELEGRAM_CHAT_ID = None  # Если есть бот

# Интервал проверки (секунды)
CHECK_INTERVAL = 600  # 10 минут