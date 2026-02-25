# 🚀 OncoMind - Быстрый старт (Локальная разработка)

## 📋 Требования

- Python 3.10+
- VS Code с расширением **Live Server**

---

## 🔧 Шаг 1: Запуск Backend

### Windows (PowerShell или CMD)

```bash
cd d:\M2\OncoMindFull\backend

# Создаём виртуальное окружение (если нет)
python -m venv venv

# Активируем
venv\Scripts\activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем сервер
python app.py
```

**Backend запустится на:** `http://127.0.0.1:5000`

---

## 🔧 Шаг 2: Запуск Frontend (Live Server)

### В VS Code:

1. Открой папку `d:\M2\OncoMindFull\frontend`
2. Установи расширение **Live Server** (если нет)
   - Extensions → Поиск "Live Server" → Install
3. Правый клик на `index.html` → **Open with Live Server**
4. Frontend откроется на `http://127.0.0.1:5500`

---

## ✅ Проверка работы

### 1. Открой браузер

```
http://127.0.0.1:5500
```

### 2. Проверь API

Открой консоль браузера (F12) и выполни:

```javascript
fetch('http://127.0.0.1:5000/api/users')
  .then(r => r.json())
  .then(console.log)
```

Должен увидеть список тестовых пользователей!

---

## 👥 Тестовые пользователи

### Врачи:

| Email | Пароль | Диплом |
|-------|--------|--------|
| `doctor@oncomind.ai` | `Doctor123!` | `12345678` |
| `elena.doctor@oncomind.ai` | `Elena2026!` | `87654321` |

### Пациенты:

| Email | Пароль |
|-------|--------|
| `maria.patient@example.com` | `Maria2026!` |
| `ivan.patient@example.com` | `Ivan2026!` |
| `anna.test@example.com` | `Anna2026!` |

---

## 🧪 Тест регистрации

1. Открой `http://127.0.0.1:5500/register.html`
2. Выбери роль (Врач/Пациент)
3. Заполни форму
4. Для врача: номер диплома (8 цифр)
5. Нажми "Зарегистрироваться"

**Успешная регистрация:** сообщение "Регистрация успешна!"

---

## 🧪 Тест входа

1. Открой `http://127.0.0.1:5500/login.html`
2. Введи email и пароль тестового пользователя
3. Нажми "Войти"

**Успешный вход:** перенаправление в личный кабинет

---

## 📁 Структура проекта

```
OncoMindFull/
├── backend/
│   ├── app.py              # Flask сервер
│   ├── requirements.txt    # Зависимости
│   ├── data/
│   │   └── users.json      # База пользователей
│   └── uploads/            # Загруженные файлы
├── frontend/
│   ├── config.js           # API конфигурация ⚙️
│   ├── index.html          # Главная
│   ├── login.html          # Вход
│   ├── register.html       # Регистрация
│   ├── styles.css          # Стили
│   ├── script.js           # Общий JS
│   ├── login.js            # Логика входа
│   └── register.js         # Логика регистрации
└── README.md
```

---

## 🔄 Обновление на сервере

Когда всё работает локально:

```bash
# 1. Коммит в Git
cd d:\M2\OncoMindFull
git add .
git commit -m "fix: регистрация работает"
git push

# 2. На сервере (SSH)
ssh root@155.212.182.149
cd /var/www/oncomind/OncoMindFull
git pull

# Если менял Python:
supervisorctl restart oncomind-backend
```

---

## 🛠️ Решение проблем

### Ошибка CORS

**Проблема:** Frontend не может подключиться к Backend

**Решение:**
- Проверь что backend запущен (`http://127.0.0.1:5000`)
- Проверь что `config.js` подключен в HTML
- Проверь CORS настройки в `backend/app.py`

### Ошибка "API_CONFIG не определён"

**Решение:**
- Убедись что `config.js` подключен **перед** `login.js` и `register.js`
- Проверь порядок скриптов в HTML

### Backend не запускается

```bash
# Проверь Python версию
python --version  # Должна быть 3.10+

# Переустанови зависимости
pip install -r requirements.txt --force-reinstall
```

### Файлы не загружаются

- Проверь что директория `backend/uploads` существует
- Проверь права доступа (на сервере)

---

## 📞 Контакты

Если что-то не работает — проверь логи:

**Backend логи:**
- Локально: в консоли где запущен `python app.py`
- На сервере: `tail -f /var/log/oncomind/backend.log`

**Frontend ошибки:**
- Консоль браузера (F12)

---

**Удачи в разработке!** 🎉
