"""
=============================================================================
PATIENT_INTERFACE.PY - Упрощённый интерфейс для пациента
=============================================================================
Интерфейс для пациентов с:
- Объяснениями простым языком без медицинских терминов
- Понятными инструкциями о лечении
- Списком вопросов для врача
- Поддерживающими сообщениями
=============================================================================
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path


# Настройка страницы
st.set_page_config(
    page_title="Ваш помощник по лечению",
    page_icon="💙",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Кастомные стили
st.markdown("""
<style>
    .main-header {
        font-size: 32px;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 20px;
    }
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 15px 0;
    }
    .step-card {
        background-color: #f8f9fa;
        border-left: 5px solid #667eea;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .question-card {
        background-color: #e8f4fd;
        border: 1px solid #b8daff;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .support-message {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        font-style: italic;
        margin: 20px 0;
    }
    .medication-box {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .side-effect-low { background-color: #d4edda; }
    .side-effect-medium { background-color: #fff3cd; }
    .side-effect-high { background-color: #f8d7da; }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Заголовок
# -----------------------------------------------------------------------------
st.markdown('<p class="main-header">💙 Ваш помощник по лечению</p>', unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; color: #666; max-width: 600px; margin: 0 auto;">
    Этот помощник поможет вам понять ваше лечение простым языком.
    Загрузите ваши медицинские документы, и мы объясним всё понятно.
</div>
""", unsafe_allow_html=True)

st.divider()


# -----------------------------------------------------------------------------
# Основная область
# -----------------------------------------------------------------------------

# Вкладки
tab1, tab2, tab3 = st.tabs(["📤 Загрузка документов", "❓ Вопросы врачу", "📚 Полезная информация"])

with tab1:
    st.header("Загрузите ваши документы")
    
    st.markdown("""
    **Что можно загрузить:**
    - 📄 Выписки из истории болезни
    - 📄 Результаты анализов
    - 📄 Заключения врачей
    - 📄 Назначения лечения
    """)
    
    # Загрузка файла
    uploaded_file = st.file_uploader(
        "Выберите файл",
        type=['pdf', 'jpg', 'jpeg', 'png'],
        help="Мы автоматически извлечём текст и объясним его простым языком"
    )
    
    # Кнопка объяснения
    col1, col2 = st.columns([3, 1])
    with col1:
        explain_button = st.button(
            "💡 Объяснить простым языком",
            type="primary",
            use_container_width=True
        )
    
    if uploaded_file:
        st.info(f"📄 Файл: **{uploaded_file.name}**")
    
    # Результаты объяснения
    if explain_button and uploaded_file:
        with st.spinner("⏳ Анализируем документы..."):
            # Прогресс
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            steps = [
                (20, "Читаем документ..."),
                (40, "Убираем личную информацию..."),
                (60, "Ищем информацию о лечении..."),
                (80, "Готовим простое объяснение..."),
                (100, "Готово!")
            ]
            
            for progress, status in steps:
                progress_bar.progress(progress)
                status_text.text(status)
            
            st.success("✅ Готово! Вот простое объяснение:")
            
            # Пример результата (заглушка)
            example_explanation = {
                "diagnosis_explained": """
                У вас обнаружено заболевание молочной железы. 
                Это значит, что некоторые клетки начали расти неправильно. 
                Хорошая новость: болезнь обнаружена на ранней стадии, 
                когда лечение наиболее эффективно.
                """,
                "stage_explained": """
                Ваша стадия (IIB) означает, что заболевание локальное 
                и не распространилось далеко. Это хорошая новость — 
                такое состояние успешно лечится.
                """,
                "treatment_plan": {
                    "what": "Химиотерапия перед операцией",
                    "why": "Лекарства помогут уменьшить размер заболевания перед операцией. 
                          Это сделает операцию более простой и эффективной.",
                    "how": "Вы будете приходить в больницу раз в 2-3 недели. 
                          Лекарства вводят через капельницу. 
                          После капельницы можно идти домой."
                },
                "medications": [
                    {
                        "name": "Доксорубицин (Красная химиотерапия)",
                        "purpose": "Основное лекарство против больных клеток",
                        "how_given": "Через капельницу, 1 раз в 2 недели"
                    },
                    {
                        "name": "Циклофосфамид",
                        "purpose": "Помогает основному лекарству работать лучше",
                        "how_given": "Через капельницу вместе с первым лекарством"
                    },
                    {
                        "name": "Паклитаксел",
                        "purpose": "Дополнительное лекарство для лучшего результата",
                        "how_given": "Через капельницу, 1 раз в неделю после первых препаратов"
                    }
                ],
                "side_effects": [
                    {
                        "effect": "Выпадение волос",
                        "frequency": "часто",
                        "what_to_do": "Волосы вырастут после лечения. 
                                      Можно купить парик заранее или коротко постричься."
                    },
                    {
                        "effect": "Тошнота",
                        "frequency": "иногда",
                        "what_to_do": "Врач даст таблетки от тошноты. 
                                      Ешьте маленькими порциями, избегайте острой пищи."
                    },
                    {
                        "effect": "Усталость",
                        "frequency": "часто",
                        "what_to_do": "Больше отдыхайте. 
                                      Лёгкая прогулка может помочь почувствовать себя лучше."
                    }
                ],
                "next_steps": [
                    "Пройти обследование сердца перед лечением",
                    "Установить порт для удобного введения лекарств",
                    "Начать первый курс химиотерапии",
                    "Посещать врача после каждого курса"
                ],
                "questions_for_doctor": [
                    "Сколько всего будет курсов лечения?",
                    "Когда я смогу вернуться к работе?",
                    "Какие симптомы требуют срочного звонка врачу?",
                    "Можно ли принимать витамины во время лечения?",
                    "Что делать если я заболею простудой во время лечения?"
                ],
                "support_message": """
                Помните: вы не одни в этой борьбе. 
                Миллионы людей успешно прошли через подобное лечение 
                и вернулись к полноценной жизни. 
                Каждый день лечения — это шаг к выздоровлению. 
                Вы сильнее, чем думаете! 💪
                """
            }
            
            # Отображение результатов
            st.divider()
            
            # Объяснение диагноза
            st.subheader("📋 Что у вас")
            st.markdown(example_explanation["diagnosis_explained"])
            
            # Стадия
            with st.expander("📊 Что означает ваша стадия", expanded=False):
                st.markdown(example_explanation["stage_explained"])
            
            # План лечения
            st.subheader("💊 Ваш план лечения")
            
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                st.info(f"**Что:** {example_explanation['treatment_plan']['what']}")
            with col_t2:
                st.info(f"**Зачем:** {example_explanation['treatment_plan']['why']}")
            with col_t3:
                st.info(f"**Как:** {example_explanation['treatment_plan']['how']}")
            
            # Лекарства
            st.subheader("💊 Лекарства")
            for med in example_explanation["medications"]:
                st.markdown(f"""
                <div class="medication-box">
                    <strong>💊 {med['name']}</strong><br><br>
                    <b>Зачем:</b> {med['purpose']}<br>
                    <b>Как вводят:</b> {med['how_given']}
                </div>
                """, unsafe_allow_html=True)
            
            # Побочные эффекты
            st.subheader("⚠️ Возможные эффекты лечения")
            st.markdown("""
            <div style="background-color: #e7f3ff; padding: 15px; border-radius: 10px; margin: 10px 0;">
                ⚠️ <strong>Важно:</strong> Не все эти эффекты обязательно у вас будут. 
                Современные лекарства помогают их уменьшить или избежать.
            </div>
            """, unsafe_allow_html=True)
            
            for se in example_explanation["side_effects"]:
                freq_map = {"часто": "🟡", "иногда": "🟢", "редко": "🔵"}
                st.markdown(f"""
                <div class="step-card">
                    <strong>{freq_map.get(se['frequency'], '⚪')} {se['effect']}</strong><br><br>
                    <b>Что делать:</b> {se['what_to_do']}
                </div>
                """, unsafe_allow_html=True)
            
            # Следующие шаги
            st.subheader("📅 Следующие шаги")
            for i, step in enumerate(example_explanation["next_steps"], 1):
                st.markdown(f"""
                <div class="step-card">
                    <strong>Шаг {i}:</strong> {step}
                </div>
                """, unsafe_allow_html=True)
            
            # Вопросы врачу
            st.subheader("❓ Вопросы которые стоит задать врачу")
            st.markdown("""
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 10px; margin: 10px 0;">
                💡 <strong>Совет:</strong> Запишите эти вопросы или покажите этот список врачу.
            </div>
            """, unsafe_allow_html=True)
            
            for q in example_explanation["questions_for_doctor"]:
                st.markdown(f"""
                <div class="question-card">
                    ❓ {q}
                </div>
                """, unsafe_allow_html=True)
            
            # Поддерживающее сообщение
            st.divider()
            st.markdown(f"""
            <div class="support-message">
                {example_explanation['support_message']}
            </div>
            """, unsafe_allow_html=True)
            
            # Кнопки
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                st.download_button(
                    "📥 Сохранить объяснение",
                    data=json.dumps(example_explanation, ensure_ascii=False, indent=2),
                    file_name=f"my_explanation_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
            with col_btn2:
                st.button("📋 Распечатать вопросы врачу")
            with col_btn3:
                st.button("🔄 Объяснить другой документ")

with tab2:
    st.header("❓ Частые вопросы")
    
    faq = {
        "Как подготовиться к химиотерапии?": """
        **Перед лечением:**
        - Хорошо выспитесь накануне
        - Поешьте лёгкую пищу за 2-3 часа до процедуры
        - Возьмите с собой воду, книгу или наушники
        - Оденьтесь удобно, с лёгким доступом к рукам
        
        **Что взять с собой:**
        - Паспорт и документы
        - Бутылку воды
        - Лёгкий перекус
        - Книгу или планшет
        """,
        
        "Можно ли работать во время лечения?": """
        Это зависит от вашего самочувствия и типа работы:
        
        ✅ **Обычно можно:**
        - Работа из дома
        - Неполный рабочий день
        - Работа без физических нагрузок
        
        ❌ **Лучше взять перерыв:**
        - Физически тяжёлая работа
        - Работа с инфекциями
        - Если вы чувствуете сильную усталость
        
        Обсудите с врачом — он даст рекомендации.
        """,
        
        "Что делать если стало плохо?": """
        **Срочно звоните врачу если:**
        - Температура выше 38°C
        - Сильная тошнота или рвота
        - Одышка или боль в груди
        - Необычное кровотечение
        
        **Телефон экстренной связи:**
        Ваш врач должен дать вам номер для срочных вопросов.
        """,
        
        "Можно ли делать прививки?": """
        **Во время лечения:**
        - Живые вакцины — ❌ Нельзя
        - Инактивированные вакцины — ⚠️ Только после консультации
        
        **После лечения:**
        - Обычно можно через 3-6 месяцев
        
        Обязательно обсудите с врачом!
        """,
        
        "Как питаться во время лечения?": """
        **Рекомендации:**
        - Ешьте маленькими порциями 5-6 раз в день
        - Пейте достаточно воды (1.5-2 литра)
        - Включите белок (мясо, рыба, яйца, бобовые)
        - Избегайте сырых продуктов (суши, мягкие сыры)
        
        **Если тошнит:**
        - Сухари, крекеры, имбирный чай
        - Избегайте жирного и острого
        """
    }
    
    selected_question = st.selectbox(
        "Выберите вопрос",
        list(faq.keys())
    )
    
    if selected_question:
        with st.expander(selected_question, expanded=True):
            st.markdown(faq[selected_question])
    
    st.divider()
    st.info("💡 Не нашли ответ на свой вопрос? Запишите его и спросите у врача!")

with tab3:
    st.header("📚 Полезная информация")
    
    st.markdown("""
    ### 📖 Словарь терминов
    
    | Термин | Простое объяснение |
    |--------|-------------------|
    | **Биопсия** | Взятие маленького кусочка ткани для анализа |
    | **Стадия** | Насколько распространилось заболевание |
    | **Химиотерапия** | Лечение специальными лекарствами против больных клеток |
    | **Лучевая терапия** | Лечение рентгеновскими лучами |
    | **Метастазы** | Клетки которые переместились в другие органы |
    | **Рецидив** | Возвращение болезни после лечения |
    | **Ремиссия** | Период когда болезнь не активна |
    
    ---
    
    ### 📞 Полезные контакты
    
    **Экстренная помощь:** 103 или 112
    
    **Горячая линия онкопомощи:** 8-800-XXX-XX-XX (бесплатно)
    
    **Психологическая поддержка:** 8-800-XXX-XX-XX
    
    ---
    
    ### 🔗 Полезные ресурсы
    
    - [Фонд профилактики рака](https://fondrp.ru)
    - [Проект «Ясное утро»](https://yasnoe-utro.ru) — помощь онкопациентам
    - [Фонд «Живи сейчас»](https://live-now.ru) — поддержка пациентов
    """)


# -----------------------------------------------------------------------------
# Футер
# -----------------------------------------------------------------------------
st.divider()
st.markdown("""
<div style="text-align: center; color: gray; font-size: 12px;">
    💙 Помните: эта информация не заменяет консультацию врача.<br>
    Всегда обсуждайте лечение с вашим доктором.
</div>
""", unsafe_allow_html=True)
