#!/usr/bin/env python3
"""
Скрипт для обновления стилей во всех HTML файлах рекомендаций
"""

import re
from pathlib import Path

# Новые стили
new_styles = """<style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #1e2b3c;
            background: linear-gradient(135deg, #f0f5ff 0%, #ffffff 50%, #f5f9ff 100%);
            min-height: 100vh;
        }
        h1 {
            font-size: 36px;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #0a2472, #1e3a8a, #2563eb, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 800;
            line-height: 1.2;
        }
        h2 {
            font-size: 26px;
            margin-top: 35px;
            margin-bottom: 20px;
            color: #1e3a8a;
            font-weight: 700;
            border-bottom: 2px solid #2563eb;
            padding-bottom: 12px;
        }
        h3 {
            font-size: 20px;
            margin-top: 25px;
            margin-bottom: 12px;
            color: #2563eb;
            font-weight: 600;
        }
        p {
            margin-bottom: 15px;
            text-align: justify;
            color: #475569;
            font-size: 16px;
        }
        ul, ol {
            margin: 15px 0 15px 25px;
        }
        li {
            margin-bottom: 8px;
            color: #475569;
            font-size: 16px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(10, 36, 114, 0.08);
        }
        th, td {
            border: 1px solid #e2e8f0;
            padding: 14px;
            text-align: left;
        }
        th {
            background: linear-gradient(135deg, #0a2472, #1e3a8a);
            color: white;
            font-weight: 600;
        }
        tr:nth-child(even) {
            background: #f8fafc;
        }
        tr:hover {
            background: #f1f5f9;
        }
        .meta {
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.05), rgba(96, 165, 250, 0.1));
            padding: 25px;
            border-radius: 16px;
            margin-bottom: 30px;
            border-left: 4px solid #2563eb;
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.1);
        }
        .meta strong {
            color: #0a2472;
            font-weight: 600;
        }
        .meta p {
            margin-bottom: 10px;
        }
        .recommendation-box {
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.05), rgba(96, 165, 250, 0.08));
            border-left: 4px solid #2563eb;
            padding: 25px;
            margin: 25px 0;
            border-radius: 0 12px 12px 0;
            box-shadow: 0 2px 10px rgba(37, 99, 235, 0.05);
        }
        .recommendation-box strong {
            color: #1e3a8a;
        }
        .recommendation-box p {
            margin-bottom: 10px;
        }
        .warning {
            background: linear-gradient(135deg, #fef3c7, #fffbf0);
            border-left: 4px solid #f59e0b;
            padding: 20px;
            margin: 25px 0;
            border-radius: 0 12px 12px 0;
            box-shadow: 0 2px 10px rgba(245, 158, 11, 0.1);
        }
        .warning p {
            margin-bottom: 0;
            color: #92400e;
        }
        .back-link {
            display: inline-block;
            margin-bottom: 25px;
            color: #2563eb;
            text-decoration: none;
            font-weight: 500;
            padding: 10px 20px;
            background: rgba(37, 99, 235, 0.1);
            border-radius: 30px;
            transition: all 0.3s ease;
        }
        .back-link:hover {
            background: rgba(37, 99, 235, 0.2);
            transform: translateX(-5px);
        }
    </style>"""

# Путь к папке с рекомендациями
kb_path = Path(__file__).parent / 'knowledge_base'

# Обрабатываем все HTML файлы
for html_file in kb_path.glob('*.html'):
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем стили между <style> и </style>
    pattern = r'<style>.*?</style>'
    new_content = re.sub(pattern, new_styles, content, flags=re.DOTALL)
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Обновлён: {html_file.name}")

print("\n🎉 Все файлы обновлены!")
