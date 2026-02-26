#!/bin/bash
# =============================================================================
# OncoMind AI Deploy Script
# =============================================================================
# Автоматический деплой AI сервера на VPS
# =============================================================================

set -e

echo "🚀 OncoMind AI Deploy..."

# 1. Остановка сервисов
echo "🛑 Остановка сервисов..."
systemctl stop oncomind || true

# 2. Обновление из репозитория
echo "📥 Обновление из репозитория..."
cd /var/www/oncomind
git pull origin main

# 3. Установка зависимостей
echo "📦 Установка зависимостей..."
cd oncology_ai_assistant

# Создаём venv если нет
if [ ! -d "venv" ]; then
    echo "🔧 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем и устанавливаем
source venv/bin/activate
pip install -r requirements.txt
deactivate

# 4. Копирование рекомендаций
echo "📚 Копирование клинических рекомендаций..."
cp ../backend/knowledge_base/*.html knowledge_base_data/minzdrav/ 2>/dev/null || true

# 5. Проверка .env
echo "🔧 Проверка конфигурации..."
if [ ! -f .env ]; then
    echo "⚠️  .env не найден. Создайте файл с вашими Yandex Cloud credentials."
    echo "   YC_FOLDER_ID=..."
    echo "   YC_IAM_TOKEN=..."
    exit 1
fi

# 6. Запуск AI сервера
echo "🤖 Запуск AI сервера (порт 8000)..."
cd /var/www/oncomind/oncology_ai_assistant

# Останавливаем предыдущий процесс если есть
pkill -f "uvicorn src.core.main:app" || true
sleep 2

# Запускаем в фоне через venv
source venv/bin/activate
nohup python -m uvicorn src.core.main:app --host 0.0.0.0 --port 8000 > /var/log/oncomind_ai.log 2>&1 &
echo $! > /var/run/oncomind_ai.pid
deactivate

sleep 5

# 7. Проверка
echo "✅ Проверка..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✅ AI сервер работает!"
else
    echo "❌ AI сервер не отвечает. Проверьте логи: tail -f /var/log/oncomind_ai.log"
    exit 1
fi

# 8. Запуск Flask
echo "🔄 Запуск Flask backend..."
systemctl start oncomind

# 9. Финальная проверка
echo "🎯 Финальная проверка..."
sleep 3

if systemctl is-active --quiet oncomind; then
    echo "✅ Flask backend работает!"
else
    echo "❌ Flask backend не работает. Проверьте: journalctl -u oncomind -f"
    exit 1
fi

echo ""
echo "🎉 Деплой завершён успешно!"
echo ""
echo "📊 Статус:"
echo "   AI сервер:  http://localhost:8000"
echo "   Flask:      http://localhost:5000"
echo "   Сайт:       https://oncomind.ru"
echo ""
echo "📋 Логи:"
echo "   AI:  tail -f /var/log/oncomind_ai.log"
echo "   Flask: journalctl -u oncomind -f"
echo ""
