# 🚀 OncoMind - Быстрый старт на сервере

## ⚡ Быстрая установка (5 минут)

### 1. Подготовка сервера

```bash
# Подключение к серверу
ssh user@your-server-ip

# Обновление системы
sudo apt update && sudo apt upgrade -y
```

### 2. Автоматическая установка

```bash
# Перейдите в директорию проекта
cd /var/www/oncomind

# Сделайте скрипт исполняемым
chmod +x install_server.sh

# Запустите установку (требуется root)
sudo ./install_server.sh
```

Скрипт автоматически:
- ✅ Установит все пакеты
- ✅ Настроит брандмауэр
- ✅ Создаст Python окружения
- ✅ Настроит переменные окружения
- ✅ Создаст systemd сервисы
- ✅ Настроит Nginx
- ✅ Предложит настроить SSL

### 3. Ручная настройка (если нужно)

Если хотите настроить вручную:

```bash
# 1. Установка пакетов
sudo apt install -y python3 python3-pip python3-venv nginx git libmagic1

# 2. Backend
cd /var/www/oncomind/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. AI Pipeline
cd /var/www/oncomind/oncology_ai_assistant
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Создание .env файлов
# См. раздел "Настройка переменных окружения" ниже
```

---

## 🔐 Настройка переменных окружения

### Backend (.env)

```bash
cd /var/www/oncomind/backend
nano .env
```

```env
SECRET_KEY=<сгенерируйте: python3 -c "import secrets; print(secrets.token_hex(32))">
ALLOWED_ORIGINS=https://your-domain.com
BASE_DIR=/var/www/oncomind/backend
AI_PIPELINE_URL=http://127.0.0.1:8000
PORT=5000
DEBUG=False
```

### AI Pipeline (.env)

```bash
cd /var/www/oncomind/oncology_ai_assistant
nano .env
```

```env
YC_FOLDER_ID=b1xxxxxxxxx
YC_API_KEY=xxxxxxxxxxx
AI_HOST=127.0.0.1
AI_PORT=8000
DEBUG=False
ALLOWED_ORIGINS=https://your-domain.com
```

---

## ⚙️ Запуск сервисов

### 1. Создание systemd сервисов

```bash
# Backend
sudo nano /etc/systemd/system/oncomind-backend.service
```

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
# AI Pipeline
sudo nano /etc/systemd/system/oncomind-ai.service
```

```ini
[Unit]
Description=OncoMind AI Pipeline
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/oncomind/oncology_ai_assistant
ExecStart=/var/www/oncomind/oncology_ai_assistant/venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Активация и запуск

```bash
sudo systemctl daemon-reload
sudo systemctl enable oncomind-backend
sudo systemctl enable oncomind-ai
sudo systemctl start oncomind-backend
sudo systemctl start oncomind-ai
```

---

## 🌐 Настройка Nginx

```bash
sudo nano /etc/nginx/sites-available/oncomind
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    root /var/www/oncomind/frontend;
    index index.html;
    
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 15M;
    }
    
    location /ai-api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 55M;
        rewrite ^/ai-api/(.*) /$1 break;
    }
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
# Активация
sudo ln -s /etc/nginx/sites-available/oncomind /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔒 Настройка SSL

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

---

## ✅ Проверка работы

```bash
# Проверка Backend
curl http://127.0.0.1:5000/api/users

# Проверка AI Pipeline
curl http://127.0.0.1:8000/health

# Проверка через домен
curl https://your-domain.com/api/users
```

---

## 📊 Мониторинг

```bash
# Статус сервисов
sudo systemctl status oncomind-backend
sudo systemctl status oncomind-ai

# Логи в реальном времени
sudo journalctl -u oncomind-backend -f
sudo journalctl -u oncomind-ai -f

# Логи Nginx
sudo tail -f /var/log/nginx/oncomind.access.log
sudo tail -f /var/log/nginx/oncomind.error.log
```

---

## 🔄 Обновление

```bash
cd /var/www/oncomind

# Обновление кода
sudo git pull origin main

# Обновление зависимостей
cd backend && source venv/bin/activate && pip install -r requirements.txt && deactivate
cd ../oncology_ai_assistant && source venv/bin/activate && pip install -r requirements.txt && deactivate

# Перезапуск
sudo systemctl restart oncomind-backend
sudo systemctl restart oncomind-ai
sudo systemctl restart nginx
```

---

## 🆘 Решение проблем

### Backend не запускается

```bash
# Проверка логов
sudo journalctl -u oncomind-backend -n 50

# Проверка порта
sudo netstat -tulpn | grep 5000

# Ручной запуск для отладки
cd /var/www/oncomind/backend
source venv/bin/activate
python app.py
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

### Ошибки Nginx

```bash
# Проверка конфигурации
sudo nginx -t

# Проверка логов
sudo tail -f /var/log/nginx/oncomind.error.log
```

---

## 📞 Контакты

- Email: team@oncomind.ai
- Telegram: @oncomind

---

**Версия:** 2.0  
**Обновлено:** Февраль 2026
