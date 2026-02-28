#!/usr/bin/env python3
"""
Скрипт для автоматического переименования PDF файлов клинических рекомендаций
на основе их содержания и метаданных.

Использование:
    python rename_guidelines.py

Скрипт:
1. Сканирует папку knowledge_base_pdf
2. Читает метаданные и первые страницы каждого PDF
3. Предлагает новое имя файла на основе содержания
4. Переименовывает файлы
"""

import os
import re
from pathlib import Path
from datetime import datetime

# Путь к папке с PDF
PDF_DIR = Path(__file__).parent / 'knowledge_base_pdf'

# Словарь соответствия заболеваний и ключевых слов
DISEASE_KEYWORDS = {
    'breast-cancer': ['рак молочной железы', 'рмж', 'груди', 'c50'],
    'lung-cancer': ['рак лёгкого', 'рак легкого', 'бронхов', 'трахеи', 'c34'],
    'melanoma': ['меланома', 'кожи', 'c43', 'c44'],
    'colorectal-cancer': ['колоректальный', 'рака ободочной', 'рака прямой кишки', 'c18', 'c19', 'c20'],
    'prostate-cancer': ['рак предстательной железы', 'простаты', 'c61'],
    'ovarian-cancer': ['рак яичников', 'яичника', 'c56'],
    'stomach-cancer': ['рак желудка', 'c16'],
    'cervical-cancer': ['рак шейки матки', 'матки', 'c53'],
    'kidney-cancer': ['рак почки', 'почек', 'c64'],
    'bladder-cancer': ['рак мочевого пузыря', 'c67'],
    'lymphoma': ['лимфома', 'лимфомы', 'c81', 'c82', 'c83', 'c84', 'c85'],
    'glioma': ['глиома', 'опухоль головного мозга', 'c71'],
    'liver-cancer': ['рак печени', 'c22'],
    'pancreatic-cancer': ['рак поджелудочной железы', 'c25'],
    'thyroid-cancer': ['рак щитовидной железы', 'c73'],
}

# Словарь для русских названий
RUSSIAN_NAMES = {
    'breast-cancer': 'Рак молочной железы',
    'lung-cancer': 'Рак лёгкого',
    'melanoma': 'Меланома кожи',
    'colorectal-cancer': 'Колоректальный рак',
    'prostate-cancer': 'Рак предстательной железы',
    'ovarian-cancer': 'Рак яичников',
    'stomach-cancer': 'Рак желудка',
    'cervical-cancer': 'Рак шейки матки',
    'kidney-cancer': 'Рак почки',
    'bladder-cancer': 'Рак мочевого пузыря',
    'lymphoma': 'Лимфомы',
    'glioma': 'Глиомы головного мозга',
    'liver-cancer': 'Рак печени',
    'pancreatic-cancer': 'Рак поджелудочной железы',
    'thyroid-cancer': 'Рак щитовидной железы',
}


def extract_text_from_pdf(pdf_path):
    """
    Извлечь текст из первых страниц PDF.
    Требует установленного pymupdf (fitz).
    """
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        text = ""
        
        # Читаем первые 3 страницы
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            text += page.get_text()
        
        doc.close()
        return text.lower()
    
    except ImportError:
        print("⚠️  PyMuPDF не установлен. Установите: pip install pymupdf")
        return ""
    except Exception as e:
        print(f"⚠️  Ошибка чтения {pdf_path}: {e}")
        return ""


def get_metadata(pdf_path):
    """Получить метаданные PDF файла."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        doc.close()
        return metadata
    except:
        return {}


def detect_disease_type(text, filename):
    """
    Определить тип заболевания по тексту и имени файла.
    Возвращает кортеж (disease_key, year).
    """
    text_lower = text.lower() if text else ""
    filename_lower = filename.lower()
    
    # Пытаемся найти год в тексте или имени файла
    year_match = re.search(r'(20\d{2})', filename_lower)
    year = year_match.group(1) if year_match else datetime.now().year
    
    # Ищем ключевые слова заболеваний
    for disease_key, keywords in DISEASE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower or keyword in filename_lower:
                return disease_key, year
    
    return None, year


def generate_new_filename(old_name, disease_key, year):
    """Сгенерировать новое имя файла."""
    russian_name = RUSSIAN_NAMES.get(disease_key, disease_key.replace('-', ' ').title())
    return f"{year}-{disease_key}.pdf", russian_name


def main():
    """Основная функция."""
    print("=" * 70)
    print("📚 Переименование PDF файлов клинических рекомендаций")
    print("=" * 70)
    
    if not PDF_DIR.exists():
        print(f"❌ Папка не найдена: {PDF_DIR}")
        print("Создайте папку и добавьте в неё PDF файлы.")
        return
    
    pdf_files = list(PDF_DIR.glob('*.pdf'))
    
    if not pdf_files:
        print(f"❌ В папке {PDF_DIR} нет PDF файлов")
        return
    
    print(f"\n📁 Найдено файлов: {len(pdf_files)}")
    print(f"📂 Папка: {PDF_DIR}\n")
    
    # Проверяем, установлен ли pymupdf
    try:
        import fitz
        has_pymupdf = True
    except ImportError:
        has_pymupdf = False
        print("⚠️  PyMuPDF не установлен. Будет использовано только имя файла.\n")
    
    renamed_count = 0
    
    for pdf_path in pdf_files:
        print(f"\n{'─' * 70}")
        print(f"📄 Файл: {pdf_path.name}")
        
        # Получаем текст из PDF
        text = ""
        if has_pymupdf:
            text = extract_text_from_pdf(pdf_path)
            if text:
                print(f"📝 Найдено текста: {len(text)} символов")
        
        # Определяем тип заболевания
        disease_key, year = detect_disease_type(text, pdf_path.name)
        
        if disease_key:
            russian_name = RUSSIAN_NAMES.get(disease_key, disease_key)
            new_filename = f"{year}-{disease_key}.pdf"
            
            print(f"🏷️  Заболевание: {russian_name}")
            print(f"📅 Год: {year}")
            print(f"💡 Новое имя: {new_filename}")
            
            # Переименовываем
            if pdf_path.name != new_filename:
                new_path = PDF_DIR / new_filename
                
                # Проверяем, нет ли уже файла с таким именем
                if new_path.exists():
                    print(f"⚠️  Файл {new_filename} уже существует! Пропускаем.")
                else:
                    try:
                        pdf_path.rename(new_path)
                        print(f"✅ Переименовано: {pdf_path.name} → {new_filename}")
                        renamed_count += 1
                    except Exception as e:
                        print(f"❌ Ошибка переименования: {e}")
            else:
                print(f"✓ Имя файла уже корректно")
        else:
            print(f"⚠️  Не удалось определить тип заболевания")
            print(f"   Оставьте имя файла вручную или добавьте ключевые слова в текст")
    
    print(f"\n{'═' * 70}")
    print(f"✅ Готово! Переименовано файлов: {renamed_count} из {len(pdf_files)}")
    print(f"{'═' * 70}\n")
    
    # Выводим итоговый список
    print("📋 Итоговый список файлов:")
    for pdf in sorted(PDF_DIR.glob('*.pdf')):
        print(f"   • {pdf.name}")
    
    print("\n💡 Совет: Проверьте файлы и при необходимости переименуйте вручную.")


if __name__ == '__main__':
    main()
