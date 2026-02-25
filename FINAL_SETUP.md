# 🎯 OncoMind - Финальная настройка

## ✅ ЧТО УЖЕ ГОТОВО

| Компонент | Статус | Расположение |
|-----------|--------|--------------|
| **Frontend** | ✅ 100% | `frontend/` |
| **Flask Backend** | ✅ 100% | `backend/` |
| **AI Pipeline** | ✅ 95% | `oncology_ai_assistant/` |
| **VPS сервер** | ✅ Настроен | `https://oncomind.ru` |

---

## 🔴 ЧТО НУЖНО СДЕЛАТЬ (приоритеты)

### 1. Настроить Yandex Cloud (30 мин) ⚡ КРИТИЧНО

**Без этого AI не работает!**

```bash
# 1. Создать сервисный аккаунт
yc iam service-account create --name oncomind-ai
yc iam service-account add-role --role ai.languageModels.user --service-account-name oncomind-ai
yc iam key create --service-account-name oncomind-ai --output oncomind_sa_key.json

# 2. Получить ID каталога
yc resource-manager folder list
```

**Создать `.env`:**

```bash
# oncology_ai_assistant/.env
YC_FOLDER_ID=b1c...  # твой ID каталога
YC_SERVICE_ACCOUNT_KEY=oncomind_sa_key.json
```

**Проверка:**
```bash
cd oncology_ai_assistant
pip install -r requirements.txt
uvicorn src.core.main:app --host 0.0.0.0 --port 8000

# Проверить: curl http://localhost:8000/health
```

📖 **Подробно:** см. `YANDEX_CLOUD_SETUP.md`

---

### 2. Скачать клинические рекомендации (1 час) 📚

```bash
# Создать директорию
mkdir -p oncology_ai_assistant/knowledge_base_data/minzdrav

# Скачать PDF с https://cr.minzdrav.gov.ru
# Минимум 3-5 рекомендаций:
# - Рак молочной железы
# - Рак лёгкого  
# - Меланома
# - Колоректальный рак
# - Лимфома
```

**Структура:**
```
oncology_ai_assistant/
└── knowledge_base_data/
    └── minzdrav/
        ├── breast_cancer.pdf
        ├── lung_cancer.pdf
        └── melanoma.pdf
```

---

### 3. Интеграция Flask + AI Pipeline (1 час) 🔗

**Добавить endpoint во Flask:**

**Файл:** `backend/app.py` (добавить в конец, перед `if __name__ == '__main__':`)

```python
# =============================================================================
# AI PIPELINE INTEGRATION
# =============================================================================

import requests

AI_PIPELINE_URL = os.getenv('AI_PIPELINE_URL', 'http://127.0.0.1:8000')

@app.route('/api/analyze', methods=['POST'])
def analyze_document():
    """
    Анализ медицинского документа через AI Pipeline
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не загружен'}), 400
        
        file = request.files['file']
        mode = request.form.get('mode', 'doctor')
        query = request.form.get('query', '')
        
        if not file.filename:
            return jsonify({'error': 'Файл не выбран'}), 400
        
        # Отправка на AI Pipeline
        files = {'file': (file.filename, file, file.content_type)}
        data = {'mode': mode, 'query': query}
        
        logger.info(f"Отправка файла на AI анализ: {file.filename}, mode={mode}")
        
        response = requests.post(
            f"{AI_PIPELINE_URL}/api/analyze",
            files=files,
            data=data,
            timeout=300  # 5 минут на анализ
        )
        
        if response.ok:
            result = response.json()
            logger.info(f"AI анализ завершён: {result.get('success')}")
            return jsonify(result)
        else:
            logger.error(f"Ошибка AI API: {response.status_code} - {response.text}")
            return jsonify({
                'error': 'Ошибка AI анализа',
                'details': response.text
            }), 500
            
    except requests.exceptions.Timeout:
        logger.error("Таймаут AI анализа")
        return jsonify({'error': 'Превышено время анализа. Попробуйте файл меньшего размера.'}), 504
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка подключения к AI Pipeline: {e}")
        return jsonify({'error': 'AI сервис недоступен'}), 503
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/guidelines/search', methods=['POST'])
def search_guidelines():
    """
    Поиск по клиническим рекомендациям
    """
    try:
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 5)
        
        response = requests.post(
            f"{AI_PIPELINE_URL}/api/guidelines/search",
            json={'query': query, 'top_k': top_k}
        )
        
        if response.ok:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Ошибка поиска'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка поиска рекомендаций: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500
```

**Обновить `backend/requirements.txt`:**

```
flask==3.0.0
flask-cors==4.0.0
werkzeug==3.0.1
requests==2.31.0  # Добавить!
```

---

### 4. Обновить frontend для работы с AI (30 мин) 🎨

**Файл:** `frontend/doctor/analyze.html` (создать)

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Анализ — OncoMind</title>
    <link rel="icon" type="image/svg+xml" href="../favicon.svg">
    <link rel="stylesheet" href="../styles.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .analysis-container { max-width: 800px; margin: 40px auto; }
        .upload-area {
            border: 2px dashed var(--primary-blue);
            border-radius: var(--radius-lg);
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover {
            background: var(--bg-light);
            border-color: var(--primary-dark);
        }
        .result-box {
            background: white;
            border-radius: var(--radius-lg);
            padding: 30px;
            margin-top: 30px;
            box-shadow: var(--shadow-md);
        }
        .verdict-compliant { background: #d4edda; border-left: 4px solid #28a745; }
        .verdict-partial { background: #fff3cd; border-left: 4px solid #ffc107; }
        .verdict-noncompliant { background: #f8d7da; border-left: 4px solid #dc3545; }
        .loading { display: none; text-align: center; padding: 20px; }
        .loading.active { display: block; }
    </style>
</head>
<body>
    <header class="header">
        <div class="container header-content">
            <div class="logo">OncoMind</div>
            <nav class="nav-menu">
                <a href="../index.html" class="nav-link">Главная</a>
                <a href="dashboard.html" class="nav-link">Кабинет</a>
                <a href="#" id="logoutBtn" class="btn btn-nav">Выйти</a>
            </nav>
        </div>
    </header>

    <section>
        <div class="container analysis-container">
            <h1>AI Анализ документа</h1>
            
            <!-- Загрузка файла -->
            <div class="upload-area" id="uploadArea">
                <i class="fas fa-cloud-upload-alt" style="font-size: 48px; color: var(--primary-blue);"></i>
                <h3>Перетащите файл сюда</h3>
                <p>или кликните для выбора</p>
                <small>PDF, JPG, PNG, XLSX (макс. 10 MB)</small>
                <input type="file" id="fileInput" accept=".pdf,.jpg,.jpeg,.png,.xlsx" style="display: none;">
            </div>

            <!-- Выбор режима -->
            <div class="form-group" style="margin-top: 20px;">
                <label>Режим анализа:</label>
                <select id="analysisMode">
                    <option value="doctor">Для врача (детальный)</option>
                    <option value="patient">Для пациента (простой)</option>
                </select>
            </div>

            <!-- Дополнительный запрос -->
            <div class="form-group" style="margin-top: 20px;">
                <label>Дополнительный запрос (опционально):</label>
                <textarea id="customQuery" rows="3" placeholder="Например: проверить дозировку..."></textarea>
            </div>

            <!-- Кнопка анализа -->
            <button class="btn btn-primary btn-block" id="analyzeBtn" style="margin-top: 20px;">
                <i class="fas fa-brain"></i> Запустить анализ
            </button>

            <!-- Индикатор загрузки -->
            <div class="loading" id="loading">
                <i class="fas fa-spinner fa-spin" style="font-size: 32px; color: var(--primary-blue);"></i>
                <p>Анализ документа... Это может занять 1-2 минуты</p>
            </div>

            <!-- Результаты -->
            <div id="result" style="display: none;"></div>
        </div>
    </section>

    <script src="../config.js"></script>
    <script>
        const API_URL = API_CONFIG.BASE_URL;
        
        // Проверка авторизации
        const user = JSON.parse(localStorage.getItem('user'));
        if (!user || user.role !== 'doctor') {
            window.location.href = '../login.html';
        }

        // Загрузка файла
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        let selectedFile = null;

        uploadArea.addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedFile = e.target.files[0];
                uploadArea.innerHTML = `
                    <i class="fas fa-file-check" style="font-size: 48px; color: green;"></i>
                    <h3>Файл выбран: ${selectedFile.name}</h3>
                    <p>${(selectedFile.size / 1024).toFixed(1)} КБ</p>
                `;
            }
        });

        // Анализ
        document.getElementById('analyzeBtn').addEventListener('click', async () => {
            if (!selectedFile) {
                alert('Выберите файл для анализа');
                return;
            }

            const mode = document.getElementById('analysisMode').value;
            const query = document.getElementById('customQuery').value;

            // Показываем загрузку
            document.getElementById('loading').classList.add('active');
            document.getElementById('analyzeBtn').disabled = true;

            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('mode', mode);
            formData.append('query', query);

            try {
                const response = await fetch(`${API_URL}/api/analyze`, {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    displayResult(result);
                } else {
                    alert(`Ошибка: ${result.error || 'Неизвестная ошибка'}`);
                }
            } catch (error) {
                console.error('Ошибка:', error);
                alert('Ошибка подключения к серверу');
            } finally {
                document.getElementById('loading').classList.remove('active');
                document.getElementById('analyzeBtn').disabled = false;
            }
        });

        function displayResult(result) {
            const data = result.data;
            const verdict = data.verdict || 'частично_соответствует';
            
            let verdictClass = 'verdict-partial';
            let verdictText = '⚠️ Частично соответствует';
            
            if (verdict === 'соответствует') {
                verdictClass = 'verdict-compliant';
                verdictText = '✅ Соответствует рекомендациям';
            } else if (verdict === 'не_соответствует') {
                verdictClass = 'verdict-noncompliant';
                verdictText = '❌ Не соответствует рекомендациям';
            }

            document.getElementById('result').innerHTML = `
                <div class="result-box ${verdictClass}">
                    <h2>${verdictText}</h2>
                    <p><strong>Уверенность:</strong> ${(data.confidence_score || 0) * 100}%</p>
                </div>
                
                <div class="result-box">
                    <h3>Диагноз</h3>
                    <p>${data.diagnosis_analysis?.primary_diagnosis || 'Не определено'}</p>
                </div>
                
                <div class="result-box">
                    <h3>Лечение</h3>
                    <p>${data.treatment_analysis?.current_treatment || 'Не определено'}</p>
                    ${data.treatment_analysis?.discrepancies ? `
                        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 10px;">
                            <strong>⚠️ Расхождения:</strong>
                            <ul>${data.treatment_analysis.discrepancies.map(d => `<li>${d}</li>`).join('')}</ul>
                        </div>
                    ` : ''}
                </div>
                
                ${data.summary ? `
                    <div class="result-box" style="background: #e3f2fd;">
                        <h3>📝 Резюме</h3>
                        <p>${data.summary}</p>
                    </div>
                ` : ''}
            `;
            
            document.getElementById('result').style.display = 'block';
        }

        // Выход
        document.getElementById('logoutBtn').addEventListener('click', () => {
            localStorage.removeItem('user');
            window.location.href = '../index.html';
        });
    </script>
</body>
</html>
```

---

### 5. Обновление на сервере (5 мин) 🚀

```bash
# На своём компьютере
cd d:\M2\OncoMindFull
git add .
git commit -m "feat: AI integration with YandexGPT"
git push

# На сервере (SSH)
ssh root@155.212.182.149
cd /var/www/oncomind/OncoMindFull
git pull

# Перезапуск backend
supervisorctl restart oncomind-backend

# Если нужно, запуск AI Pipeline
cd /var/www/oncomind/OncoMindFull/oncology_ai_assistant
pip install -r requirements.txt
uvicorn src.core.main:app --host 127.0.0.1 --port 8000 &

# Проверка
supervisorctl status
curl https://oncomind.ru/api/analyze --form "file=@test.pdf" --form "mode=doctor"
```

---

## ✅ ФИНАЛЬНЫЙ ЧЕКЛИСТ

```
□ Yandex Cloud настроен (сервисный аккаунт, ключ, folder_id)
□ .env файл создан в oncology_ai_assistant/
□ AI Pipeline запущен (порт 8000)
□ Клинические рекомендации скачаны (минимум 3 PDF)
□ Flask интегрирован с AI Pipeline
□ endpoint /api/analyze добавлен
□ frontend/doctor/analyze.html создан
□ Обновление на сервере выполнено
□ Тестовый анализ прошёл успешно
```

---

## 🎯 МАРШРУТНАЯ КАРТА

```
1. Yandex Cloud        → 30 мин
2. Клинические         → 1 час
   рекомендации
   
3. Интеграция          → 1 час
   Flask + AI
   
4. Frontend            → 30 мин
   (analyze.html)
   
5. Тестирование        → 1 час
   
6. Деплой на           → 15 мин
   сервер
   ────────────────────────────────
   ИТОГО: ~4.5 часов
```

---

## 📞 Поддержка

- Документация: `README.md`, `FUNCTIONAL_STATUS.md`
- Yandex Cloud: `YANDEX_CLOUD_SETUP.md`
- Локальный запуск: `START_LOCAL.md`

**Готово! 🎉**
