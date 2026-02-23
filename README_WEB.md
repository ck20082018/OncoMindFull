# OncoMind — Веб-сайт и тестирование OCR

## 📋 Обзор

Этот проект включает:
1. **Веб-сайт** с регистрацией врачей и пациентов
2. **Drag-and-drop** загрузку файлов (.xlsx, .pdf, .txt, изображения)
3. **Backend** с проверкой диплома врача (8 цифр)
4. **Тест точности OCR** для различных форматов файлов

---

## 🚀 Быстрый старт

### 1. Регистрация пользователей

Откройте `index.html` в браузере и перейдите на страницу регистрации:

```
register.html
```

**Тестовый врач:**
- Email: `test.doctor@oncomind.ai`
- Пароль: `TestDoctor123!`
- Номер диплома: `12345678`

### 2. Запуск backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Backend запустится на `http://localhost:5000`

### 3. Тестирование OCR

```bash
# Демонстрационный тест
python ocr_accuracy_test.py --demo

# Тест с вашими данными
python ocr_accuracy_test.py --test-data path/to/files --ground-truth path/to/ground_truth.txt --output report.json
```

---

## 📁 Структура проекта

```
OncoMind-main/
├── index.html              # Главная страница
├── register.html           # Страница регистрации
├── register.js             # Логика регистрации и drag-and-drop
├── styles.css              # Стили
├── script.js               # Основной JS
├── backend/
│   ├── app.py              # Flask backend
│   ├── requirements.txt    # Зависимости
│   ├── data/
│   │   └── users.json      # База пользователей
│   └── uploads/            # Загруженные файлы
├── ocr_accuracy_test.py    # Тест точности OCR
└── README_WEB.md           # Этот файл
```

---

## 🔐 Регистрация

### Для врачей

Обязательные поля:
- ФИО
- Email
- Пароль (минимум 8 символов)
- **Номер диплома** (ровно 8 цифр)
- Специализация
- Место работы

### Для пациентов

Обязательные поля:
- ФИО
- Email
- Пароль

Опционально:
- Дата рождения
- Телефон

---

## 📤 Загрузка файлов

**Поддерживаемые форматы:**
- 📄 `.pdf` — документы
- 📊 `.xlsx` — Excel таблицы
- 📝 `.txt` — текстовые файлы
- 🖼️ `.jpg`, `.jpeg`, `.png` — изображения

**Ограничения:**
- Максимальный размер файла: 10 MB
- Несколько файлов можно загрузить одновременно

---

## 🧪 Тестирование OCR

### Требования

```bash
pip install easyocr opencv-python pillow numpy
pip install pandas openpyxl  # для .xlsx
pip install pymupdf  # для PDF
```

### Использование

#### Демонстрационный режим

```bash
python ocr_accuracy_test.py --demo
```

Создаст тестовые данные и проверит точность.

#### Тест с вашими файлами

1. Подготовьте директорию с файлами:
   ```
   test_data/
   ├── document1.pdf
   ├── image1.jpg
   ├── table1.xlsx
   └── notes.txt
   ```

2. Создайте файл с эталонным текстом:
   ```
   ground_truth.txt
   ```

3. Запустите тест:
   ```bash
   python ocr_accuracy_test.py \
       --test-data test_data/ \
       --ground-truth ground_truth.txt \
       --output report.json
   ```

### Параметры

| Параметр | Описание |
|----------|----------|
| `--test-data` | Директория с тестовыми файлами |
| `--ground-truth` | Файл с правильным текстом |
| `--output` | Сохранить отчёт в JSON |
| `--languages` | Языки OCR (по умолчанию: ru en) |
| `--use-gpu` | Использовать GPU |
| `--demo` | Демонстрационный режим |

### Метрики в отчёте

- **Схожесть текстов** — общий коэффициент схожести (0-100%)
- **Точность слов** — процент правильно распознанных слов
- **Точность символов** — процент правильно распознанных символов
- **Уверенность OCR** — средняя уверенность движка
- **Время обработки** — время на каждый файл

---

## 📡 API Endpoints

### POST `/api/register`

Регистрация нового пользователя.

**Пример запроса:**
```javascript
const formData = new FormData();
formData.append('role', 'doctor');
formData.append('email', 'doctor@example.com');
formData.append('password', 'Password123!');
formData.append('full_name', 'Иванов Иван');
formData.append('diploma_number', '12345678');
formData.append('files', fileInput.files[0]);

fetch('/api/register', { method: 'POST', body: formData });
```

### POST `/api/login`

Вход пользователя.

```json
{
  "email": "doctor@example.com",
  "password": "Password123!"
}
```

### POST `/api/validate-diploma`

Проверка номера диплома.

```json
{
  "diploma_number": "12345678"
}
```

### GET `/api/users`

Получение списка пользователей (админ).

---

## 🔧 Настройка

### Переменные окружения (опционально)

Создайте `.env` файл в директории `backend`:

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
MAX_CONTENT_LENGTH=10485760
```

---

## 📝 Примеры

### Пример отчёта OCR

```json
{
  "total_files": 5,
  "avg_similarity": 0.92,
  "avg_word_accuracy": 0.89,
  "avg_char_accuracy": 0.94,
  "avg_confidence": 0.91,
  "total_time": 12.45,
  "results": [...]
}
```

### Пример ответа API

**Успешная регистрация:**
```json
{
  "message": "Регистрация успешна",
  "user": {
    "id": "...",
    "email": "doctor@example.com",
    "full_name": "Иванов Иван",
    "role": "doctor"
  }
}
```

**Ошибка (диплом уже зарегистрирован):**
```json
{
  "error": "Диплом с таким номером уже зарегистрирован"
}
```

---

## ❓ Решение проблем

### Ошибка "EasyOCR не установлен"

```bash
pip install easyocr
```

### Ошибка "Pandas не установлен"

```bash
pip install pandas openpyxl
```

### Файлы не загружаются

1. Проверьте размер файла (макс. 10 MB)
2. Проверьте формат файла
3. Убедитесь, что директория `backend/uploads` существует

### Диплом не принимается

- Номер должен содержать **ровно 8 цифр**
- Без букв и специальных символов
- Пример: `12345678`

---

## 📞 Контакты

- Email: team@oncomind.ai
- Telegram: @oncomind

---

## 📄 Лицензия

© 2025 OncoMind. Все права защищены.
