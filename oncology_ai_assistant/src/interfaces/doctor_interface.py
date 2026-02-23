"""
=============================================================================
DOCTOR_INTERFACE.PY - Интерфейс Streamlit для врача-онколога
=============================================================================
Профессиональный интерфейс для врачей с:
- Детальным анализом соответствия лечения рекомендациям
- Ссылками на конкретные пункты клинических рекомендаций
- Оценкой рисков и confidence score
- Возможностью поиска по базе знаний
=============================================================================
"""

import streamlit as st
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Настройка страницы
st.set_page_config(
    page_title="AI-помощник врача-онколога",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомные стили
st.markdown("""
<style>
    .verdict-box {
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .verdict-compliant {
        background-color: #d4edda;
        border: 2px solid #28a745;
    }
    .verdict-partial {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
    }
    .verdict-noncompliant {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
    }
    .confidence-score {
        font-size: 24px;
        font-weight: bold;
    }
    .reference-card {
        background-color: #f8f9fa;
        border-left: 4px solid #007bff;
        padding: 15px;
        margin: 10px 0;
    }
    .risk-card {
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .risk-low { background-color: #d4edda; }
    .risk-medium { background-color: #fff3cd; }
    .risk-high { background-color: #f8d7da; }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Заголовок
# -----------------------------------------------------------------------------
st.title("🩺 AI-помощник врача-онколога")
st.markdown("""
**Система проверки соответствия лечения клиническим рекомендациям**

Загрузите медицинские документы пациента для анализа соответствия назначенного
лечения актуальным клиническим рекомендациям Минздрава РФ.
""")


# -----------------------------------------------------------------------------
# Боковая панель
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Выбор режима
    analysis_mode = st.selectbox(
        "Тип анализа",
        ["Стандартный", "Расширенный", "Быстрый"],
        help="Расширенный анализ включает больше источников"
    )
    
    # Источник рекомендаций
    guideline_source = st.multiselect(
        "Источники рекомендаций",
        ["Минздрав РФ", "NCCN", "ESMO"],
        default=["Минздрав РФ"]
    )
    
    st.divider()
    
    # Статус системы
    st.subheader("📊 Статус системы")
    
    # Проверка подключения (заглушка)
    api_available = st.session_state.get('api_available', True)
    kb_loaded = st.session_state.get('kb_loaded', False)
    
    st.metric("API доступно", "✅" if api_available else "❌")
    st.metric("База знаний", "✅ Загружена" if kb_loaded else "⚠️ Не загружена")
    
    st.divider()
    
    # Информация
    with st.expander("ℹ️ О системе"):
        st.markdown("""
        **Версия:** 1.0.0
        
        **Назначение:**
        - Проверка соответствия лечения рекомендациям
        - Выявление потенциальных рисков
        - Предоставление обоснования
        
        **Важно:** Система не назначает лечение,
        а только проверяет соответствие стандартам.
        """)


# -----------------------------------------------------------------------------
# Основная область
# -----------------------------------------------------------------------------

# Вкладки
tab1, tab2, tab3 = st.tabs(["📤 Загрузка документов", "🔍 Поиск рекомендаций", "📋 История"])

with tab1:
    st.header("Загрузка медицинских документов")
    
    # Область загрузки
    uploaded_file = st.file_uploader(
        "Выберите файл для анализа",
        type=['pdf', 'jpg', 'jpeg', 'png', 'xls', 'xlsx'],
        help="Поддерживаются: PDF, изображения, Excel"
    )
    
    # Дополнительный запрос
    custom_query = st.text_area(
        "Дополнительный запрос (опционально)",
        placeholder="Например: проверить дозировку паклитаксела",
        height=100
    )
    
    # Кнопка анализа
    col1, col2 = st.columns([3, 1])
    with col1:
        analyze_button = st.button(
            "🔬 Запустить анализ",
            type="primary",
            use_container_width=True
        )
    
    if uploaded_file:
        st.info(f"📄 Файл: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} КБ)")
    
    # Результаты анализа
    if analyze_button and uploaded_file:
        with st.spinner("⏳ Обработка документов..."):
            # Прогресс бар
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Симуляция процесса (в реальности здесь вызов API)
            steps = [
                (10, "Извлечение текста из документа..."),
                (30, "Анонимизация персональных данных..."),
                (50, "Поиск релевантных рекомендаций..."),
                (70, "Анализ соответствия лечения..."),
                (90, "Формирование отчёта..."),
                (100, "Готово!")
            ]
            
            for progress, status in steps:
                progress_bar.progress(progress)
                status_text.text(status)
            
            # Здесь должен быть вызов API к бэкенду
            # Для демонстрации показываем пример результата
            
            st.success("✅ Анализ завершён!")
            
            # Пример результата (заглушка для демонстрации)
            example_result = {
                "verdict": "частично_соответствует",
                "confidence_score": 0.78,
                "diagnosis_analysis": {
                    "primary_diagnosis": "Рак молочной железы T2N1M0, IIB стадия",
                    "histology": "Инвазивная дольковая карцинома, G2",
                    "molecular_markers": "ER+, PR+, HER2-, Ki67=25%"
                },
                "treatment_analysis": {
                    "current_treatment": "AC-T схема (доксорубицин + циклофосфамид, затем паклитаксел)",
                    "guideline_recommendation": "Рекомендована неоадъювантная/адъювантная химиотерапия",
                    "discrepancies": ["Дозировка паклитаксела ниже рекомендованной на 15%"],
                    "dosage_check": "требует_проверки"
                },
                "guideline_references": [
                    {
                        "source": "Минздрав РФ",
                        "document": "Рак молочной железы. КР 2023",
                        "section": "Лекарственная терапия",
                        "point": "п. 4.2.1",
                        "quote": "Стандартная схема AC-T: доксорубицин 60 мг/м² + циклофосфамид 600 мг/м²"
                    }
                ],
                "risks": [
                    {
                        "type": "побочный_эффект",
                        "description": "Риск кардиотоксичности при применении антрациклинов",
                        "severity": "средний",
                        "recommendation": "Рекомендуется мониторинг ФВ ЛЖ каждые 3 месяца"
                    }
                ],
                "summary": "Лечение в целом соответствует рекомендациям. Требуется коррекция дозировки паклитаксела."
            }
            
            # Отображение результатов
            st.divider()
            st.subheader("📊 Результаты анализа")
            
            # Вердикт
            verdict = example_result["verdict"]
            if verdict == "соответствует":
                verdict_class = "verdict-compliant"
                verdict_text = "✅ Соответствует рекомендациям"
            elif verdict == "частично_соответствует":
                verdict_class = "verdict-partial"
                verdict_text = "⚠️ Частично соответствует"
            else:
                verdict_class = "verdict-noncompliant"
                verdict_text = "❌ Не соответствует рекомендациям"
            
            st.markdown(f"""
            <div class="verdict-box {verdict_class}">
                <h3>{verdict_text}</h3>
                <p class="confidence-score">Уверенность: {example_result['confidence_score']*100:.0f}%</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Колонки для деталей
            col_diag, col_treat = st.columns(2)
            
            with col_diag:
                with st.expander("📋 Анализ диагноза", expanded=True):
                    diag = example_result["diagnosis_analysis"]
                    st.markdown(f"""
                    - **Основной диагноз:** {diag['primary_diagnosis']}
                    - **Гистология:** {diag['histology']}
                    - **Молекулярные маркеры:** {diag['molecular_markers']}
                    """)
            
            with col_treat:
                with st.expander("💊 Анализ лечения", expanded=True):
                    treat = example_result["treatment_analysis"]
                    st.markdown(f"""
                    - **Текущее лечение:** {treat['current_treatment']}
                    - **Рекомендация:** {treat['guideline_recommendation']}
                    - **Проверка дозировок:** {treat['dosage_check']}
                    """)
                    
                    if treat['discrepancies']:
                        st.warning("⚠️ Расхождения:")
                        for disc in treat['discrepancies']:
                            st.write(f"- {disc}")
            
            # Ссылки на рекомендации
            st.subheader("📚 Клинические рекомендации")
            for ref in example_result["guideline_references"]:
                st.markdown(f"""
                <div class="reference-card">
                    <strong>{ref['source']}:</strong> {ref['document']}<br>
                    <em>Раздел:</em> {ref['section']}, <em>{ref['point']}</em><br>
                    <blockquote>{ref['quote']}</blockquote>
                </div>
                """, unsafe_allow_html=True)
            
            # Риски
            st.subheader("⚠️ Риски")
            for risk in example_result["risks"]:
                risk_class = f"risk-{risk['severity']}"
                severity_map = {"низкий": "🟢", "средний": "🟡", "высокий": "🔴"}
                st.markdown(f"""
                <div class="risk-card {risk_class}">
                    <strong>{severity_map[risk['severity']]} {risk['type']}</strong><br>
                    {risk['description']}<br>
                    <em>Рекомендация:</em> {risk['recommendation']}
                </div>
                """, unsafe_allow_html=True)
            
            # Резюме
            st.info(f"📝 **Резюме:** {example_result['summary']}")
            
            # Кнопки действий
            st.divider()
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            with col_exp1:
                st.download_button(
                    "📥 Скачать PDF отчёт",
                    data=json.dumps(example_result, ensure_ascii=False, indent=2),
                    file_name=f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            with col_exp2:
                st.button("📋 Копировать резюме")
            with col_exp3:
                st.button("🔄 Новый анализ")

with tab2:
    st.header("🔍 Поиск по клиническим рекомендациям")
    
    search_query = st.text_input(
        "Поисковый запрос",
        placeholder="Например: лечение рака лёгкого 3 стадии"
    )
    
    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        search_button = st.button("🔍 Найти", type="secondary")
    
    if search_query and search_button:
        with st.spinner("Поиск..."):
            # Заглушка результатов поиска
            st.markdown("""
            ### Найдено рекомендаций: 3
            
            **1. Рак лёгкого. Клинические рекомендации Минздрава РФ, 2023**
            - Стадирование: TNM классификация
            - Лечение III стадии: комбинированная терапия
            - [Подробнее](#)
            
            **2. Молекулярно-генетические маркеры при раке лёгкого**
            - EGFR, ALK, ROS1 тестирование
            - Таргетная терапия
            - [Подробнее](#)
            
            **3. Лучевая терапия при раке лёгкого**
            - Показания и противопоказания
            - Режимы фракционирования
            - [Подробнее](#)
            """)

with tab3:
    st.header("📋 История анализов")
    
    # Заглушка истории
    st.markdown("""
    | Дата | Файл | Вердикт | Статус |
    |------|------|---------|--------|
    | 20.02.2026 14:30 | patient_001.pdf | Частично соответствует | ✅ |
    | 20.02.2026 12:15 | biopsy_result.jpg | Соответствует | ✅ |
    | 19.02.2026 16:45 | treatment_plan.xlsx | Не соответствует | ⚠️ |
    """)
    
    st.button("🗑️ Очистить историю")


# -----------------------------------------------------------------------------
# Футер
# -----------------------------------------------------------------------------
st.divider()
st.markdown("""
<div style="text-align: center; color: gray; font-size: 12px;">
    Oncology AI Assistant v1.0.0 | Система не заменяет консультацию специалиста
</div>
""", unsafe_allow_html=True)
