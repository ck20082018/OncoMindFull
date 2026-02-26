# 🩺 AI-помощник для проверки лечения онкопациентов

Система для анализа медицинских документов и проверки соответствия лечения клиническим рекомендациям Минздрава РФ.

## 📋 О проекте

Проект создан для кейс-чемпионата от Сеченовского университета по онкологии.

**Назначение:**
- ✅ Приём медицинских данных (PDF, изображения, Excel через OCR)
- ✅ Анонимизация персональных данных ДО отправки в AI
- ✅ Сверка лечения с клиническими рекомендациями Минздрава РФ
- ✅ Два вывода: для врача (детальный) и пациента (простым языком)
- ✅ Интеграция с Yandex Cloud AI (YandexGPT Pro)

## ⚠️ Важное предупреждение

**Система НЕ назначает лечение самостоятельно** — она только проверяет соответствие назначений актуальным клиническим рекомендациям.

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        ИНТЕРФЕЙСЫ                                │
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │   Врач (Streamlit)  │    │  Пациент (Streamlit)│             │
│  └──────────┬──────────┘    └──────────┬──────────┘             │
└─────────────┼───────────────────────────┼───────────────────────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    PIPELINE                              │    │
│  │  ┌─────────┐  ┌─────────────┐  ┌──────────────┐         │    │
│  │  │   OCR   │→ │Анонимизация │→ │  RAG Поиск   │         │    │
│  │  └─────────┘  └─────────────┘  └──────────────┘         │    │
│  │                                          │                │    │
│  │                                          ▼                │    │
│  │                                   ┌─────────────┐         │    │
│  │                                   │  YandexGPT  │         │    │
│  │                                   └─────────────┘         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    БАЗА ЗНАНИЙ                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Минздрав РФ    │  │     NCCN        │  │     ESMO        │  │
│  │   (локально)    │  │   (интеграция)  │  │   (интеграция)  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Быстрый старт

### 1. Требования

- Python 3.10+
- Аккаунт в Yandex Cloud с доступом к YandexGPT
- 8+ GB RAM (для локальных эмбеддингов)

### 2. Установка

```bash
# Клонирование репозитория
cd oncology_ai_assistant

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Установка зависимостей
pip install -r requirements.txt
```

### 3. Настройка

#### Yandex Cloud

1. Создайте сервисный аккаунт с ролью `ai.languageModels.user`:
```bash
yc iam service-account create --name oncology-assistant
yc iam service-account add-role \
  --role ai.languageModels.user \
  --service-account-name oncology-assistant
yc iam key create \
  --service-account-name oncology-assistant \
  --output credentials/authorized_key.json
```

2. Получите ID каталога:
```bash
yc resource-manager folder list
```

3. Скопируйте `.env.example` в `.env` и заполните:
```bash
cp .env.example .env
```

```env
YC_FOLDER_ID=b1cxxxxxxxxxxxxxxxxxxxxxxxxxx
YC_SERVICE_ACCOUNT_KEY=credentials/authorized_key.json
```

#### Клинические рекомендации

Поместите PDF файлы клинических рекомендаций в `knowledge_base_data/minzdrav/`:
- Рак молочной железы
- Рак лёгкого
- Меланома
- и другие...

### 4. Запуск

#### Backend (FastAPI)

```bash
# Запуск API сервера
uvicorn src.core.main:app --host 0.0.0.0 --port 8000 --reload
```

API доступно по адресу: http://localhost:8000
Документация Swagger: http://localhost:8000/docs

#### Интерфейс врача

```bash
streamlit run src/interfaces/doctor_interface.py --server.port 8501
```

#### Интерфейс пациента

```bash
streamlit run src/interfaces/patient_interface.py --server.port 8502
```

## 📁 Структура проекта

```
oncology_ai_assistant/
├── config/
│   ├── config.yaml              # Основная конфигурация
│   └── yandex_cloud_config.yaml # Настройки Yandex Cloud
├── src/
│   ├── core/
│   │   ├── main.py              # FastAPI приложение
│   │   └── pipeline.py          # Основной пайплайн
│   ├── ocr/
│   │   ├── ocr_engine.py        # OCR движок (EasyOCR)
│   │   └── pdf_parser.py        # Парсер PDF/Excel
│   ├── anonymization/
│   │   ├── anonymizer.py        # Анонимизация PII
│   │   └── patterns.py          # Regex паттерны
│   ├── llm/
│   │   ├── yandex_client.py     # Клиент YandexGPT
│   │   ├── prompt_templates.py  # Шаблоны промптов
│   │   └── json_validator.py    # Валидация JSON
│   ├── knowledge_base/
│   │   ├── guideline_manager.py # Управление рекомендациями
│   │   ├── guideline_updater.py # Обновление рекомендаций
│   │   └── rag_search.py        # RAG поиск
│   ├── interfaces/
│   │   ├── doctor_interface.py  # Streamlit для врача
│   │   └── patient_interface.py # Streamlit для пациента
│   └── utils/
│       ├── logger.py            # Логирование
│       └── validators.py        # Валидаторы
├── knowledge_base_data/
│   ├── minzdrav/                # Клинические рекомендации
│   └── index/                   # RAG индекс
├── test_cases/
│   └── synthetic_patient_001.json
├── temp/                        # Временные файлы
├── logs/                        # Логи
├── .env.example
├── requirements.txt
└── README.md
```

## 🔒 Безопасность

### Анонимизация

Перед отправкой в YandexGPT все персональные данные удаляются:

| Тип данных | Паттерн | Замена |
|------------|---------|--------|
| ФИО | Иванов Иван Иванович | [ФИО] |
| Паспорт | 4500 123456 | [ПАСПОРТ] |
| Полис ОМС | 1234567890123456 | [ПОЛИС] |
| СНИЛС | 123-456-789 12 | [СНИЛС] |
| Телефон | +7 (999) 123-45-67 | [ТЕЛЕФОН] |
| Email | test@example.com | [EMAIL] |

### Логи

- Логи не содержат персональных данных
- Автоматическая санитизация чувствительной информации
- Ротация логов каждые 100 MB

### Временные файлы

- Автоматическое удаление после обработки
- TTL: 1 час

## 📊 API Endpoints

### Анализ документов

```bash
POST /api/analyze
Content-Type: multipart/form-data

file: <медицинский документ>
mode: doctor|patient
query: <дополнительный запрос>
```

### Поиск по рекомендациям

```bash
POST /api/guidelines/search

{
  "query": "лечение рака молочной железы",
  "top_k": 5
}
```

### Проверка обновлений

```bash
POST /api/guidelines/update/check
```

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/

# Проверка типа
mypy src/

# Линтинг
flake8 src/
```

## 📝 Примеры использования

### Python SDK

```python
from src.core.pipeline import OncologyPipeline
from src.llm.yandex_client import YandexGPTConfig

# Конфигурация
config = YandexGPTConfig(
    folder_id="b1c...",
    service_account_key_path="credentials/key.json"
)

# Создание пайплайна
pipeline = OncologyPipeline(
    yandex_config=config,
    data_dir="knowledge_base_data/minzdrav"
)

# Анализ для врача
result = pipeline.process_doctor("patient_scan.pdf")
print(result.data)

# Анализ для пациента
result = pipeline.process_patient("patient_scan.pdf")
print(result.data)
```

### cURL

```bash
# Анализ документа
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@patient_document.pdf" \
  -F "mode=doctor" \
  -F "query=проверить дозировку"
```

## 🔧 Конфигурация

### config.yaml

```yaml
app:
  name: "Oncology AI Assistant"
  version: "1.0.0"
  debug: false

llm:
  model_name: "yandexgpt-pro"
  temperature: 0.1  # Низкая для точности
  max_tokens: 4000
  json_mode: true

anonymization:
  strict_mode: true
  use_placeholders: true

rag:
  embedding_model: "sentence-transformers/ruBert-large"
  top_k: 5
  similarity_threshold: 0.7
```

## 🛠️ Разработка

### Добавление новой клинической рекомендации

1. Скачайте PDF с cr.minzdrav.gov.ru
2. Поместите в `knowledge_base_data/minzdrav/`
3. Переиндексируйте:
```bash
POST /api/guidelines/update/download
```

### Добавление нового паттерна анонимизации

```python
# src/anonymization/patterns.py
PATTERNS['new_pattern'] = PatternConfig(
    name='new_pattern',
    pattern=re.compile(r'ваш_regex'),
    placeholder='[НОВЫЙ_ПЛЕЙСХОЛДЕР]',
    description='Описание'
)
```

## 📄 Лицензия

Проект создан для образовательных целей в рамках кейс-чемпионата.

## 👥 Команда

- Разработчик: [Голобородько Вячеслав]
- Университет: МГТУ СТАНКИН 15.03.05
- Дата: Февраль 2026

## 📞 Контакты

- Email: [ck20082018@gmail.com]
- Telegram: [@ck20082018]

## ⚠️ Отказ от ответственности

Система является вспомогательным инструментом и не заменяет консультацию квалифицированного врача-онколога. Все решения о лечении должны приниматься врачом на основе клинической картины и индивидуальных особенностей пациента.
