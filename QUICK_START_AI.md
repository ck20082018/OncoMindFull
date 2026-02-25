# 🚀 OncoMind AI - Быстрый старт

## 📋 ЧТО ГОТОВО

✅ **Frontend** - все страницы работают  
✅ **Backend** - регистрация, вход, API  
✅ **Клинические рекомендации** - 12 HTML файлов с поиском  
✅ **AI Integration** - endpoint `/api/analyze` готов  
✅ **Тестовые пользователи** - doctor@oncomind.ai / Doctor123!

---

## 🔑 ШАГ 1: Получите ключи Yandex Cloud (15 мин)

### 1.1 Создайте сервисный аккаунт

1. Перейдите на https://console.cloud.yandex.ru/
2. Войдите под аккаунтом Яндекс
3. Выберите облако → каталог
4. **Запомните ID каталога** (начинается с `b1c...`)
5. left menu → **Service Accounts** → **Create service account**
6. Name: `oncomind-ai`
7. Role: **ai.languageModels.user**
8. Click **Create**

### 1.2 Создайте ключ

1. В списке аккаунтов нажмите `oncomind-ai`
2. **Authorized keys** → **Create new key**
3. Скачайте файл `key.json`
4. **Переименуйте** в `oncomind_sa_key.json`
5. **Положите** в папку: `d:\M2\OncoMindFull\oncology_ai_assistant\`

### 1.3 Получите IAM токен

**Через CLI (если установлен yc):**
```bash
cd d:\M2\OncoMindFull\oncology_ai_assistant
yc iam create-token --key-file oncomind_sa_key.json
```

**Или через API:**
```bash
curl -X POST -H "Content-Type: application/json" -d @oncomind_sa_key.json https://iam.api.cloud.yandex.net/iam/v1/tokens
```

Сохраните токен (начинается с `t1.`)

---

## ⚙️ ШАГ 2: Настройте .env (2 мин)

```bash
cd d:\M2\OncoMindFull\oncology_ai_assistant
copy .env.example .env
```

**Откройте `.env` и заполните:**

```env
YC_FOLDER_ID=b1c...                    # ← Ваш ID каталога из шага 1.1
YC_SERVICE_ACCOUNT_KEY=oncomind_sa_key.json
YC_IAM_TOKEN=t1....                    # ← Ваш токен из шага 1.3
AI_PORT=8000
DEBUG=True
```

---

## 🏃 ШАГ 3: Запустите AI сервер (3 мин)

```bash
# Перейдите в папку AI
cd d:\M2\OncoMindFull\oncology_ai_assistant

# Установите зависимости
pip install -r requirements.txt

# Запустите AI сервер (FastAPI)
uvicorn src.core.main:app --host 0.0.0.0 --port 8000 --reload
```

**Проверьте:**
- Откройте http://localhost:8000/health
- Должно вернуться: `{"status":"healthy"}`

---

## 🏃 ШАГ 4: Запустите Backend (2 мин)

**В НОВОМ ОКНЕ терминала:**

```bash
# Перейдите в папку backend
cd d:\M2\OncoMindFull\backend

# Установите зависимости (если ещё не установлены)
pip install -r requirements.txt

# Запустите Flask сервер
python app.py
```

**Проверьте:**
- Откройте http://localhost:5000/api/users
- Должен вернуться список тестовых пользователей

---

## 🏃 ШАГ 5: Проверьте сайт

**Откройте в браузере:**

1. http://localhost:5000 (или https://oncomind.ru для сервера)
2. Войдите как: `doctor@oncomind.ai` / `Doctor123!`
3. Проверьте разделы:
   - ✅ Кабинет врача
   - ✅ Клинические рекомендации (12 шт)
   - ✅ Поиск рекомендаций
   - ✅ Анализ лекарств (требует AI)

---

## 🧪 ТЕСТирование AI

### Тест 1: Проверка YandexGPT

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Пациенту назначен доксорубицин 60 мг/м2. Проверь совместимость.\",\"mode\":\"doctor\"}"
```

**Должен вернуться JSON с анализом.**

### Тест 2: Через Flask (полный пайплайн)

```bash
curl -X POST http://localhost:5000/api/analyze \
  -F "file=@test_document.pdf" \
  -F "mode=doctor" \
  -F "query=Проверь совместимость препаратов"
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
d:\M2\OncoMindFull\
├── backend/                    # Flask (порт 5000)
│   ├── app.py                  # ← Запускается первым
│   ├── data/users.json         # Тестовые пользователи
│   └── uploads/                # Загруженные файлы
│
├── oncology_ai_assistant/      # AI Pipeline (порт 8000)
│   ├── .env                    # ← НАСТРОИТЬ ЗДЕСЬ
│   ├── oncomind_sa_key.json    # ← ПОЛОЖИТЬ СЮДА
│   ├── requirements.txt
│   └── src/
│       ├── core/main.py        # FastAPI сервер
│       └── ...
│
├── frontend/                   # Веб-интерфейс
│   ├── index.html
│   ├── login.html
│   ├── doctor/
│   └── patient/
│
└── YANDEX_CLOUD_SETUP.md       # Подробная инструкция
```

---

## 💡 КОМАНДЫ ДЛЯ СЕРВЕРА

**Обновление на сервере:**

```bash
cd /var/www/oncomind
git pull origin main
systemctl restart oncomind
systemctl status oncomind
```

**Проверка логов:**

```bash
# Backend логи
journalctl -u oncomind -f

# Nginx логи
tail -f /var/log/nginx/oncomind.error.log
```

---

## ❓ ПРОБЛЕМЫ

### AI сервер не запускается

```bash
# Проверьте .env
cd oncology_ai_assistant
cat .env

# Проверьте ключ
ls -la oncomind_sa_key.json

# Пересоздайте токен
yc iam create-token --key-file oncomind_sa_key.json
```

### Flask не видит AI сервер

- Убедитесь, что AI сервер запущен на порту 8000
- Проверьте: `curl http://localhost:8000/health`
- В `.env` должно быть: `AI_PORT=8000`

### Ошибка IAM токена

- Токен действует 1 час
- Получите новый: `yc iam create-token --key-file oncomind_sa_key.json`
- Обновите в `.env`

---

## 📞 КОНТАКТЫ

- Telegram: @oncomind
- Email: team@oncomind.ai
- Документация: `YANDEX_CLOUD_SETUP.md`, `TODO.md`

---

## 🎯 ИТОГИ

| Что | Статус | Команда |
|-----|--------|---------|
| Frontend | ✅ 100% | `npm start` или Live Server |
| Backend | ✅ 100% | `python backend/app.py` |
| AI Pipeline | ✅ 100% | `uvicorn src.core.main:app` |
| Клинические рекомендации | ✅ 100% | https://oncomind.ru/doctor/dashboard.html |
| Тестовые пользователи | ✅ 100% | doctor@oncomind.ai / Doctor123! |

**Для полной работы AI нужно:**
1. ✅ Настроить Yandex Cloud (15 мин)
2. ✅ Создать .env (2 мин)
3. ✅ Запустить AI сервер (3 мин)
4. ✅ Запустить Backend (2 мин)

**Итого: ~22 минуты**
