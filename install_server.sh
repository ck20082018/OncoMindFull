#!/bin/bash
# =============================================================================
# OncoMind - Скрипт автоматической установки на сервер
# =============================================================================
# Использование:
#   chmod +x install_server.sh
#   sudo ./install_server.sh
# =============================================================================

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Логирование
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка запуска от root
if [ "$EUID" -ne 0 ]; then 
    log_error "Запустите скрипт от root (sudo ./install_server.sh)"
    exit 1
fi

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================
APP_DIR="/var/www/oncomind"
BACKEND_USER="www-data"
BACKEND_PORT="5000"
AI_PORT="8000"
DOMAIN=""  # Будет запрошено у пользователя

# =============================================================================
# 1. ПОДГОТОВКА СЕРВЕРА
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 1: Обновление системы и установка пакетов"
log_info "=================================================="

apt update
apt upgrade -y

apt install -y \
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

log_success "Пакеты установлены"

# =============================================================================
# 2. НАСТРОЙКА БРАНДМАУЭРА
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 2: Настройка брандмауэра (UFW)"
log_info "=================================================="

ufw allow OpenSSH
ufw allow 'Nginx Full'
echo "y" | ufw enable

log_success "Брандмауэр настроен"

# =============================================================================
# 3. НАСТРОЙКА FAIL2BAN
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 3: Настройка Fail2Ban"
log_info "=================================================="

cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

cat > /etc/fail2ban/jail.d/nginx.conf << 'EOF'
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
EOF

systemctl enable fail2ban
systemctl restart fail2ban

log_success "Fail2Ban настроен"

# =============================================================================
# 4. СОЗДАНИЕ ДИРЕКТОРИЙ
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 4: Создание директорий"
log_info "=================================================="

mkdir -p $APP_DIR
chown -R $BACKEND_USER:$BACKEND_USER $APP_DIR

log_success "Директории созданы"

# =============================================================================
# 5. УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 5: Установка Python зависимостей"
log_info "=================================================="

# Backend
log_info "Установка зависимостей Backend..."
cd $APP_DIR/backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# AI Pipeline
log_info "Установка зависимостей AI Pipeline..."
cd $APP_DIR/oncology_ai_assistant

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

log_success "Python зависимости установлены"

# =============================================================================
# 6. НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 6: Настройка переменных окружения"
log_info "=================================================="

# Запрос домена
read -p "Введите ваш домен (например, oncomind.ru): " DOMAIN

# Генерация SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Backend .env
log_info "Создание .env для Backend..."
cat > $APP_DIR/backend/.env << EOF
# OncoMind Backend - Переменные окружения
SECRET_KEY=$SECRET_KEY
ALLOWED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
BASE_DIR=$APP_DIR/backend
USERS_FILE=$APP_DIR/backend/data/users.json
MAX_FILE_SIZE=10485760
AI_PIPELINE_URL=http://127.0.0.1:$AI_PORT
HOST=127.0.0.1
PORT=$BACKEND_PORT
DEBUG=False
LOG_LEVEL=INFO
EOF

# AI Pipeline .env
log_info "Создание .env для AI Pipeline..."
read -p "Введите Yandex Cloud Folder ID: " YC_FOLDER_ID
read -p "Введите Yandex Cloud API Key: " YC_API_KEY

cat > $APP_DIR/oncology_ai_assistant/.env << EOF
# OncoMind AI Pipeline - Переменные окружения
YC_FOLDER_ID=$YC_FOLDER_ID
YC_API_KEY=$YC_API_KEY
YC_SERVICE_ACCOUNT_KEY=$APP_DIR/oncology_ai_assistant/oncomind_sa_key.json
AI_HOST=127.0.0.1
AI_PORT=$AI_PORT
DEBUG=False
DATABASE_URL=sqlite:///./oncomind_ai.db
LOG_LEVEL=INFO
LOG_FILE=$APP_DIR/oncology_ai_assistant/logs/oncomind_ai.log
ALLOWED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
EOF

log_success "Переменные окружения настроены"

# =============================================================================
# 7. СОЗДАНИЕ SYSTEMD СЕРВИСОВ
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 7: Создание systemd сервисов"
log_info "=================================================="

# Backend сервис
cat > /etc/systemd/system/oncomind-backend.service << EOF
[Unit]
Description=OncoMind Backend (Flask)
After=network.target oncomind-ai.service

[Service]
Type=exec
User=$BACKEND_USER
Group=$BACKEND_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin"
ExecStart=$APP_DIR/backend/venv/bin/python app.py
Restart=always
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal
SyslogIdentifier=oncomind-backend

[Install]
WantedBy=multi-user.target
EOF

# AI Pipeline сервис
cat > /etc/systemd/system/oncomind-ai.service << EOF
[Unit]
Description=OncoMind AI Pipeline (FastAPI)
After=network.target

[Service]
Type=exec
User=$BACKEND_USER
Group=$BACKEND_USER
WorkingDirectory=$APP_DIR/oncology_ai_assistant
Environment="PATH=$APP_DIR/oncology_ai_assistant/venv/bin"
ExecStart=$APP_DIR/oncology_ai_assistant/venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port $AI_PORT
Restart=always
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal
SyslogIdentifier=oncomind-ai

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable oncomind-ai
systemctl enable oncomind-backend
systemctl start oncomind-ai
systemctl start oncomind-backend

log_success "Systemd сервисы созданы и запущены"

# =============================================================================
# 8. НАСТРОЙКА NGINX
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 8: Настройка Nginx"
log_info "=================================================="

cat > /etc/nginx/sites-available/oncomind << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    root $APP_DIR/frontend;
    index index.html;

    access_log /var/log/nginx/oncomind.access.log;
    error_log /var/log/nginx/oncomind.error.log;

    location /static {
        alias $APP_DIR/frontend;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /api/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        client_max_body_size 15M;
    }

    location /ai-api/ {
        proxy_pass http://127.0.0.1:$AI_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 180s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        client_max_body_size 55M;
        
        rewrite ^/ai-api/(.*) /\$1 break;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

ln -sf /etc/nginx/sites-available/oncomind /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl restart nginx

log_success "Nginx настроен"

# =============================================================================
# 9. НАСТРОЙКА SSL (LET'S ENCRYPT)
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 9: Настройка SSL (Let's Encrypt)"
log_info "=================================================="

read -p "Настроить SSL сертификат? (y/n): " SETUP_SSL

if [ "$SETUP_SSL" = "y" ]; then
    certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
    
    systemctl status certbot.timer
    
    log_success "SSL настроен"
else
    log_warning "SSL не настроен (можно настроить позже через certbot)"
fi

# =============================================================================
# 10. ПРОВЕРКА РАБОТЫ
# =============================================================================
echo ""
log_info "=================================================="
log_info "ШАГ 10: Проверка работы"
log_info "=================================================="

sleep 5

log_info "Проверка Backend..."
curl -s http://127.0.0.1:$BACKEND_PORT/api/users | head -c 100 && log_success "Backend работает" || log_error "Backend не работает"

log_info "Проверка AI Pipeline..."
curl -s http://127.0.0.1:$AI_PORT/health | head -c 100 && log_success "AI Pipeline работает" || log_error "AI Pipeline не работает"

# =============================================================================
# ЗАВЕРШЕНИЕ
# =============================================================================
echo ""
log_success "=================================================="
log_success "УСТАНОВКА ЗАВЕРШЕНА!"
log_success "=================================================="
echo ""
echo "Домен: $DOMAIN"
echo "Backend: http://127.0.0.1:$BACKEND_PORT"
echo "AI Pipeline: http://127.0.0.1:$AI_PORT"
echo ""
echo "Полезные команды:"
echo "  Проверка статуса Backend:  sudo systemctl status oncomind-backend"
echo "  Проверка статуса AI:       sudo systemctl status oncomind-ai"
echo "  Просмотр логов Backend:    sudo journalctl -u oncomind-backend -f"
echo "  Просмотр логов AI:         sudo journalctl -u oncomind-ai -f"
echo ""
echo "Документация: DEPLOY_SERVER.md"
echo ""
