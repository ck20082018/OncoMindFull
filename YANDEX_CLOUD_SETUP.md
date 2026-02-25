# 🔑 Настройка Yandex Cloud для OncoMind

## 📋 Шаг 1: Регистрация в Yandex Cloud

1. Перейди на https://cloud.yandex.ru
2. Зарегистрируйся (нужен Яндекс ID)
3. Привяжи карту (дадут 4000₽ на тестирование)

---

## 📋 Шаг 2: Создание сервисного аккаунта

### Вариант A: Через консоль (проще)

```bash
# Установи Yandex Cloud CLI (если нет)
# https://cloud.yandex.ru/docs/cli/quickstart

# Авторизуйся
yc init

# Создай сервисный аккаунт
yc iam service-account create --name oncomind-ai

# Добавь роль для доступа к YandexGPT
yc iam service-account add-role \
  --role ai.languageModels.user \
  --service-account-name oncomind-ai

# Создай ключ (сохранится в файл)
yc iam key create \
  --service-account-name oncomind-ai \
  --output oncomind_sa_key.json
```

### Вариант B: Через веб-консоль

1. Зайди в https://console.cloud.yandex.ru
2. **Сервисные аккаунты** → **Создать**
3. Имя: `oncomind-ai`
4. Роль: **ai.languageModels.user**
5. **Создать ключ** → скачается JSON файл

---

## 📋 Шаг 3: Получить ID каталога

```bash
# Через CLI
yc resource-manager folder list

# Или в веб-консоли:
# Выбери проект → скопируй ID каталога из URL
# Выглядит как: b1cxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 📋 Шаг 4: Настройка .env файла

### Для AI Pipeline (FastAPI)

**Файл:** `d:\M2\OncoMindFull\oncology_ai_assistant\.env`

```env
# =============================================================================
# YANDEX CLOUD - Аутентификация
# =============================================================================

# ID каталога (обязательно)
YC_FOLDER_ID=b1cxxxxxxxxxxxxxxxxxxxxxxxxxx

# Сервисный аккаунт (путь к JSON ключу)
YC_SERVICE_ACCOUNT_KEY=oncomind_sa_key.json

# Или IAM-токен для быстрого теста (действует 1 час)
# Получить через: yc iam create-token
# YC_IAM_TOKEN=t1.xxxxxxxxxxxxx

# =============================================================================
# НАСТРОЙКИ ПРИЛОЖЕНИЯ
# =============================================================================
LOG_LEVEL=INFO
KNOWLEDGE_BASE_DIR=knowledge_base_data/minzdrav
```

### Для Flask Backend (если будет интегрирован)

**Файл:** `d:\M2\OncoMindFull\backend\.env`

```env
# Путь к AI Pipeline
AI_PIPELINE_URL=http://127.0.0.1:8000

# Или напрямую YandexGPT (если AI Pipeline не используется)
YC_FOLDER_ID=b1cxxxxxxxxxxxxxxxxxxxxxxxxxx
YC_SERVICE_ACCOUNT_KEY=../oncology_ai_assistant/oncomind_sa_key.json
```

---

## 📋 Шаг 5: Проверка подключения

### Тест через CLI

```bash
# Создай IAM-токен
yc iam create-token

# Проверь YandexGPT
curl -X POST \
  'https://llm.api.cloud.yandex.net/foundationModels/v1/completion' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $(yc iam create-token)" \
  -H "x-folder-id: b1cxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -d '{
    "modelUri": "gpt://b1cxxxxxxxxxxxxxxxxxxxxxxxxxx/yandexgpt-pro",
    "completionOptions": {
      "temperature": 0.1,
      "maxTokens": 100
    },
    "messages": [
      {"role": "user", "text": "Привет! Как дела?"}
    ]
  }'
```

### Тест через Python

```python
# test_yandex_gpt.py
from oncology_ai_assistant.src.llm.yandex_client import (
    YandexGPTClient,
    YandexGPTConfig
)
import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv('oncology_ai_assistant/.env')

# Создаём конфиг
config = YandexGPTConfig(
    folder_id=os.getenv('YC_FOLDER_ID'),
    service_account_key_path=os.getenv('YC_SERVICE_ACCOUNT_KEY')
)

# Создаём клиент
client = YandexGPTClient(config)

# Тестовый запрос
response = client.complete(
    user_text="Привет! Напиши краткий ответ.",
    system_prompt="Ты полезный ассистент.",
    temperature=0.1,
    max_tokens=100
)

print(f"Ответ: {response.text}")
print(f"Токены: {response.total_tokens}")
print(f"Время: {response.processing_time:.2f}с")
```

**Запуск:**
```bash
cd d:\M2\OncoMindFull
python test_yandex_gpt.py
```

---

## 📋 Шаг 6: Запуск AI Pipeline

```bash
# Перейди в директорию AI
cd d:\M2\OncoMindFull\oncology_ai_assistant

# Установи зависимости (если нет)
pip install -r requirements.txt

# Запусти FastAPI сервер
uvicorn src.core.main:app --host 0.0.0.0 --port 8000 --reload
```

**Проверка:**
```bash
# Health check
curl http://localhost:8000/health

# Список рекомендаций
curl http://localhost:8000/api/guidelines/list
```

---

## 💰 Стоимость YandexGPT

### Тарифы (на 2026 год)

| Модель | Стоимость |
|--------|-----------|
| **YandexGPT Pro** | ~1₽ за 1000 токенов |
| **YandexGPT Lite** | ~0.3₽ за 1000 токенов |

### Примерный расход

| Сценарий | Токены/запрос | Запросов/день | ₽/мес |
|----------|---------------|---------------|-------|
| **Демо** | ~500 | 10 | ~150 |
| **Тесты** | ~1000 | 50 | ~1500 |
| **Продакшен** | ~2000 | 200 | ~12000 |

**Гранты:**
- Новые пользователи: 4000₽ на 60 дней
- Студенты: дополнительные гранты

---

## 🔒 Безопасность

### Что нельзя делать:

```
❌ Коммитить .env с реальными ключами в Git
❌ Публиковать oncomind_sa_key.json в репозитории
❌ Передавать ключи третьим лицам
```

### Что нужно делать:

```
✅ Добавить .env в .gitignore
✅ Хранить ключи в секретах (GitHub Secrets, CI/CD)
✅ Регулярно обновлять ключи (раз в 3-6 мес)
✅ Использовать разные аккаунты для dev/prod
```

---

## 🛠️ Решение проблем

### Ошибка: "IAM-токен недействителен"

**Решение:**
```bash
# Получить новый токен
yc iam create-token

# Или пересоздать ключ сервисного аккаунта
yc iam key create --service-account-name oncomind-ai
```

### Ошибка: "Нет доступа к YandexGPT"

**Решение:**
```bash
# Проверь роли
yc iam service-account list-roles oncomind-ai

# Должна быть: ai.languageModels.user
# Если нет — добавь:
yc iam service-account add-role \
  --role ai.languageModels.user \
  --service-account-name oncomind-ai
```

### Ошибка: "Folder ID не найден"

**Решение:**
```bash
# Проверь список каталогов
yc resource-manager folder list

# Скопируй правильный ID (выглядит как b1cxxxx...)
```

---

## 📞 Поддержка

- Документация Yandex Cloud: https://cloud.yandex.ru/docs
- YandexGPT: https://cloud.yandex.ru/docs/yandexgpt/
- Telegram: @oncomind

---

## ✅ Чеклист готовности

```
□ Yandex Cloud аккаунт создан
□ Сервисный аккаунт создан
□ Роль ai.languageModels.user добавлена
□ Ключ скачан (oncomind_sa_key.json)
□ ID каталога получен
□ .env файл создан и заполнен
□ Тестовый запрос успешен
□ AI Pipeline запущен (порт 8000)
```

**После этого AI-анализ готов к работе!** 🎉
