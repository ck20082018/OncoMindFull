#!/usr/bin/env python3
"""
Скрипт для создания/сброса тестовых пользователей OncoMind
Запускать только на сервере для инициализации тестовых аккаунтов
"""

import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path

# Путь к файлу пользователей
USERS_FILE = Path(__file__).parent / 'data' / 'users.json'
USERS_FILE.parent.mkdir(exist_ok=True)


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"


def create_test_users():
    """Создание тестовых пользователей"""
    
    test_users = [
        {
            "id": secrets.token_hex(16),
            "email": "doctor@oncomind.ai",
            "password_hash": hash_password("Doctor123!"),
            "full_name": "Александр Петрович Смирнов",
            "role": "doctor",
            "created_at": datetime.now().isoformat(),
            "diploma_number": "12345678",
            "specialization": "Онколог, химиотерапевт",
            "clinic": "Городской онкологический диспансер №1",
            "birth_date": None,
            "phone": None,
            "files": []
        },
        {
            "id": secrets.token_hex(16),
            "email": "elena.doctor@oncomind.ai",
            "password_hash": hash_password("Elena2026!"),
            "full_name": "Елена Владимировна Козлова",
            "role": "doctor",
            "created_at": datetime.now().isoformat(),
            "diploma_number": "87654321",
            "specialization": "Онколог, радиотерапевт",
            "clinic": "Областная клиническая больница",
            "birth_date": None,
            "phone": None,
            "files": []
        },
        {
            "id": secrets.token_hex(16),
            "email": "maria.patient@example.com",
            "password_hash": hash_password("Maria2026!"),
            "full_name": "Мария Ивановна Петрова",
            "role": "patient",
            "created_at": datetime.now().isoformat(),
            "diploma_number": None,
            "specialization": None,
            "clinic": None,
            "birth_date": "15.03.1965",
            "phone": "+7 (999) 123-45-67",
            "files": []
        },
        {
            "id": secrets.token_hex(16),
            "email": "ivan.patient@example.com",
            "password_hash": hash_password("Ivan2026!"),
            "full_name": "Иван Сергеевич Соколов",
            "role": "patient",
            "created_at": datetime.now().isoformat(),
            "diploma_number": None,
            "specialization": None,
            "clinic": None,
            "birth_date": "22.08.1958",
            "phone": "+7 (999) 765-43-21",
            "files": []
        },
        {
            "id": secrets.token_hex(16),
            "email": "anna.test@example.com",
            "password_hash": hash_password("Anna2026!"),
            "full_name": "Анна Дмитриевна Новикова",
            "role": "patient",
            "created_at": datetime.now().isoformat(),
            "diploma_number": None,
            "specialization": None,
            "clinic": None,
            "birth_date": "03.12.1978",
            "phone": "+7 (999) 456-78-90",
            "files": []
        }
    ]
    
    # Сохранение в файл
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(test_users, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)
    print("ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ СОЗДАНЫ")
    print("=" * 60)
    print("\n👨‍⚕️ ВРАЧИ:")
    print("   Email: doctor@oncomind.ai")
    print("   Пароль: Doctor123!")
    print("   Email: elena.doctor@oncomind.ai")
    print("   Пароль: Elena2026!")
    print("\n👤 ПАЦИЕНТЫ:")
    print("   Email: maria.patient@example.com")
    print("   Пароль: Maria2026!")
    print("   Email: ivan.patient@example.com")
    print("   Пароль: Ivan2026!")
    print("   Email: anna.test@example.com")
    print("   Пароль: Anna2026!")
    print("=" * 60)
    print(f"\nФайл сохранён: {USERS_FILE}")
    
    return test_users


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        confirm = input("Вы уверены? Это удалит всех текущих пользователей! (yes/no): ")
        if confirm.lower() != 'yes':
            print("Отменено")
            exit(0)
    
    create_test_users()
