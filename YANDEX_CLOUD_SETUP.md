# 🔑 Yandex Cloud Setup Guide

## Быстрая настройка за 15 минут

### 1️⃣ Создайте сервисный аккаунт (5 мин)

**Через веб-консоль:**

1. Перейдите на https://console.cloud.yandex.ru/
2. Войдите под аккаунтом Яндекс
3. Выберите облако → каталог (или создайте новый)
4. **Запомните ID каталога** (начинается с `b1c...`)
5. left menu → **Service Accounts** → **Create service account**
6. Name: `oncomind-ai`
7. Role: **ai.languageModels.user**
8. Click **Create**

---

### 2️⃣ Создайте ключ (3 мин)

1. В списке аккаунтов нажмите `oncomind-ai`
2. **Authorized keys** → **Create new key**
3. Скачайте файл `key.json`
4. **Переименуйте** в `oncomind_sa_key.json`
5. **Положите** в папку: `d:\M2\OncoMindFull\oncology_ai_assistant\`

---

### 3️⃣ Получите IAM токен (2 мин)

**Через CLI (если установлен yc):**

```bash
cd d:\M2\OncoMindFull\oncology_ai_assistant
yc iam create-token --key-file oncomind_sa_key.json
```

**Через API (если нет yc):**

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d @oncomind_sa_key.json \
  https://iam.api.cloud.yandex.net/iam/v1/tokens
```

Сохраните токен (начинается с `t1.`) — он нужен для тестов!

---

### 4️⃣ Настройте .env (2 мин)

```bash
cd d:\M2\OncoMindFull\oncology_ai_assistant
copy .env.example .env
```

**Откройте `.env` и заполните:**

```env
YC_FOLDER_ID=b1c...                    # ← Ваш ID каталога
YC_SERVICE_ACCOUNT_KEY=oncomind_sa_key.json
YC_IAM_TOKEN=t1....                    # ← Ваш токен
AI_PORT=8000
DEBUG=True
```

---

### 5️⃣ Установите зависимости (3 мин)

```bash
cd d:\M2\OncoMindFull\oncology_ai_assistant
pip install -r requirements.txt
```

---

### 6️⃣ Запустите AI сервер

```bash
uvicorn src.core.main:app --host 0.0.0.0 --port 8000 --reload
```

**Проверьте:**

- Откройте http://localhost:8000/health
- Должно вернуться: `{"status":"healthy"}`

---

## 🧪 Тестирование

### Тест 1: Проверка YandexGPT

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Пациенту назначен доксорубицин 60 мг/м2. Проверь совместимость.\",\"mode\":\"doctor\"}"
```

**Ответ должен содержать:**
- Анализ препарата
- Проверку совместимости
- Рекомендации

---

### Тест 2: Поиск по рекомендациям

```bash
curl http://localhost:8000/api/guidelines/search?q=рак%20молочной%20железы
```

---

## 💰 Стоимость

**YandexGPT тарифы:**

- ~0.5-1₽ за 1000 токенов
- 1 запрос = ~100-300 токенов
- **Для тестов:** ~100-300₽/мес
- **Для продакшена:** ~1000-3000₽/мес

**Лимиты:**
- 1 млн токенов в месяц по умолчанию
- Можно увеличить в консоли

---

## 🔒 Безопасность

**Никогда не коммитьте:**
- `.env` файл
- `oncomind_sa_key.json`
- IAM токены

**Добавьте в `.gitignore`:**

```
.env
*.json
!config.json
logs/
*.log
```

---

## ❓ Troubleshooting

### Ошибка: "IAM токен недействителен"

**Решение:**
- Токен действует 1 час
- Получите новый: `yc iam create-token --key-file oncomind_sa_key.json`
- Обновите в `.env`

### Ошибка: "Нет доступа к YandexGPT"

**Решение:**
- Проверьте роль у сервисного аккаунта
- Должна быть: `ai.languageModels.user`
- Добавьте: `yc iam service-account add-role --role ai.languageModels.user --service-account-name oncomind-ai`

### Ошибка: "Каталог не найден"

**Решение:**
- Проверьте ID каталога
- Должен начинаться с `b1c...`
- Получите: `yc resource-manager folder list`

---

## 📞 Контакты

- Telegram: @oncomind
- Email: team@oncomind.ai
