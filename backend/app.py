"""
Backend для регистрации пользователей OncoMind
Поддержка двух ролей: врач и пациент
"""

import os
import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Настройка CORS для локальной разработки и продакшена
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # Разрешить все (для разработки)
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Конфигурация
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.xlsx', '.txt', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Путь к файлу пользователей
USERS_FILE = Path(__file__).parent / 'data' / 'users.json'
USERS_FILE.parent.mkdir(exist_ok=True)


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
            with open(self.users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for user_data in data:
                    user = User(**user_data)
                    self.users[user.id] = user
                    if user.diploma_number:
                        self.diploma_to_user[user.diploma_number] = user.id
    
    def _save_users(self):
        """Сохранение пользователей в файл"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(u) for u in self.users.values()], f, ensure_ascii=False, indent=2)
    
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
        """Хеширование пароля"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hash_obj.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Проверка пароля"""
        try:
            salt, hash_value = password_hash.split('$')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hash_obj.hex() == hash_value
        except:
            return False
    
    def validate_diploma_format(self, diploma_number: str) -> bool:
        """Проверка формата диплома (8 цифр)"""
        return diploma_number.isdigit() and len(diploma_number) == 8
    
    def is_diploma_registered(self, diploma_number: str) -> bool:
        """Проверка, зарегистрирован ли диплом"""
        return diploma_number in self.diploma_to_user
    
    def create_user(self, user_data: dict) -> tuple[Optional[User], Optional[str]]:
        """Создание нового пользователя"""
        # Проверка email
        if any(u.email == user_data['email'] for u in self.users.values()):
            return None, 'Email уже зарегистрирован'
        
        # Проверка диплома для врачей
        if user_data['role'] == 'doctor':
            diploma = user_data.get('diploma_number', '')
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


def allowed_file(filename: str) -> bool:
    """Проверка расширения файла"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def save_uploaded_files(files) -> List[str]:
    """Сохранение загруженных файлов"""
    saved_files = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            if file.content_length > MAX_FILE_SIZE:
                continue
            filename = secure_filename(file.filename)
            # Добавляем timestamp для уникальности
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = UPLOAD_FOLDER / unique_filename
            file.save(filepath)
            saved_files.append(unique_filename)
    return saved_files


@app.route('/api/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    try:
        # Логирование входящих данных
        logger.info(f"Получен запрос на регистрацию")
        logger.info(f"Form data: {dict(request.form)}")
        logger.info(f"Files: {request.files}")
        
        # Получение данных формы
        role = request.form.get('role', 'patient')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        logger.info(f"role={role}, email={email}, full_name={full_name}")

        # Валидация обязательных полей
        if not all([email, password, full_name, role]):
            logger.warning(f"Не все поля заполнены: email={email}, full_name={full_name}")
            return jsonify({'error': 'Заполните все обязательные поля'}), 400
        
        # Подготовка данных
        user_data = {
            'email': email,
            'password': password,
            'full_name': full_name,
            'role': role
        }
        
        # Поля для врача
        if role == 'doctor':
            user_data.update({
                'diploma_number': request.form.get('diploma_number'),
                'specialization': request.form.get('specialization'),
                'clinic': request.form.get('clinic')
            })
        # Поля для пациента
        else:
            user_data.update({
                'birth_date': request.form.get('birth_date'),
                'phone': request.form.get('phone')
            })
        
        # Создание пользователя
        user, error = user_manager.create_user(user_data)
        if error:
            return jsonify({'error': error}), 400
        
        # Сохранение файлов
        if 'files' in request.files:
            files = request.files.getlist('files')
            saved_files = save_uploaded_files(files)
            user.files = saved_files
            user_manager._save_users()
        
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
        app.logger.error(f"Ошибка регистрации: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/login', methods=['POST'])
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
            return jsonify({'error': 'Пользователь не найден'}), 404
        
        if not user_manager.verify_password(password, user.password_hash):
            logger.warning(f"Неверный пароль для: {email}")
            return jsonify({'error': 'Неверный пароль'}), 401
        
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


if __name__ == '__main__':
    print("=" * 50)
    print("OncoMind Backend Server")
    print("=" * 50)
    print(f"Тестовый врач:")
    print(f"  Email: test.doctor@oncomind.ai")
    print(f"  Пароль: TestDoctor123!")
    print(f"  Диплом: 12345678")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
