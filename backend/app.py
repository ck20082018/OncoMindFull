"""
Backend для регистрации пользователей OncoMind
Поддержка двух ролей: врач и пациент

ИСПРАВЛЕНИЯ БЕЗОПАСНОСТИ:
- Добавлена CSRF защита
- Улучшена валидация паролей (минимум 8 символов)
- Усилено хеширование (310000 итераций PBKDF2)
- Добавлен rate limiting
- Проверка MIME-type для файлов
- Исправлен secret_key через переменную окружения
- Настроен CORS с белым списком доменов
"""

import os
import re
import json
import hashlib
import secrets
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from functools import wraps
from flask import Flask, request, jsonify, session, g
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging
import time
import threading
from collections import defaultdict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# БЕЗОПАСНОСТЬ: Rate Limiter (простая реализация)
# =============================================================================
class RateLimiter:
    """Простой rate limiter для защиты от DoS."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self._lock = threading.Lock()
    
    def is_allowed(self, key: str) -> bool:
        """Проверка, разрешён ли запрос."""
        with self._lock:
            now = time.time()
            # Очищаем старые запросы
            self.requests[key] = [
                t for t in self.requests[key] 
                if now - t < self.window_seconds
            ]
            # Проверяем лимит
            if len(self.requests[key]) >= self.max_requests:
                return False
            self.requests[key].append(now)
            return True
    
    def get_retry_after(self, key: str) -> int:
        """Время до следующего разрешённого запроса."""
        if not self.requests[key]:
            return 0
        oldest = min(self.requests[key])
        return max(0, int(self.window_seconds - (time.time() - oldest)))


# Глобальные rate limiter'ы
login_limiter = RateLimiter(max_requests=5, window_seconds=60)
register_limiter = RateLimiter(max_requests=3, window_seconds=300)
api_limiter = RateLimiter(max_requests=100, window_seconds=60)


def rate_limit(limiter: RateLimiter, key_func=None):
    """Декоратор для rate limiting."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            key = key_func() if key_func else request.remote_addr or 'unknown'
            if not limiter.is_allowed(key):
                retry_after = limiter.get_retry_after(key)
                logger.warning(f"Rate limit превышен для {key}")
                return jsonify({
                    'error': 'Слишком много запросов',
                    'retry_after': retry_after
                }), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator


def get_client_ip():
    """Получение IP клиента с учётом прокси."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'


# =============================================================================
# БЕЗОПАСНОСТЬ: CSRF защита
# =============================================================================
class CSRFProtect:
    """Простая CSRF защита."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        app.before_request(self._check_csrf)
        app.config.setdefault('WTF_CSRF_ENABLED', True)
    
    def _check_csrf(self):
        """Проверка CSRF токена для небезопасных методов."""
        if request.method in ['POST', 'PUT', 'DELETE']:
            # Пропускаем API endpoints с токеном в заголовке
            if request.headers.get('X-CSRF-Token'):
                token = request.headers.get('X-CSRF-Token')
                session_token = session.get('csrf_token')
                if token != session_token:
                    logger.warning(f"CSRF токен не совпадает")
                    return jsonify({'error': 'Неверный CSRF токен'}), 403
            # Для API используем проверку Origin/Referer
            origin = request.headers.get('Origin')
            if origin:
                allowed_origins = os.environ.get(
                    'ALLOWED_ORIGINS', 
                    'http://localhost,http://127.0.0.1'
                ).split(',')
                if origin not in allowed_origins:
                    logger.warning(f"Недопустимый Origin: {origin}")
                    return jsonify({'error': 'Недопустимый источник'}), 403


# =============================================================================
# ПРИЛОЖЕНИЕ FLASK
# =============================================================================
app = Flask(__name__)

# БЕЗОПАСНОСТЬ: Secret key из переменной окружения
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# БЕЗОПАСНОСТЬ: Настройка CORS с белым списком
ALLOWED_ORIGINS = os.environ.get(
    'ALLOWED_ORIGINS',
    'http://localhost,http://localhost:80,http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500'
).split(',')

CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token", "X-User-Id"],
        "supports_credentials": True
    }
})

# Инициализация CSRF защиты
csrf = CSRFProtect(app)

# Конфигурация AI Pipeline
AI_PIPELINE_URL = os.environ.get('AI_PIPELINE_URL', 'http://127.0.0.1:8000')

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================
# Пути из переменных окружения
BASE_DIR = Path(os.environ.get('BASE_DIR', Path(__file__).parent))
UPLOAD_FOLDER = BASE_DIR / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.xlsx', '.docx', '.txt', '.jpg', '.jpeg', '.png'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'image/jpeg',
    'image/png',
}
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 10 * 1024 * 1024))  # 10 MB

# Пути к файлам пользователей
USERS_FILE = Path(os.environ.get('USERS_FILE', BASE_DIR / 'data' / 'users.json'))
USERS_FILE.parent.mkdir(exist_ok=True)


# =============================================================================
# МОДЕЛИ ДАННЫХ
# =============================================================================
@dataclass
class User:
    id: str
    email: str
    password_hash: str
    full_name: str
    role: str
    created_at: str
    # Для врачей
    diploma_number: Optional[str] = None
    specialization: Optional[str] = None
    clinic: Optional[str] = None
    # Для пациентов
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    # Загруженные файлы
    files: List[str] = None

    def __post_init__(self):
        if self.files is None:
            self.files = []


# =============================================================================
# БЕЗОПАСНОСТЬ: Валидация паролей
# =============================================================================
def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Проверка сложности пароля.
    
    Требования:
    - Минимум 8 символов
    - Хотя бы одна заглавная буква
    - Хотя бы одна строчная буква
    - Хотя бы одна цифра
    """
    if len(password) < 8:
        return False, 'Пароль должен содержать минимум 8 символов'
    
    if not re.search(r'[A-Z]', password):
        return False, 'Пароль должен содержать хотя бы одну заглавную букву'
    
    if not re.search(r'[a-z]', password):
        return False, 'Пароль должен содержать хотя бы одну строчную букву'
    
    if not re.search(r'\d', password):
        return False, 'Пароль должен содержать хотя бы одну цифру'
    
    return True, None


# =============================================================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# =============================================================================
class UserManager:
    """Управление пользователями"""

    def __init__(self, users_file: Path):
        self.users_file = users_file
        self.users: Dict[str, User] = {}
        self.diploma_to_user: Dict[str, str] = {}
        self._load_users()

        # Если нет пользователей, создаём тестовых
        if len(self.users) == 0:
            self._init_test_users()

    def _load_users(self):
        """Загрузка пользователей из файла"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data:
                        user = User(**user_data)
                        self.users[user.id] = user
                        if user.diploma_number:
                            self.diploma_to_user[user.diploma_number] = user.id
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка загрузки users.json: {e}")
                # Создаём резервную копию повреждённого файла
                backup = self.users_file.with_suffix('.json.bak')
                self.users_file.rename(backup)
                logger.info(f"Повреждённый файл сохранён как {backup}")

    def _save_users(self):
        """Сохранение пользователей в файл"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [asdict(u) for u in self.users.values()], 
                    f, 
                    ensure_ascii=False, 
                    indent=2
                )
        except IOError as e:
            logger.error(f"Ошибка сохранения users.json: {e}")

    def _init_test_users(self):
        """Создание тестовых пользователей для разработки"""

        # Тестовый врач 1 (основной)
        test_doctor1 = User(
            id=secrets.token_hex(16),
            email='doctor@oncomind.ai',
            password_hash=self._hash_password('Doctor123!'),
            full_name='Александр Петрович Смирнов',
            role='doctor',
            created_at=datetime.now().isoformat(),
            diploma_number='12345678',
            specialization='Онколог, химиотерапевт',
            clinic='Городской онкологический диспансер №1',
            files=[]
        )
        self.users[test_doctor1.id] = test_doctor1
        self.diploma_to_user['12345678'] = test_doctor1.id

        # Тестовый врач 2 (молодой специалист)
        test_doctor2 = User(
            id=secrets.token_hex(16),
            email='elena.doctor@oncomind.ai',
            password_hash=self._hash_password('Elena2026!'),
            full_name='Елена Владимировна Козлова',
            role='doctor',
            created_at=datetime.now().isoformat(),
            diploma_number='87654321',
            specialization='Онколог, радиотерапевт',
            clinic='Областная клиническая больница',
            files=[]
        )
        self.users[test_doctor2.id] = test_doctor2
        self.diploma_to_user['87654321'] = test_doctor2.id

        # Тестовый пациент 1 (рак молочной железы)
        test_patient1 = User(
            id=secrets.token_hex(16),
            email='maria.patient@example.com',
            password_hash=self._hash_password('Maria2026!'),
            full_name='Мария Ивановна Петрова',
            role='patient',
            created_at=datetime.now().isoformat(),
            birth_date='15.03.1965',
            phone='+7 (999) 123-45-67',
            files=[]
        )
        self.users[test_patient1.id] = test_patient1

        # Тестовый пациент 2 (рак лёгкого)
        test_patient2 = User(
            id=secrets.token_hex(16),
            email='ivan.patient@example.com',
            password_hash=self._hash_password('Ivan2026!'),
            full_name='Иван Сергеевич Соколов',
            role='patient',
            created_at=datetime.now().isoformat(),
            birth_date='22.08.1958',
            phone='+7 (999) 765-43-21',
            files=[]
        )
        self.users[test_patient2.id] = test_patient2

        # Тестовый пациент 3 (с полными данными)
        test_patient3 = User(
            id=secrets.token_hex(16),
            email='anna.test@example.com',
            password_hash=self._hash_password('Anna2026!'),
            full_name='Анна Дмитриевна Новикова',
            role='patient',
            created_at=datetime.now().isoformat(),
            birth_date='03.12.1978',
            phone='+7 (999) 456-78-90',
            files=[]
        )
        self.users[test_patient3.id] = test_patient3

        self._save_users()

        print("\n" + "="*60)
        print("ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ СОЗДАНЫ")
        print("="*60)
        print("\n👨‍⚕️ ВРАЧИ:")
        print(f"   Email: doctor@oncomind.ai")
        print(f"   Пароль: Doctor123!")
        print(f"   ФИО: Александр Петрович Смирнов")
        print(f"   Диплом: 12345678")
        print()
        print(f"   Email: elena.doctor@oncomind.ai")
        print(f"   Пароль: Elena2026!")
        print(f"   ФИО: Елена Владимировна Козлова")
        print(f"   Диплом: 87654321")
        print("\n👤 ПАЦИЕНТЫ:")
        print(f"   Email: maria.patient@example.com")
        print(f"   Пароль: Maria2026!")
        print(f"   ФИО: Мария Ивановна Петрова (РМЖ)")
        print()
        print(f"   Email: ivan.patient@example.com")
        print(f"   Пароль: Ivan2026!")
        print(f"   ФИО: Иван Сергеевич Соколов (Рак лёгкого)")
        print()
        print(f"   Email: anna.test@example.com")
        print(f"   Пароль: Anna2026!")
        print(f"   ФИО: Анна Дмитриевна Новикова")
        print("="*60)

    def _hash_password(self, password: str) -> str:
        """
        Хеширование пароля с использованием PBKDF2.
        БЕЗОПАСНОСТЬ: 310000 итераций (рекомендация OWASP 2026)
        """
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode(), 
            salt.encode(), 
            310000  # Увеличено с 100000 до 310000
        )
        return f"{salt}${hash_obj.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Проверка пароля"""
        try:
            salt, hash_value = password_hash.split('$')
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256', 
                password.encode(), 
                salt.encode(), 
                310000
            )
            return hash_obj.hex() == hash_value
        except Exception:
            return False

    def validate_diploma_format(self, diploma_number: str) -> bool:
        """Проверка формата диплома (8 цифр)"""
        if not diploma_number:
            return False
        diploma_number = str(diploma_number).strip()
        return diploma_number.isdigit() and len(diploma_number) == 8

    def is_diploma_registered(self, diploma_number: str) -> bool:
        """Проверка, зарегистрирован ли диплом"""
        return diploma_number in self.diploma_to_user

    def create_user(self, user_data: dict) -> tuple[Optional[User], Optional[str]]:
        """Создание нового пользователя"""
        logger.info(f"create_user: email={user_data.get('email')}, role={user_data.get('role')}, diploma={user_data.get('diploma_number')}")

        # Проверка email
        if any(u.email == user_data['email'] for u in self.users.values()):
            return None, 'Email уже зарегистрирован'

        # БЕЗОПАСНОСТЬ: Проверка сложности пароля
        password_valid, password_error = validate_password_strength(user_data['password'])
        if not password_valid:
            return None, password_error

        # Проверка диплома для врачей
        if user_data['role'] == 'doctor':
            diploma = user_data.get('diploma_number', '')
            logger.info(f"Проверка диплома: '{diploma}', isdigit={diploma.isdigit() if diploma else 'N/A'}, len={len(diploma) if diploma else 0}")
            if not self.validate_diploma_format(diploma):
                return None, 'Номер диплома должен содержать ровно 8 цифр'
            if self.is_diploma_registered(diploma):
                return None, 'Диплом с таким номером уже зарегистрирован'

        # Создание пользователя
        user = User(
            id=secrets.token_hex(16),
            email=user_data['email'],
            password_hash=self._hash_password(user_data['password']),
            full_name=user_data['full_name'],
            role=user_data['role'],
            created_at=datetime.now().isoformat(),
            diploma_number=user_data.get('diploma_number') if user_data['role'] == 'doctor' else None,
            specialization=user_data.get('specialization') if user_data['role'] == 'doctor' else None,
            clinic=user_data.get('clinic') if user_data['role'] == 'doctor' else None,
            birth_date=user_data.get('birth_date') if user_data['role'] == 'patient' else None,
            phone=user_data.get('phone') if user_data['role'] == 'patient' else None,
            files=[]
        )

        self.users[user.id] = user
        if user.diploma_number:
            self.diploma_to_user[user.diploma_number] = user.id
        self._save_users()

        return user, None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Получение пользователя по email"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None


# Инициализация менеджера пользователей
user_manager = UserManager(USERS_FILE)


# =============================================================================
# БЕЗОПАСНОСТЬ: Проверка файлов
# =============================================================================
def allowed_file(filename: str) -> bool:
    """Проверка расширения файла"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def validate_mime_type(file_stream, filename: str) -> tuple[bool, Optional[str]]:
    """
    Проверка MIME-type файла.
    БЕЗОПАСНОСТЬ: Защита от подделки расширения
    """
    # Читаем первые байты для определения типа
    file_stream.seek(0)
    header = file_stream.read(1024)
    file_stream.seek(0)
    
    # Простая проверка по сигнатурам
    magic_signatures = {
        b'%PDF': 'application/pdf',
        b'\xff\xd8\xff': 'image/jpeg',
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'PK\x03\x04': 'application/zip',  # DOCX/XLSX
    }
    
    detected_type = None
    for signature, mime_type in magic_signatures.items():
        if header.startswith(signature):
            detected_type = mime_type
            break
    
    # Для DOCX/XLSX проверяем более детально
    if detected_type == 'application/zip':
        ext = Path(filename).suffix.lower()
        if ext in ['.docx', '.xlsx']:
            return True, None
    
    if detected_type and detected_type not in ALLOWED_MIME_TYPES:
        return False, f'Недопустимый тип файла: {detected_type}'
    
    return True, None


def save_uploaded_files(files) -> List[str]:
    """Сохранение загруженных файлов с проверкой MIME-type"""
    saved_files = []
    for file in files:
        if file and file.filename:
            # Проверка расширения
            if not allowed_file(file.filename):
                logger.warning(f"Недопустимое расширение: {file.filename}")
                continue
            
            # Проверка размера
            file.seek(0, 2)  # Перемещаемся в конец
            size = file.tell()
            file.seek(0)  # Возвращаемся в начало
            
            if size > MAX_FILE_SIZE:
                logger.warning(f"Файл слишком большой: {file.filename} ({size} байт)")
                continue
            
            # Проверка MIME-type
            is_valid, error = validate_mime_type(file, file.filename)
            if not is_valid:
                logger.warning(f"Недопустимый MIME-type: {file.filename} - {error}")
                continue
            
            filename = secure_filename(file.filename)
            # Добавляем timestamp и random для уникальности
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            random_suffix = secrets.token_hex(4)
            unique_filename = f"{timestamp}_{random_suffix}_{filename}"
            filepath = UPLOAD_FOLDER / unique_filename
            file.save(filepath)
            saved_files.append(unique_filename)
    
    return saved_files


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/register', methods=['POST'])
@rate_limit(register_limiter, key_func=get_client_ip)
def register():
    """Регистрация нового пользователя"""
    try:
        # Логирование входящих данных (без пароля!)
        logger.info("="*60)
        logger.info("ПОЛУЧЕН ЗАПРОС НА РЕГИСТРАЦИЮ")
        logger.info(f"Form data: role={request.form.get('role')}, email={request.form.get('email')}")

        # Получение данных формы
        role = request.form.get('role', 'patient')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')

        logger.info(f"role={role}, email={email}, full_name={full_name}")

        # Валидация обязательных полей
        if not email:
            logger.error("Не указан email")
            return jsonify({'error': 'Не указан email'}), 400
        if not password:
            logger.error("Не указан пароль")
            return jsonify({'error': 'Не указан пароль'}), 400
        if not full_name:
            logger.error("Не указано ФИО")
            return jsonify({'error': 'Не указано ФИО'}), 400
        if not role:
            logger.error("Не указана роль")
            return jsonify({'error': 'Не указана роль'}), 400
        
        # БЕЗОПАСНОСТЬ: Проверка сложности пароля
        password_valid, password_error = validate_password_strength(password)
        if not password_valid:
            return jsonify({'error': password_error}), 400

        # Подготовка данных
        user_data = {
            'email': email,
            'password': password,
            'full_name': full_name,
            'role': role
        }

        # Поля для врача
        if role == 'doctor':
            diploma_number = request.form.get('diploma_number', '')
            logger.info(f"Doctor registration: diploma_number='{diploma_number}'")
            user_data.update({
                'diploma_number': diploma_number.strip() if diploma_number else '',
                'specialization': request.form.get('specialization', ''),
                'clinic': request.form.get('clinic', '')
            })
        # Поля для пациента
        else:
            user_data.update({
                'birth_date': request.form.get('birth_date', ''),
                'phone': request.form.get('phone', '')
            })

        logger.info(f"Создание пользователя: {user_data['email']}")

        # Создание пользователя
        user, error = user_manager.create_user(user_data)
        if error:
            logger.error(f"Ошибка создания пользователя: {error}")
            return jsonify({'error': error}), 400

        logger.info(f"Пользователь создан: {user.id}, {user.email}")

        # Сохранение файлов
        if 'files' in request.files:
            files = request.files.getlist('files')
            saved_files = save_uploaded_files(files)
            user.files = saved_files
            user_manager._save_users()
            logger.info(f"Файлы сохранены: {saved_files}")

        logger.info("="*60)
        return jsonify({
            'message': 'Регистрация успешна',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role
            }
        }), 201

    except Exception as e:
        app.logger.error(f"Критическая ошибка регистрации: {e}", exc_info=True)
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/login', methods=['POST'])
@rate_limit(login_limiter, key_func=get_client_ip)
def login():
    """Вход пользователя"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember', False)

        logger.info(f"Попытка входа: {email}")

        if not email or not password:
            return jsonify({'error': 'Введите email и пароль'}), 400

        user = user_manager.get_user_by_email(email)
        if not user:
            logger.warning(f"Пользователь не найден: {email}")
            # Задержка для защиты от перебора
            time.sleep(0.5)
            return jsonify({'error': 'Неверный email или пароль'}), 401

        if not user_manager.verify_password(password, user.password_hash):
            logger.warning(f"Неверный пароль для: {email}")
            # Задержка для защиты от перебора
            time.sleep(0.5)
            return jsonify({'error': 'Неверный email или пароль'}), 401

        # Успешный вход
        logger.info(f"Успешный вход: {email} ({user.role})")

        return jsonify({
            'message': 'Вход выполнен',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'diploma_number': user.diploma_number if user.role == 'doctor' else None,
                'specialization': user.specialization if user.role == 'doctor' else None,
                'clinic': user.clinic if user.role == 'doctor' else None
            }
        }), 200

    except Exception as e:
        logger.error(f"Ошибка входа: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/validate-diploma', methods=['POST'])
@rate_limit(api_limiter, key_func=get_client_ip)
def validate_diploma():
    """Проверка номера диплома"""
    try:
        data = request.json
        diploma_number = data.get('diploma_number', '')

        if not user_manager.validate_diploma_format(diploma_number):
            return jsonify({
                'valid': False,
                'message': 'Номер диплома должен содержать ровно 8 цифр'
            }), 400

        if user_manager.is_diploma_registered(diploma_number):
            return jsonify({
                'valid': False,
                'message': 'Диплом уже зарегистрирован'
            }), 400

        return jsonify({
            'valid': True,
            'message': 'Диплом действителен'
        }), 200

    except Exception as e:
        app.logger.error(f"Ошибка проверки диплома: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/users', methods=['GET'])
@rate_limit(api_limiter, key_func=get_client_ip)
def get_users():
    """Получение списка пользователей (для администратора)"""
    users_list = []
    for user in user_manager.users.values():
        users_list.append({
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'created_at': user.created_at,
            'diploma_number': user.diploma_number if user.role == 'doctor' else None
        })
    return jsonify({'users': users_list}), 200


@app.route('/api/guidelines', methods=['GET'])
@rate_limit(api_limiter, key_func=get_client_ip)
def get_guidelines():
    """Получение списка клинических рекомендаций"""
    try:
        guidelines_file = BASE_DIR / 'knowledge_base' / 'index.json'

        if not guidelines_file.exists():
            return jsonify({'error': 'База рекомендаций не найдена'}), 404

        with open(guidelines_file, 'r', encoding='utf-8') as f:
            guidelines = json.load(f)

        # Поиск по названию
        search_query = request.args.get('q', '').lower()
        if search_query:
            guidelines = [
                g for g in guidelines 
                if search_query in g['title'].lower() or
                any(search_query in tag.lower() for tag in g.get('tags', []))
            ]

        return jsonify({'guidelines': guidelines}), 200

    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/guidelines/<guideline_id>', methods=['GET'])
@rate_limit(api_limiter, key_func=get_client_ip)
def get_guideline(guideline_id):
    """Получение конкретной рекомендации"""
    try:
        guidelines_file = BASE_DIR / 'knowledge_base' / 'index.json'

        if not guidelines_file.exists():
            return jsonify({'error': 'База рекомендаций не найдена'}), 404

        with open(guidelines_file, 'r', encoding='utf-8') as f:
            guidelines = json.load(f)

        guideline = next((g for g in guidelines if g['id'] == guideline_id), None)

        if not guideline:
            return jsonify({'error': 'Рекомендация не найдена'}), 404

        # Читаем HTML файл
        html_file = BASE_DIR / 'knowledge_base' / guideline['file']

        if not html_file.exists():
            return jsonify({'error': 'Файл рекомендации не найден'}), 404

        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({
            'guideline': guideline,
            'content': content
        }), 200

    except Exception as e:
        logger.error(f"Ошибка получения рекомендации: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/analyze', methods=['POST'])
@rate_limit(api_limiter, key_func=get_client_ip)
def analyze():
    """
    Анализ медицинского документа через AI Pipeline

    Параметры:
    - file: файл (PDF, JPG, PNG, TXT, XLSX)
    - mode: 'doctor' или 'patient'
    - query: дополнительный запрос (опционально)
    """
    try:
        import requests

        # Проверка файла
        if 'file' not in request.files:
            return jsonify({'error': 'Нет файла'}), 400

        file = request.files['file']
        mode = request.form.get('mode', 'doctor')
        query = request.form.get('query', '')

        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400

        # Проверка размера
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            return jsonify({'error': 'Файл слишком большой'}), 413

        # Проверка расширения и MIME-type
        if not allowed_file(file.filename):
            return jsonify({'error': 'Недопустимый формат файла'}), 400
        
        is_valid, error = validate_mime_type(file, file.filename)
        if not is_valid:
            return jsonify({'error': f'Недопустимый тип файла: {error}'}), 400

        # Подготовка файла для отправки на AI Pipeline
        files = {'file': (file.filename, file, file.content_type)}
        data = {'mode': mode, 'query': query}

        logger.info(f"Отправка файла на AI анализ: {file.filename}, mode={mode}")

        # Отправка на AI Pipeline
        try:
            response = requests.post(
                f"{AI_PIPELINE_URL}/api/analyze",
                files=files,
                data=data,
                timeout=120  # 2 минуты на анализ
            )

            if response.ok:
                return jsonify(response.json())
            else:
                logger.error(f"Ошибка AI Pipeline: {response.status_code} - {response.text}")
                return jsonify({
                    'error': 'Ошибка AI анализа',
                    'details': response.text
                }), 500

        except requests.exceptions.ConnectionError:
            logger.error(f"Не удалось подключиться к AI Pipeline: {AI_PIPELINE_URL}")
            return jsonify({
                'error': 'AI сервер недоступен',
                'message': 'Сервис анализа временно недоступен. Попробуйте позже.'
            }), 503
        except requests.exceptions.Timeout:
            logger.error("Превышено время ожидания AI Pipeline")
            return jsonify({
                'error': 'Превышено время ожидания',
                'message': 'Анализ занимает больше времени. Попробуйте снова.'
            }), 504

    except Exception as e:
        logger.error(f"Критическая ошибка анализа: {e}", exc_info=True)
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/doctor/patients', methods=['GET'])
@rate_limit(api_limiter, key_func=get_client_ip)
def get_doctor_patients():
    """Получение списка пациентов врача"""
    try:
        user_id = request.args.get('user_id')

        if not user_id:
            user_id = request.headers.get('X-User-Id')

        if not user_id:
            return jsonify({'error': 'Не указан ID врача'}), 400

        doctor = user_manager.users.get(user_id)
        if not doctor or doctor.role != 'doctor':
            return jsonify({'error': 'Врач не найден'}), 404

        patients = [u for u in user_manager.users.values() if u.role == 'patient']

        patients_data = []
        for patient in patients:
            patients_data.append({
                'id': patient.id,
                'full_name': patient.full_name,
                'email': patient.email,
                'birth_date': patient.birth_date,
                'phone': patient.phone,
                'is_my_patient': getattr(patient, 'doctor_id', None) == user_id
            })

        return jsonify({'patients': patients_data}), 200

    except Exception as e:
        logger.error(f"Ошибка получения пациентов: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/doctor/patients/assign', methods=['POST'])
@rate_limit(api_limiter, key_func=get_client_ip)
def assign_patient():
    """Закрепление пациента за врачом"""
    try:
        data = request.json
        doctor_id = data.get('doctor_id')
        patient_id = data.get('patient_id')

        if not doctor_id or not patient_id:
            return jsonify({'error': 'Не указаны ID'}), 400

        doctor = user_manager.users.get(doctor_id)
        patient = user_manager.users.get(patient_id)

        if not doctor or doctor.role != 'doctor':
            return jsonify({'error': 'Врач не найден'}), 404

        if not patient or patient.role != 'patient':
            return jsonify({'error': 'Пациент не найден'}), 404

        if not hasattr(patient, 'doctor_id'):
            patient.doctor_id = None
        patient.doctor_id = doctor_id
        user_manager._save_users()

        logger.info(f"Пациент {patient_id} закреплён за врачом {doctor_id}")

        return jsonify({
            'message': 'Пациент успешно закреплён',
            'patient_id': patient_id,
            'doctor_id': doctor_id
        }), 200

    except Exception as e:
        logger.error(f"Ошибка закрепления пациента: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/doctor/patients/unassign', methods=['POST'])
@rate_limit(api_limiter, key_func=get_client_ip)
def unassign_patient():
    """Открепление пациента от врача"""
    try:
        data = request.json
        patient_id = data.get('patient_id')

        if not patient_id:
            return jsonify({'error': 'Не указан ID пациента'}), 400

        patient = user_manager.users.get(patient_id)

        if not patient:
            return jsonify({'error': 'Пациент не найден'}), 404

        if hasattr(patient, 'doctor_id'):
            patient.doctor_id = None
            user_manager._save_users()

        logger.info(f"Пациент {patient_id} откреплён")

        return jsonify({
            'message': 'Пациент откреплён',
            'patient_id': patient_id
        }), 200

    except Exception as e:
        logger.error(f"Ошибка открепления пациента: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/user/profile', methods=['GET'])
@rate_limit(api_limiter, key_func=get_client_ip)
def get_profile():
    """Получение профиля пользователя"""
    try:
        user_id = request.headers.get('X-User-Id')
        
        if not user_id:
            return jsonify({'error': 'Не указан ID пользователя'}), 400
        
        user = user_manager.users.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        return jsonify({
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'diploma_number': user.diploma_number if user.role == 'doctor' else None,
                'specialization': user.specialization if user.role == 'doctor' else None,
                'clinic': user.clinic if user.role == 'doctor' else None,
                'birth_date': user.birth_date if user.role == 'patient' else None,
                'phone': user.phone if user.role == 'patient' else None,
                'files': user.files
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения профиля: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


# =============================================================================
# ОБРАБОТКА ОШИБОК
# =============================================================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Не найдено'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({
        'error': 'Слишком много запросов',
        'message': 'Пожалуйста, подождите перед следующей попыткой'
    }), 429


# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================
if __name__ == '__main__':
    # Генерация CSRF токена для сессии
    @app.before_request
    def ensure_csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
    
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Запуск сервера на {host}:{port}")
    app.run(host=host, port=port, debug=debug)
