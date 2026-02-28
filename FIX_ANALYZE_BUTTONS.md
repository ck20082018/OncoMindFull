# 🔧 OncoMind - Исправление кнопок в разделе "Анализ лечения"

## ✅ Что было исправлено

### Проблема
Кнопки в разделе "Анализ лечения" (`analyze.html`) не работали из-за:
1. Функции были определены внутри `DOMContentLoaded`, но вызывались через `onclick` из HTML
2. Отсутствовало подключение `script.js` с утилитами
3. `API_CONFIG` указывал на production URL вместо локального сервера

### Исправления

1. **analyze.html** - Переписана структура:
   - ✅ Функции вынесены в глобальную область
   - ✅ Добавлена нормальная инициализация через `addEventListener`
   - ✅ Добавлено подключение `script.js`
   - ✅ Добавлена обработка ошибок
   - ✅ Добавлены сообщения об успехе/ошибке
   - ✅ Улучшена валидация файлов

2. **config.js** - Исправлено определение окружения:
   - ✅ Для localhost используется `http://127.0.0.1:5000`
   - ✅ Для продакшена используется `https://oncomind.ru`
   - ✅ Добавлено логирование для отладки

---

## 🚀 Как запустить

### 1. Запустите Backend сервер

```bash
cd d:\M2\OncoMindFull\backend

# Активация виртуального окружения
venv\Scripts\activate

# Запуск сервера
python app.py
```

**Ожидаемый вывод:**
```
Запуск сервера на 127.0.0.1:5000
```

### 2. Откройте frontend

**Вариант A: Через Live Server (рекомендуется)**
- Откройте `d:\M2\OncoMindFull\frontend` в VS Code
- Нажмите правой кнопкой на `index.html`
- Выберите "Open with Live Server"

**Вариант B: Прямое открытие**
- Откройте в браузере: `d:\M2\OncoMindFull\frontend\index.html`

### 3. Войдите в систему

**Тестовый врач:**
- Email: `doctor@oncomind.ai`
- Пароль: `Doctor123!`

### 4. Перейдите в "Анализ лечения"

1. Войдите как врач
2. Нажмите на карточку "Проверка тактики лечения" (или любую другую)
3. Должна открыться страница `analyze.html`

---

## ✅ Проверка работы

### Чек-лист

- [ ] Кнопки переключения режимов работают (тактика/совместимость/аналоги)
- [ ] Drag-and-drop зона реагирует на наведение
- [ ] Клик по зоне загрузки открывает выбор файлов
- [ ] Файлы добавляются в список
- [ ] Кнопка удаления файла работает
- [ ] Кнопка "Запустить анализ" активна
- [ ] При нажатии на "Запустить анализ" без файлов показывается ошибка
- [ ] При загрузке файла и нажатии "Запустить анализ" показывается loading overlay

---

## 🐛 Отладка

### Если кнопки всё ещё не работают

1. **Откройте консоль разработчика** (F12)
2. **Проверьте вкладки:**
   - **Console** - должны быть логи:
     ```
     [API_CONFIG] Текущий URL: http://127.0.0.1:5000 (Localhost: true )
     [Analyze] DOM загружен
     [Analyze] Пользователь авторизован: doctor@oncomind.ai
     ```
   - **Network** - при нажатии на "Запустить анализ" должен быть POST запрос на `/api/analyze`

3. **Проверьте что backend запущен:**
   ```bash
   curl http://127.0.0.1:5000/api/users
   ```
   
   **Ожидаемый ответ:**
   ```json
   {"users": [...]}
   ```

### Частые ошибки

| Ошибка | Решение |
|--------|---------|
| `API_CONFIG is not defined` | Проверьте что `config.js` подключён перед другими скриптами |
| `Failed to fetch` | Backend не запущен или неправильный URL |
| `404 Not Found` | Неправильный путь к API endpoint |
| `CORS error` | Проверьте настройки CORS в `backend/app.py` |

---

## 📁 Структура файлов

```
frontend/
├── config.js              ← Исправлено!
├── script.js              ← Утилиты (escapeHtml и т.д.)
├── doctor/
│   ├── dashboard.html     ← Ссылки на analyze.html
│   └── analyze.html       ← Исправлено!
└── ...
```

---

## 🎯 Что проверяет новый код

### 1. Авторизация
```javascript
const user = JSON.parse(localStorage.getItem('user') || 'null');
if (!user || user.role !== 'doctor') {
    window.location.href = '../login.html';
    return;
}
```

### 2. Валидация файлов
```javascript
const allowedTypes = ['application/pdf', ...];
const allowedExtensions = ['.pdf', '.xlsx', ...];

if (allowedTypes.includes(file.type) || allowedExtensions.includes(extension)) {
    uploadedFiles.push(file);
} else {
    showError(`Файл "${file.name}" имеет неподдерживаемый формат`);
}
```

### 3. Валидация перед отправкой
```javascript
if (currentMode === 'analogs') {
    const substance = document.getElementById('activeSubstance').value.trim();
    if (!substance) {
        showError('Введите активное вещество');
        return;
    }
} else if (uploadedFiles.length === 0) {
    showError('Загрузите файлы для анализа');
    return;
}
```

---

## 📞 Если проблема осталась

1. Сохраните скриншот консоли (F12 → Console)
2. Проверьте версию браузера
3. Попробуйте другой браузер (Chrome, Firefox, Edge)
4. Очистите кэш браузера (Ctrl+Shift+Delete)

---

**Исправлено:** Февраль 2026  
**Версия:** 2.0 (с исправлениями безопасности)
