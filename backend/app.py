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

# Конфигурация AI Pipeline
AI_PIPELINE_URL = os.environ.get('AI_PIPELINE_URL', 'http://127.0.0.1:8000')

# Конфигурация
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.xlsx', '.docx', '.txt', '.jpg', '.jpeg', '.png'}
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
        logger.info("="*60)
        logger.info("ПОЛУЧЕН ЗАПРОС НА РЕГИСТРАЦИЮ")
        logger.info(f"Form data: {dict(request.form)}")
        logger.info(f"Files: {list(request.files.keys()) if request.files else 'Нет'}")

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
            logger.info(f"Doctor registration: diploma_number='{diploma_number}', len={len(diploma_number) if diploma_number else 0}")
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

        logger.info(f"Создание пользователя: {user_data}")

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
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


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


@app.route('/api/guidelines', methods=['GET'])
def get_guidelines():
    """Получение списка клинических рекомендаций"""
    try:
        import json
        guidelines_file = Path(__file__).parent / 'knowledge_base' / 'index.json'
        
        if not guidelines_file.exists():
            return jsonify({'error': 'База рекомендаций не найдена'}), 404
        
        with open(guidelines_file, 'r', encoding='utf-8') as f:
            guidelines = json.load(f)
        
        # Поиск по названию
        search_query = request.args.get('q', '').lower()
        if search_query:
            guidelines = [g for g in guidelines if search_query in g['title'].lower() or 
                         any(search_query in tag.lower() for tag in g.get('tags', []))]
        
        return jsonify({'guidelines': guidelines}), 200
    
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/guidelines/<guideline_id>', methods=['GET'])
def get_guideline(guideline_id):
    """Получение конкретной рекомендации"""
    try:
        import json
        guidelines_file = Path(__file__).parent / 'knowledge_base' / 'index.json'
        
        if not guidelines_file.exists():
            return jsonify({'error': 'База рекомендаций не найдена'}), 404
        
        with open(guidelines_file, 'r', encoding='utf-8') as f:
            guidelines = json.load(f)
        
        guideline = next((g for g in guidelines if g['id'] == guideline_id), None)
        
        if not guideline:
            return jsonify({'error': 'Рекомендация не найдена'}), 404
        
        # Читаем HTML файл
        html_file = Path(__file__).parent / 'knowledge_base' / guideline['file']
        
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
def get_doctor_patients():
    """Получение списка пациентов врача"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            # Получаем из сессии или заголовка
            user_id = request.headers.get('X-User-Id')
        
        if not user_id:
            return jsonify({'error': 'Не указан ID врача'}), 400
        
        # Находим врача
        doctor = user_manager.users.get(user_id)
        if not doctor or doctor.role != 'doctor':
            return jsonify({'error': 'Врач не найден'}), 404
        
        # Получаем всех пациентов
        patients = [u for u in user_manager.users.values() if u.role == 'patient']
        
        # Формируем ответ
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
def assign_patient():
    """Закрепление пациента за врачом"""
    try:
        data = request.json
        doctor_id = data.get('doctor_id')
        patient_id = data.get('patient_id')
        
        if not doctor_id or not patient_id:
            return jsonify({'error': 'Не указаны ID'}), 400
        
        # Находим врача и пациента
        doctor = user_manager.users.get(doctor_id)
        patient = user_manager.users.get(patient_id)
        
        if not doctor or doctor.role != 'doctor':
            return jsonify({'error': 'Врач не найден'}), 404
        
        if not patient or patient.role != 'patient':
            return jsonify({'error': 'Пациент не найден'}), 404
        
        # Закрепляем пациента (добавляем атрибут если нет)
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
def unassign_patient():
    """Открепление пациента от врача"""
    try:
        data = request.json
        patient_id = data.get('patient_id')
        
        if not patient_id:
            return jsonify({'error': 'Не указан ID пациента'}), 400
        
        # Находим пациента
        patient = user_manager.users.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Пациент не найден'}), 404
        
        # Открепляем
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


@app.route('/api/guidelines-pdf', methods=['GET'])
def get_guidelines_pdf():
    """Получение списка PDF клинических рекомендаций"""
    try:
        import os
        pdf_dir = Path(__file__).parent / 'knowledge_base_pdf'
        
        if not pdf_dir.exists():
            pdf_dir.mkdir(exist_ok=True)
            return jsonify({'guidelines': [], 'message': 'Папка пуста. Добавьте PDF файлы.'}), 200
        
        # Получаем список PDF файлов
        pdf_files = [f for f in pdf_dir.iterdir() if f.suffix.lower() == '.pdf']
        
        guidelines = []
        for pdf in pdf_files:
            guidelines.append({
                'id': pdf.stem,
                'title': pdf.stem.replace('-', ' ').replace('_', ' ').title(),
                'filename': pdf.name,
                'size': pdf.stat().st_size,
                'created': pdf.stat().st_mtime
            })
        
        # Сортируем по имени
        guidelines.sort(key=lambda x: x['title'])
        
        return jsonify({'guidelines': guidelines}), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения списка PDF: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/guidelines-pdf/<filename>', methods=['GET'])
def download_guideline_pdf(filename):
    """Скачивание/просмотр PDF клинической рекомендации"""
    try:
        from flask import send_file
        import os
        
        pdf_dir = Path(__file__).parent / 'knowledge_base_pdf'
        pdf_path = pdf_dir / filename
        
        # Проверка безопасности
        if not pdf_path.exists():
            return jsonify({'error': 'Файл не найден'}), 404
        
        if not pdf_path.suffix.lower() == '.pdf':
            return jsonify({'error': 'Неверный формат файла'}), 400
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=False  # Открывать в браузере, не скачивать
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки PDF: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("OncoMind Backend Server")
    print("=" * 50)
    print(f"Тестовый врач:")
    print(f"  Email: doctor@oncomind.ai")
    print(f"  Пароль: Doctor123!")
    print(f"  Диплом: 12345678")
    print("=" * 50)
    
    # Проверка режима работы
    import os
    debug_mode = os.environ.get('FLASK_ENV', 'production') != 'production'
    
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=5000
    )
