#!/bin/bash
# OncoMind - Диагностика сервера
# Использование: sudo bash diagnose.sh

echo "=============================================="
echo "🔍 OncoMind - Диагностика сервера"
echo "=============================================="
echo ""

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

function check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# 1. Проверка ОС и архитектуры
echo -e "${BLUE}📌 1. Информация о системе${NC}"
echo "-------------------------------------------"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d '=' -f2 | tr -d '"')"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "Uptime: $(uptime -p 2>/dev/null || uptime)"
echo ""

# 2. Проверка Python
echo -e "${BLUE}📌 2. Python${NC}"
echo "-------------------------------------------"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python3 не установлен${NC}"
    echo "   Установите: sudo apt install python3 python3-pip python3-venv"
fi

if command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version)
    echo -e "${GREEN}✅ $PIP_VERSION${NC}"
else
    echo -e "${RED}❌ Pip3 не установлен${NC}"
fi
echo ""

# 3. Проверка Git
echo -e "${BLUE}📌 3. Git${NC}"
echo "-------------------------------------------"
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    echo -e "${GREEN}✅ $GIT_VERSION${NC}"
else
    echo -e "${RED}❌ Git не установлен${NC}"
fi
echo ""

# 4. Проверка Nginx
echo -e "${BLUE}📌 4. Nginx${NC}"
echo "-------------------------------------------"
if command -v nginx &> /dev/null; then
    NGINX_VERSION=$(nginx -v 2>&1)
    echo -e "${GREEN}✅ $NGINX_VERSION${NC}"
    
    # Статус сервиса
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✅ Nginx запущен${NC}"
    else
        echo -e "${RED}❌ Nginx остановлен${NC}"
        echo "   Запуск: sudo systemctl start nginx"
    fi
    
    # Конфигурация
    if [ -f /etc/nginx/sites-available/oncomind ]; then
        echo -e "${GREEN}✅ Конфиг OncoMind существует${NC}"
    else
        echo -e "${RED}❌ Конфиг OncoMind не найден${NC}"
        echo "   Путь: /etc/nginx/sites-available/oncomind"
    fi
    
    if [ -L /etc/nginx/sites-enabled/oncomind ]; then
        echo -e "${GREEN}✅ Конфиг включен в sites-enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  Конфиг не включен в sites-enabled${NC}"
        echo "   Команда: sudo ln -s /etc/nginx/sites-available/oncomind /etc/nginx/sites-enabled/"
    fi
else
    echo -e "${RED}❌ Nginx не установлен${NC}"
fi
echo ""

# 5. Проверка SSL сертификатов
echo -e "${BLUE}📌 5. SSL сертификаты (Let's Encrypt)${NC}"
echo "-------------------------------------------"
if command -v certbot &> /dev/null; then
    CERTBOT_VERSION=$(certbot --version)
    echo -e "${GREEN}✅ $CERTBOT_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  Certbot не установлен${NC}"
    echo "   Установите: sudo apt install certbot python3-certbot-nginx"
fi

# Проверка сертификатов
if [ -d /etc/letsencrypt/live ]; then
    echo -e "${GREEN}✅ Директория сертификатов существует${NC}"
    echo "   Сертификаты:"
    sudo ls -la /etc/letsencrypt/live/ 2>/dev/null | grep -v "^total" | grep -v "^d"
else
    echo -e "${RED}❌ Директория сертификатов не найдена${NC}"
    echo "   Получите сертификат: sudo certbot certonly --standalone -d ваш-домен"
fi
echo ""

# 6. Проверка systemd сервиса OncoMind
echo -e "${BLUE}📌 6. Сервис OncoMind${NC}"
echo "-------------------------------------------"
if [ -f /etc/systemd/system/oncomind.service ]; then
    echo -e "${GREEN}✅ Файл сервиса существует${NC}"
    
    if systemctl is-active --quiet oncomind; then
        echo -e "${GREEN}✅ Сервис запущен${NC}"
        echo "   Статус: active"
    else
        echo -e "${RED}❌ Сервис остановлен${NC}"
        echo "   Запуск: sudo systemctl start oncomind"
    fi
    
    if systemctl is-enabled --quiet oncomind; then
        echo -e "${GREEN}✅ Сервис включен в автозагрузку${NC}"
    else
        echo -e "${YELLOW}⚠️  Сервис не включен в автозагрузку${NC}"
        echo "   Команда: sudo systemctl enable oncomind"
    fi
else
    echo -e "${RED}❌ Файл сервиса не найден${NC}"
    echo "   Путь: /etc/systemd/system/oncomind.service"
fi
echo ""

# 7. Проверка репозитория и кода
echo -e "${BLUE}📌 7. Репозиторий и код${NC}"
echo "-------------------------------------------"
if [ -d /var/www/oncomind/.git ]; then
    echo -e "${GREEN}✅ Репозиторий существует${NC}"
    cd /var/www/oncomind
    
    # Текущая ветка
    BRANCH=$(git branch --show-current)
    echo "   Ветка: $BRANCH"
    
    # Последний коммит
    LAST_COMMIT=$(git log -1 --pretty=format:"%h - %s (%ar)" 2>/dev/null)
    echo "   Последний коммит: $LAST_COMMIT"
    
    # Статус
    CHANGES=$(git status --porcelain)
    if [ -z "$CHANGES" ]; then
        echo -e "${GREEN}✅ Нет локальных изменений${NC}"
    else
        echo -e "${YELLOW}⚠️  Есть локальные изменения:${NC}"
        echo "$CHANGES"
    fi
else
    echo -e "${RED}❌ Репозиторий не найден в /var/www/oncomind${NC}"
    echo "   Клонирование: sudo git clone https://github.com/ck20082018/OncoMindFull.git /var/www/oncomind"
fi
echo ""

# 8. Проверка виртуального окружения и зависимостей
echo -e "${BLUE}📌 8. Виртуальное окружение и зависимости${NC}"
echo "-------------------------------------------"
if [ -d /var/www/oncomind/backend/venv ]; then
    echo -e "${GREEN}✅ Виртуальное окружение существует${NC}"
    
    # Проверка Flask
    if /var/www/oncomind/backend/venv/bin/python -c "import flask" 2>/dev/null; then
        FLASK_VERSION=$(/var/www/oncomind/backend/venv/bin/pip show flask | grep Version)
        echo -e "${GREEN}✅ $FLASK_VERSION${NC}"
    else
        echo -e "${RED}❌ Flask не установлен${NC}"
    fi
    
    # Проверка flask-cors
    if /var/www/oncomind/backend/venv/bin/python -c "import flask_cors" 2>/dev/null; then
        CORS_VERSION=$(/var/www/oncomind/backend/venv/bin/pip show flask-cors | grep Version)
        echo -e "${GREEN}✅ $CORS_VERSION${NC}"
    else
        echo -e "${RED}❌ Flask-CORS не установлен${NC}"
    fi
else
    echo -e "${RED}❌ Виртуальное окружение не найдено${NC}"
    echo "   Создание: cd /var/www/oncomind/backend && python3 -m venv venv"
fi
echo ""

# 9. Проверка портов
echo -e "${BLUE}📌 9. Сетевые порты${NC}"
echo "-------------------------------------------"
echo "Порт 80 (HTTP):"
if sudo ss -tlnp | grep -q ':80'; then
    sudo ss -tlnp | grep ':80'
    echo -e "${GREEN}✅ Слушает${NC}"
else
    echo -e "${RED}❌ Не слушает${NC}"
fi

echo ""
echo "Порт 443 (HTTPS):"
if sudo ss -tlnp | grep -q ':443'; then
    sudo ss -tlnp | grep ':443'
    echo -e "${GREEN}✅ Слушает${NC}"
else
    echo -e "${RED}❌ Не слушает${NC}"
fi

echo ""
echo "Порт 5000 (Backend Flask):"
if sudo ss -tlnp | grep -q ':5000'; then
    sudo ss -tlnp | grep ':5000'
    echo -e "${GREEN}✅ Слушает${NC}"
else
    echo -e "${RED}❌ Не слушает${NC}"
    echo "   Проверьте: sudo systemctl status oncomind"
fi
echo ""

# 10. Проверка брандмауэра (UFW)
echo -e "${BLUE}📌 10. Брандмауэр (UFW)${NC}"
echo "-------------------------------------------"
if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "Status: active"; then
        echo -e "${YELLOW}⚠️  UFW активен${NC}"
        echo "   Разрешенные порты:"
        sudo ufw status | grep -E "^[0-9]+" || echo "   Нет правил"
    else
        echo -e "${GREEN}✅ UFW не активен${NC}"
    fi
else
    echo -e "${GREEN}✅ UFW не установлен${NC}"
fi
echo ""

# 11. Проверка логов
echo -e "${BLUE}📌 11. Последние ошибки (логи)${NC}"
echo "-------------------------------------------"
echo "Backend (последние 5 строк):"
sudo journalctl -u oncomind -n 5 --no-pager 2>/dev/null || echo "   Нет логов"

echo ""
echo "Nginx errors (последние 5 строк):"
sudo tail -5 /var/log/nginx/oncomind.error.log 2>/dev/null || echo "   Нет логов"

echo ""
echo "Nginx access (последние 5 строк):"
sudo tail -5 /var/log/nginx/oncomind.access.log 2>/dev/null || echo "   Нет логов"
echo ""

# 12. Проверка прав доступа
echo -e "${BLUE}📌 12. Права доступа${NC}"
echo "-------------------------------------------"
if [ -d /var/www/oncomind ]; then
    echo "Владелец /var/www/oncomind:"
    ls -ld /var/www/oncomind
fi

if [ -d /var/www/oncomind/backend ]; then
    echo "Владелец /var/www/oncomind/backend:"
    ls -ld /var/www/oncomind/backend
fi
echo ""

# 13. Проверка .env файла
echo -e "${BLUE}📌 13. Конфигурация (.env)${NC}"
echo "-------------------------------------------"
if [ -f /var/www/oncomind/backend/.env ]; then
    echo -e "${GREEN}✅ .env файл существует${NC}"
    echo "   Переменные:"
    sudo cat /var/www/oncomind/backend/.env 2>/dev/null | grep -v "^#" | grep -v "^$"
else
    echo -e "${YELLOW}⚠️  .env файл не найден${NC}"
    echo "   Создайте: /var/www/oncomind/backend/.env"
fi
echo ""

# Итог
echo "=============================================="
echo -e "${BLUE}📊 ИТОГИ${NC}"
echo "=============================================="

ISSUES=0

# Проверка критических компонентов
if ! systemctl is-active --quiet nginx; then ((ISSUES++)); fi
if ! systemctl is-active --quiet oncomind; then ((ISSUES++)); fi
if ! sudo ss -tlnp | grep -q ':5000'; then ((ISSUES++)); fi
if ! sudo ss -tlnp | grep -q ':443'; then ((ISSUES++)); fi
if [ ! -f /etc/nginx/sites-available/oncomind ]; then ((ISSUES++)); fi
if [ ! -d /var/www/oncomind/backend/venv ]; then ((ISSUES++)); fi

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ Все системы работают корректно!${NC}"
    echo ""
    echo "🌐 Приложение доступно по адресу:"
    echo "   https://155.212.182.149"
else
    echo -e "${RED}❌ Найдено проблем: $ISSUES${NC}"
    echo ""
    echo "🔧 Рекомендации:"
    echo "   1. Запустите остановленные сервисы"
    echo "   2. Проверьте логи ошибок выше"
    echo "   3. Убедитесь что все порты открыты"
fi

echo ""
echo "=============================================="
echo "Для обновления выполните:"
echo "   cd /var/www/oncomind && sudo git pull origin main"
echo "   sudo systemctl restart oncomind"
echo "   sudo nginx -t && sudo systemctl reload nginx"
echo "=============================================="
