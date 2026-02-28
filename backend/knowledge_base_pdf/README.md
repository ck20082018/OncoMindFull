# Клинические рекомендации в формате PDF

Эта папка предназначена для хранения PDF файлов клинических рекомендаций Минздрава РФ.

## Правила именования файлов

**Формат:** ГОД-заболевание.pdf

**Примеры:**
- 2026-breast-cancer.pdf - Рак молочной железы
- 2026-lung-cancer.pdf - Рак лёгкого
- 2026-melanoma.pdf - Меланома кожи
- 2026-colorectal-cancer.pdf - Колоректальный рак
- 2026-prostate-cancer.pdf - Рак предстательной железы
- 2026-ovarian-cancer.pdf - Рак яичников
- 2026-stomach-cancer.pdf - Рак желудка
- 2026-cervical-cancer.pdf - Рак шейки матки
- 2026-kidney-cancer.pdf - Рак почки
- 2026-bladder-cancer.pdf - Рак мочевого пузыря
- 2026-lymphoma.pdf - Лимфомы
- 2026-glioma.pdf - Глиомы головного мозга

## Автоматическое переименование

Используйте скрипт для автоматического переименования файлов:

```bash
cd /var/www/oncomind/backend
python rename_guidelines.py
```

Скрипт анализирует содержание PDF и переименовывает файлы по формату.

## Как добавить рекомендации

### Способ 1: Скачать с cr.minzdrav.gov.ru

```bash
cd /var/www/oncomind/backend/knowledge_base_pdf
wget -O 2026-breast-cancer.pdf "https://cr.minzdrav.gov.ru/recomend/633/download"
```

### Способ 2: Через SFTP

1. Подключитесь к серверу: 155.212.182.149
2. Перейдите в: /var/www/oncomind/backend/knowledge_base_pdf/
3. Загрузите PDF файлы

### Способ 3: Через Git

1. Скачайте PDF на компьютер
2. Положите в: d:\M2\OncoMindFull\backend\knowledge_base_pdf\
3. Сделайте: git add -A && git commit -m "Добавлены PDF" && git push
4. На сервере: git pull origin main

## Проверка

```bash
# 1. Проверьте папку
ls -la /var/www/oncomind/backend/knowledge_base_pdf/

# 2. Проверьте API
curl http://localhost:5000/api/guidelines-pdf | python3 -m json.tool

# 3. Откройте в браузере
https://oncomind.ru/doctor/guidelines-pdf.html
```
