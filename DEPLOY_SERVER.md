# 🚀 OncoMind - Полная инструкция по деплою на сервер

## 📋 Содержание

1. [Требования к серверу](#требования-к-серверу)
2. [Подготовка сервера](#подготовка-сервера)
3. [Установка приложения](#установка-приложения)
4. [Настройка переменных окружения](#настройка-переменных-окружения)
5. [Настройка systemd сервисов](#настройка-systemd-сервисов)
6. [Настройка Nginx](#настройка-nginx)
7. [Настройка SSL (Let's Encrypt)](#настройка-ssl)
8. [Проверка работы](#проверка-работы)
9. [Мониторинг и логи](#мониторинг-и-логи)
10. [Исправления безопасности в этой версии](#исправления-безопасности)

---

## 🔧 Требования к серверу

### Минимальные требования

| Параметр | Значение |
|----------|----------|
| CPU | 2 ядра |
| RAM | 4 GB |
| Disk | 20 GB SSD |
| OS | Ubuntu 22.04 LTS / Debian 11+ |

### Рекомендуемые требования

| Параметр | Значение |
|----------|----------|
| CPU | 4 ядра |
| RAM | 8 GB |
| Disk | 40 GB SSD |
| OS | Ubuntu 22.04 LTS |

---

## 📦 Подготовка сервера

### 1. Подключение к серверу

```bash
ssh user@your-server-ip
```

### 2. Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Установка необходимых пакетов

```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    nginx \
    git \
    curl \
    wget \
    build-essential \
    libmagic1 \
    certbot \
    python3-certbot-nginx \
    fail2ban \
    ufw
```

### 4. Настройка брандмауэра (UFW)

```bash
# Разрешаем SSH
sudo ufw allow OpenSSH

# Разрешаем HTTP/HTTPS
sudo ufw allow 'Nginx Full'

# Включаем брандмауэр
sudo ufw enable

# Проверка статуса
sudo ufw status
```

### 5. Настройка Fail2Ban для защиты от брутфорса

```bash
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

Создайте файл `/etc/fail2ban/jail.d/nginx.conf`:

```ini
[nginx-http-auth]
enabled = true
port    = http,https
filter  = nginx-http-auth
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port    = http,https
filter  = nginx-limit-req
logpath = /var/log/nginx/error.log
```

```bash
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
```

---

## 📥 Установка приложения

### 1. Создание директории приложения

```bash
sudo mkdir -p /var/www/oncomind
sudo chown -R $USER:$USER /var/www/oncomind
cd /var/www/oncomind
```

### 2. Клонирование репозитория

```bash
git clone <your-repository-url> .
```

Или скопируйте файлы через SCP:

```bash
# С локальной машины
scp -r d:/M2/OncoMindFull/* user@your-server-ip:/var/www/oncomind/
```

### 3. Установка Python зависимостей

#### Backend (Flask):

```bash
cd /var/www/oncomind/backend

# Создание виртуального окружения
python3 -m venv venv

# Активация
source venv/bin/activate

# Обновление pip
pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt

# Выход из venv
deactivate
```

#### AI Pipeline (FastAPI):

```bash
cd /var/www/oncomind/oncology_ai_assistant

# Создание виртуального окружения
python3 -m venv venv

# Активация
source venv/bin/activate

# Обновление pip
pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt

# Выход из venv
deactivate
```

---

## 🔐 Настройка переменных окружения

### 1. Создание .env файла для Backend

```bash
cd /var/www/oncomind/backend
cp ../env.example .env
nano .env
```

**Содержимое .env:**

```bash
# =============================================================================
# OncoMind Backend - Переменные окружения
# =============================================================================

# Секретный ключ для сессий (сгенерируйте новый!)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Разрешённые origin для CORS (укажите ваш домен)
ALLOWED_ORIGINS=https://oncomind.ru,https://www.oncomind.ru

# Путь к базовой директории
BASE_DIR=/var/www/oncomind/backend

# Путь к файлу пользователей
USERS_FILE=/var/www/oncomind/backend/data/users.json

# Максимальный размер файла (10 MB)
MAX_FILE_SIZE=10485760

# AI Pipeline URL
AI_PIPELINE_URL=http://127.0.0.1:8000

# Хост и порт для Flask
HOST=127.0.0.1
PORT=5000

# Режим отладки (False для продакшена!)
DEBUG=False

# Уровень логирования
LOG_LEVEL=INFO
```

### 2. Создание .env файла для AI Pipeline

```bash
cd /var/www/oncomind/oncology_ai_assistant
cp .env.example .env
nano .env
```

**Содержимое .env:**

```bash
# =============================================================================
# OncoMind AI Pipeline - Переменные окружения
# =============================================================================

# Yandex Cloud Configuration
YC_FOLDER_ID=b1xxxxxxxxxxxxxxxxx  # Ваш ID каталога
YC_API_KEY=xxxxxxxxxxxxxxxxxxxxxxx  # Ваш API ключ
YC_SERVICE_ACCOUNT_KEY=/var/www/oncomind/oncology_ai_assistant/oncomind_sa_key.json

# AI Server Configuration
AI_HOST=127.0.0.1
AI_PORT=8000
DEBUG=False

# Database
DATABASE_URL=sqlite:///./oncomind_ai.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/www/oncomind/oncology_ai_assistant/logs/oncomind_ai.log

# CORS
ALLOWED_ORIGINS=https://oncomind.ru,https://www.oncomind.ru
```

### 3. Создание директорий для логов

```bash
sudo mkdir -p /var/www/oncomind/backend/logs
sudo mkdir -p /var/www/oncomind/oncology_ai_assistant/logs
sudo chown -R $USER:$USER /var/www/oncomind/*/logs
```

---

## ⚙️ Настройка systemd сервисов

### 1. Сервис для Backend (Flask)

```bash
sudo nano /etc/systemd/system/oncomind-backend.service
```

**Содержимое файла:**

```ini
[Unit]
Description=OncoMind Backend (Flask)
After=network.target oncomind-ai.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/oncomind/backend
Environment="PATH=/var/www/oncomind/backend/venv/bin"
ExecStart=/var/www/oncomind/backend/venv/bin/python app.py
Restart=always
RestartSec=10

# Безопасность
NoNewPrivileges=true
PrivateTmp=true

# Логи
StandardOutput=journal
StandardError=journal
SyslogIdentifier=oncomind-backend

[Install]
WantedBy=multi-user.target
```

### 2. Сервис для AI Pipeline (FastAPI)

```bash
sudo nano /etc/systemd/system/oncomind-ai.service
```

**Содержимое файла:**

```ini
[Unit]
Description=OncoMind AI Pipeline (FastAPI)
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/oncomind/oncology_ai_assistant
Environment="PATH=/var/www/oncomind/oncology_ai_assistant/venv/bin"
ExecStart=/var/www/oncomind/oncology_ai_assistant/venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

# Безопасность
NoNewPrivileges=true
PrivateTmp=true

# Логи
StandardOutput=journal
StandardError=journal
SyslogIdentifier=oncomind-ai

[Install]
WantedBy=multi-user.target
```

### 3. Активация и запуск сервисов

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение сервисов
sudo systemctl enable oncomind-ai
sudo systemctl enable oncomind-backend

# Запуск сервисов
sudo systemctl start oncomind-ai
sudo systemctl start oncomind-backend

# Проверка статуса
sudo systemctl status oncomind-ai
sudo systemctl status oncomind-backend
```

---

## 🌐 Настройка Nginx

### 1. Создание конфигурации Nginx

```bash
sudo nano /etc/nginx/sites-available/oncomind
```

**Содержимое файла:**

```nginx
server {
    listen 80;
    server_name oncomind.ru www.oncomind.ru;

    # Корневая директория frontend
    root /var/www/oncomind/frontend;
    index index.html;

    # Логи
    access_log /var/log/nginx/oncomind.access.log;
    error_log /var/log/nginx/oncomind.error.log;

    # Статические файлы
    location /static {
        alias /var/www/oncomind/frontend;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Backend API (Flask)
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        # Размеры
        client_max_body_size 15M;
    }

    # AI Pipeline API
    location /ai-api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты для AI (дольше)
        proxy_connect_timeout 180s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Размеры
        client_max_body_size 55M;
        
        # Rewrite path
        rewrite ^/ai-api/(.*) /$1 break;
    }

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Защита от некоторых атак
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### 2. Активация конфигурации

```bash
# Создание симлинка
sudo ln -s /etc/nginx/sites-available/oncomind /etc/nginx/sites-enabled/

# Удаление дефолтной конфигурации
sudo rm /etc/nginx/sites-enabled/default

# Проверка конфигурации
sudo nginx -t

# Перезапуск Nginx
sudo systemctl restart nginx
```

---

## 🔒 Настройка SSL (Let's Encrypt)

### 1. Получение сертификата

```bash
sudo certbot --nginx -d oncomind.ru -d www.oncomind.ru
```

### 2. Автоматическое обновление

Certbot автоматически создаёт cron задачу для обновления. Проверьте:

```bash
sudo systemctl status certbot.timer
```

### 3. Проверка автообновления

```bash
sudo certbot renew --dry-run
```

---

## ✅ Проверка работы

### 1. Проверка сервисов

```bash
# Backend
curl http://127.0.0.1:5000/api/users

# AI Pipeline
curl http://127.0.0.1:8000/health

# Через Nginx
curl https://oncomind.ru/api/users
```

### 2. Проверка логов

```bash
# Backend логи
sudo journalctl -u oncomind-backend -f

# AI Pipeline логи
sudo journalctl -u oncomind-ai -f

# Nginx логи
sudo tail -f /var/log/nginx/oncomind.access.log
sudo tail -f /var/log/nginx/oncomind.error.log
```

### 3. Проверка безопасности

```bash
# Проверка открытых портов
sudo netstat -tulpn

# Должны быть открыты только:
# 22 (SSH)
# 80 (HTTP)
# 443 (HTTPS)
```

---

## 📊 Мониторинг и логи

### 1. Просмотр логов в реальном времени

```bash
# Все логи OncoMind
sudo journalctl -f -t oncomind-backend -t oncomind-ai

# Только ошибки
sudo journalctl -p err -f
```

### 2. Мониторинг ресурсов

```bash
# Установка htop
sudo apt install -y htop

# Запуск
htop
```

### 3. Настройка ротации логов

```bash
sudo nano /etc/logrotate.d/oncomind
```

**Содержимое:**

```
/var/log/nginx/oncomind.*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    prerotate
        if [ -d /etc/logrotate.d/httpd-prerotate ]; then
            run-parts /etc/logrotate.d/httpd-prerotate
        fi
    endscript
    postrotate
        invoke-rc.d nginx rotate >/dev/null 2>&1
    endscript
}
```

---

## 🛡️ Исправления безопасности в этой версии

### Backend (app.py)

| Исправление | Описание |
|-------------|----------|
| ✅ Rate Limiting | Защита от DoS и брутфорса (5 запросов/мин для login) |
| ✅ CSRF защита | Токены для форм |
| ✅ Валидация паролей | Минимум 8 символов, заглавные, строчные, цифры |
| ✅ Усиленное хеширование | PBKDF2 с 310000 итераций (OWASP 2026) |
| ✅ Проверка MIME-type | Защита от подделки расширения файлов |
| ✅ Secret key из env | Не генерируется при каждом запуске |
| ✅ CORS с белым списком | Только разрешённые домены |
| ✅ Санитизация логов | Токены и пароли не попадают в логи |

### Frontend

| Исправление | Описание |
|-------------|----------|
| ✅ XSS защита | Функция escapeHtml() для всех пользовательских данных |
| ✅ Безопасная вставка | textContent вместо innerHTML |
| ✅ Валидация на клиенте | Проверка email и пароля перед отправкой |
| ✅ Безопасные атрибуты | Блокировка опасных атрибутов |

### AI Pipeline (main.py, logger.py)

| Исправление | Описание |
|-------------|----------|
| ✅ Проверка размера до загрузки | Экономия памяти |
| ✅ CORS с белым списком | Только разрешённые домены |
| ✅ Санитизация токенов | API ключи и IAM токены скрыты |
| ✅ Безопасное логирование | Санитизация ошибок и аргументов |

---

## 🔄 Деплой обновлений

### 1. Обновление кода

```bash
cd /var/www/oncomind

# Если через git
sudo git pull origin main

# Или скопируйте новые файлы
# scp -r new_files/* user@server:/var/www/oncomind/
```

### 2. Обновление зависимостей

```bash
# Backend
cd /var/www/oncomind/backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate

# AI Pipeline
cd /var/www/oncomind/oncology_ai_assistant
source venv/bin/activate
pip install -r requirements.txt --upgrade
deactivate
```

### 3. Перезапуск сервисов

```bash
sudo systemctl daemon-reload
sudo systemctl restart oncomind-backend
sudo systemctl restart oncomind-ai
sudo systemctl restart nginx
```

### 4. Проверка

```bash
sudo systemctl status oncomind-backend oncomind-ai nginx
```

---

## 🆘 Решение проблем

### Backend не запускается

```bash
# Проверка логов
sudo journalctl -u oncomind-backend -n 50

# Проверка порта
sudo netstat -tulpn | grep 5000

# Проверка прав
ls -la /var/www/oncomind/backend/
```

### AI Pipeline не запускается

```bash
# Проверка логов
sudo journalctl -u oncomind-ai -n 50

# Проверка порта
sudo netstat -tulpn | grep 8000

# Проверка Yandex Cloud
curl -H "Authorization: Api-Key YOUR_API_KEY" \
     https://ai.api.cloud.yandex.net/v1/folders/YOUR_FOLDER_ID
```

### Nginx не проксирует запросы

```bash
# Проверка конфигурации
sudo nginx -t

# Проверка логов
sudo tail -f /var/log/nginx/oncomind.error.log

# Проверка брандмауэра
sudo ufw status
```

---

## 📞 Контакты поддержки

- Email: team@oncomind.ai
- Telegram: @oncomind

---

## 📝 Чек-лист после деплоя

- [ ] Backend доступен через API
- [ ] AI Pipeline отвечает на /health
- [ ] Frontend загружается
- [ ] Регистрация работает
- [ ] Вход работает
- [ ] HTTPS настроен
- [ ] Логи пишутся
- [ ] Rate limiting работает
- [ ] CORS настроен правильно
- [ ] Резервное копирование настроено

---

**Версия инструкции:** 2.0 (с исправлениями безопасности)  
**Дата обновления:** Февраль 2026
