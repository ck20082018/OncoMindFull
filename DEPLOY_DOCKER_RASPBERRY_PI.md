# Инструкция по деплою OncoMind на Raspberry Pi 5 через Docker

## 📋 Требования

- **Raspberry Pi 5** (4GB или 8GB RAM рекомендуется)
- **Raspberry Pi OS** (64-bit, Debian Bookworm)
- **МикроSD карта** от 32GB или **SSD через USB 3.0** (рекомендуется)
- **Доступ в интернет** для загрузки образов и Yandex Cloud API

---

## 🚀 Быстрый старт (5 минут)

### 1. Подготовка Raspberry Pi

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Установка Docker Compose
sudo apt install -y docker-compose-plugin

# Проверка установки
docker --version
docker compose version
```

### 2. Клонирование проекта

```bash
cd ~
git clone <ваш-репозиторий> OncoMindFull
cd OncoMindFull
```

Или скопируйте файлы через SCP:

```bash
# С вашего компьютера
scp -r d:/M2/OncoMindFull/* pi@<raspberry-ip>:/home/pi/OncoMindFull/
```

### 3. Настройка переменных окружения

```bash
# Копирование файла окружения
cp .env.docker .env

# Редактирование переменных
nano .env
```

**Обязательно измените:**

```env
# Сгенерируйте новый секретный ключ
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Ваш домен или IP
ALLOWED_ORIGINS=http://<raspberry-ip>

# Yandex Cloud credentials
YC_FOLDER_ID=b1xxxxxxxxxxxxxxxxxxxxxxxxxx
YC_API_KEY=xxxxxxxxxxxxxxxxxxxxxxx
```

### 4. Подготовка credentials Yandex Cloud

```bash
# Создание директории для credentials
mkdir -p oncology_ai_assistant/credentials

# Копирование ключа сервисного аккаунта
# Если у вас есть файл authorized_key.json:
cp /path/to/authorized_key.json oncology_ai_assistant/credentials/

# Или создайте через yc CLI:
# yc iam key create --service-account-name <sa-name> --output oncology_ai_assistant/credentials/authorized_key.json
```

### 5. Запуск через Docker Compose

```bash
# Сборка и запуск всех сервисов
docker compose up -d --build

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

### 6. Проверка работы

```bash
# Проверка Backend
curl http://localhost:5000/api/users

# Проверка AI Pipeline
curl http://localhost:8000/health

# Проверка через Nginx
curl http://localhost/api/users
```

**Откройте браузер:**
- `http://<raspberry-ip>` - основной интерфейс
- `http://<raspberry-ip>:5000` - backend API
- `http://<raspberry-ip>:8000` - AI pipeline

---

## ⚙️ Подробная настройка

### Структура Docker Compose

```yaml
services:
  backend:    # Flask API (порт 5000)
  ai:         # FastAPI AI Pipeline (порт 8000)
  nginx:      # Reverse proxy (порты 80, 443)
```

### Тома (Volumes)

| Том | Назначение |
|-----|------------|
| `backend_data` | База пользователей |
| `backend_uploads` | Загруженные файлы |
| `ai_index` | RAG индекс для поиска |
| `ai_logs` | Логи AI pipeline |

---

## 🔐 Настройка SSL (опционально)

### 1. Создание самоподписанного сертификата

```bash
# Создание директории для SSL
mkdir -p ssl
cd ssl

# Генерация сертификата
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout oncomind.key \
  -out oncomind.crt \
  -subj "/C=RU/ST=Moscow/L=Moscow/O=OncoMind/CN=<raspberry-ip>"
```

### 2. Обновление nginx.conf для HTTPS

Замените `listen 80;` на:

```nginx
listen 443 ssl;
ssl_certificate /etc/nginx/ssl/oncomind.crt;
ssl_certificate_key /etc/nginx/ssl/oncomind.key;

# Перенаправление HTTP на HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

### 3. Перезапуск Nginx

```bash
docker compose restart nginx
```

---

## 📊 Мониторинг и управление

### Управление сервисами

```bash
# Запуск
docker compose up -d

# Остановка
docker compose down

# Перезапуск
docker compose restart

# Пересборка
docker compose up -d --build --force-recreate

# Просмотр логов
docker compose logs -f [service_name]

# Статус
docker compose ps
```

### Мониторинг ресурсов

```bash
# Установка htop
sudo apt install -y htop

# Запуск
htop

# Использование Docker
docker stats

# Использование диска
df -h
du -sh ~/OncoMindFull
```

### Логи

```bash
# Все логи
docker compose logs -f

# Только backend
docker compose logs -f backend

# Только AI
docker compose logs -f ai

# Только nginx
docker compose logs -f nginx

# Последние 100 строк
docker compose logs --tail=100 backend
```

---

## 🔄 Обновление

### 1. Обновление кода

```bash
cd ~/OncoMindFull

# Если через git
git pull origin main

# Или скопируйте новые файлы
```

### 2. Пересборка и перезапуск

```bash
# Полная пересборка
docker compose up -d --build --force-recreate

# Или только перезапуск
docker compose restart
```

### 3. Очистка старых образов

```bash
# Удаление старых образов
docker image prune -a

# Очистка неиспользуемых томов
docker volume prune
```

---

## 🛠️ Решение проблем

### Backend не запускается

```bash
# Проверка логов
docker compose logs backend

# Проверка внутри контейнера
docker exec -it oncomind-backend bash
cd backend
python app.py
```

### AI Pipeline не запускается

```bash
# Проверка логов
docker compose logs ai

# Проверка внутри контейнера
docker exec -it oncomind-ai bash
cd oncology_ai_assistant
uvicorn src.core.main:app --host 0.0.0.0 --port 8000
```

### Ошибки памяти (OOM)

Raspberry Pi 5 может не хватать памяти для AI модели:

```bash
# Увеличение swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Измените CONF_SWAPSIZE=1024 на CONF_SWAPSIZE=4096
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Проблемы с EasyOCR на ARM

EasyOCR может не работать на ARM. Временно отключите OCR:

```bash
# В .env
OCR_USE_GPU=false
```

Или используйте упрощённую версию в Dockerfile.ai.

### Ошибки подключения к Yandex Cloud

```bash
# Проверка credentials
docker exec -it oncomind-ai bash
cat /app/oncology_ai_assistant/credentials/authorized_key.json

# Проверка IAM токена
docker exec -it oncomind-ai bash
yc iam create-token
```

### Контейнер не отвечает

```bash
# Перезапуск контейнера
docker compose restart [service_name]

# Полная пересборка
docker compose down
docker compose up -d --build --force-recreate

# Очистка кеша
docker builder prune -a
```

---

## 📈 Оптимизация для Raspberry Pi 5

### 1. Использование SSD вместо SD карты

```bash
# Подключение SSD через USB 3.0
# Копирование системы на SSD
sudo rpi-eeprom-update
sudo raspi-config
# Advanced Options > Boot Order > USB Boot
```

### 2. Оверклокинг (опционально)

```bash
# Редактирование config.txt
sudo nano /boot/firmware/config.txt

# Добавление (на свой страх и риск):
over_voltage=6
arm_freq=3000
gpu_freq=750
```

### 3. Охлаждение

Убедитесь, что Raspberry Pi 5 имеет активное охлаждение для стабильной работы.

---

## 📊 Производительность

| Компонент | RAM | CPU | Примечание |
|-----------|-----|-----|------------|
| Backend | ~100MB | Низкая | Flask API |
| AI Pipeline | ~2-4GB | Средняя | Зависит от модели |
| Nginx | ~10MB | Низкая | Reverse proxy |
| **Итого** | **~3-5GB** | **Средняя** | |

**Рекомендации:**
- Raspberry Pi 5 8GB - оптимально
- Raspberry Pi 5 4GB - возможно, потребуется swap
- SSD настоятельно рекомендуется для производительности

---

## 🆘 Аварийное восстановление

### Резервное копирование

```bash
# Бэкап данных пользователей
docker run --rm \
  -v oncomindfull_backend_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/backup_data.tar.gz /data

# Бэкап AI индекса
docker run --rm \
  -v oncomindfull_ai_index:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/backup_ai_index.tar.gz /data
```

### Восстановление

```bash
# Восстановление данных
docker run --rm \
  -v oncomindfull_backend_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/backup_data.tar.gz -C /

# Перезапуск
docker compose up -d
```

---

## 📞 Контакты поддержки

- Email: team@oncomind.ai
- Telegram: @oncomind

---

**Версия инструкции:** 1.0
**Дата:** Март 2026
**Платформа:** Raspberry Pi 5 (ARM64)
