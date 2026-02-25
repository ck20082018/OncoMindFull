# OncoMind - AI-помощник онколога

## 🚀 Быстрый старт

### Локальная разработка

#### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python app.py
```

#### Frontend
Откройте `frontend/index.html` в браузере или используйте Live Server в VS Code.

---

## 🌐 Деплой на сервер

### Вариант 1: Railway.app (рекомендуется)

1. Создайте аккаунт на [railway.app](https://railway.app)
2. Нажмите "New Project" → "Deploy from GitHub repo"
3. Выберите репозиторий `OncoMindFull`
4. Добавьте переменные окружения в Railway:
   - `PYTHON_VERSION` = `3.11`
5. Укажите Build Command: `cd backend && pip install -r requirements.txt`
6. Укажите Start Command: `cd backend && python app.py`

### Вариант 2: Render.com

1. Создайте аккаунт на [render.com](https://render.com)
2. "New +" → "Web Service"
3. Подключите GitHub репозиторий
4. Настройки:
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python app.py`
   - **Environment**: Python 3

### Вариант 3: VPS (Ubuntu/Debian)

```bash
# Установка зависимостей
sudo apt update
sudo apt install -y python3-pip python3-venv nginx git

# Клонирование репозитория
cd /var/www
git clone <ваш-репозиторий> oncomind
cd oncomind

# Настройка backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Запуск через systemd
sudo nano /etc/systemd/system/oncomind.service
```

**oncomind.service:**
```ini
[Unit]
Description=OncoMind Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/oncomind/backend
ExecStart=/var/www/oncomind/backend/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Активация сервиса
sudo systemctl enable oncomind
sudo systemctl start oncomind

# Настройка Nginx
sudo nano /etc/nginx/sites-available/oncomind
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name oncomind.ru www.oncomind.ru;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /var/www/oncomind/backend/static;
    }
}
```

```bash
# Активация сайта
sudo ln -s /etc/nginx/sites-available/oncomind /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔐 Переменные окружения

Создайте `.env` файл в папке `backend/`:

```env
FLASK_ENV=production
SECRET_KEY=ваш_секретный_ключ
CORS_ORIGINS=https://oncomind.ru
```

---

## 📊 Тестовые учетные данные

**Врач:**
- Email: `doctor@oncomind.ai`
- Пароль: `Doctor123!`

**Пациент:**
- Email: `maria.patient@example.com`
- Пароль: `Maria2026!`

---

## 📝 Структура проекта

```
OncoMindFull/
├── backend/           # Flask API
│   ├── app.py        # Основной сервер
│   ├── data/         # База пользователей
│   └── uploads/      # Загруженные файлы
├── frontend/         # HTML/CSS/JS интерфейс
│   ├── doctor/       # Кабинет врача
│   └── patient/      # Кабинет пациента
└── test_cases/       # Тестовые сценарии
```

---

## 🛠️ API Endpoints

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/api/register` | POST | Регистрация пользователя |
| `/api/login` | POST | Вход в систему |
| `/api/validate-diploma` | POST | Проверка диплома врача |
| `/api/users` | GET | Список пользователей (admin) |

---

## 📞 Контакты

Email: team@oncomind.ai
