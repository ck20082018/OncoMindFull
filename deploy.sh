#!/bin/bash
# Скрипт деплоя OncoMind на VPS
# Использование: ./deploy.sh

set -e

echo "🚀 Деплой OncoMind..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка запуска от root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Ошибка: запустите скрипт от root (sudo ./deploy.sh)${NC}"
    exit 1
fi

# 1. Обновление кода из Git
echo -e "${YELLOW}📦 Обновление кода из Git...${NC}"
cd /var/www/oncomind
git pull origin main
echo -e "${GREEN}✅ Код обновлен${NC}"

# 2. Установка зависимостей
echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
cd /var/www/oncomind/backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
echo -e "${GREEN}✅ Зависимости установлены${NC}"

# 3. Перезапуск сервиса
echo -e "${YELLOW}🔄 Перезапуск сервиса...${NC}"
systemctl daemon-reload
systemctl restart oncomind
echo -e "${GREEN}✅ Сервис перезапущен${NC}"

# 4. Проверка статуса
echo -e "${YELLOW}📊 Статус сервиса:${NC}"
systemctl status oncomind --no-pager

# 5. Проверка Nginx
echo -e "${YELLOW}🔍 Проверка Nginx...${NC}"
nginx -t
if [ $? -eq 0 ]; then
    systemctl reload nginx
    echo -e "${GREEN}✅ Nginx конфигурация валидна${NC}"
else
    echo -e "${RED}❌ Ошибка конфигурации Nginx${NC}"
    exit 1
fi

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Деплой завершен успешно!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "📍 Приложение доступно по адресу: http://ваш-домен.ru"
echo ""
echo "📊 Логи:"
echo "   Backend: journalctl -u oncomind -f"
echo "   Nginx: tail -f /var/log/nginx/oncomind.error.log"
