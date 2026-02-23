"""
=============================================================================
OCR_ACCURACY_TEST.PY - Тест точности OCR
=============================================================================
Скрипт для проверки точности распознавания различных форматов файлов:
- Изображения: .jpg, .png, .jpeg
- Документы: .pdf, .txt
- Таблицы: .xlsx

Использование:
    python ocr_accuracy_test.py --test-data path/to/test_data --ground-truth path/to/ground_truth.txt

Или для быстрого теста:
    python ocr_accuracy_test.py --demo
=============================================================================
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher
import tempfile

# Добавляем путь к модулю OCR
sys.path.insert(0, str(Path(__file__).parent / 'oncology_ai_assistant' / 'src'))

from ocr.ocr_engine import OCREngine, MedicalDocumentOCR
from ocr.pdf_parser import PDFParser

# Опциональные импорты
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Результат теста для одного файла."""
    file_name: str
    file_type: str
    ocr_text: str
    ground_truth: str
    similarity: float  # 0.0 - 1.0
    word_accuracy: float
    char_accuracy: float
    processing_time: float
    confidence: float
    errors: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestReport:
    """Общий отчёт по тестированию."""
    total_files: int
    avg_similarity: float
    avg_word_accuracy: float
    avg_char_accuracy: float
    avg_confidence: float
    total_time: float
    results: List[TestResult]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OCRAccuracyTester:
    """Тестирование точности OCR."""

    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    SUPPORTED_DOC_FORMATS = {'.pdf', '.txt', '.xlsx'}

    def __init__(
        self,
        languages: List[str] = None,
        use_gpu: bool = False,
        confidence_threshold: float = 0.5
    ):
        """
        Инициализация тестировщика.

        Args:
            languages: Языки для OCR.
            use_gpu: Использовать GPU.
            confidence_threshold: Порог уверенности.
        """
        self.languages = languages or ['ru', 'en']
        self.use_gpu = use_gpu
        self.confidence_threshold = confidence_threshold

        logger.info("Инициализация OCREngine...")
        try:
            self.ocr_engine = OCREngine(
                languages=self.languages,
                use_gpu=self.use_gpu,
                confidence_threshold=self.confidence_threshold
            )
            self.doc_ocr = MedicalDocumentOCR(ocr_engine=self.ocr_engine)
            logger.info("OCR движок успешно инициализирован")
        except ImportError as e:
            logger.error(f"Ошибка инициализации OCR: {e}")
            self.ocr_engine = None
            self.doc_ocr = None

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Вычисление схожести двух текстов (коэффициент Жаккара).

        Args:
            text1: Первый текст.
            text2: Второй текст.

        Returns:
            Коэффициент схожести (0.0 - 1.0).
        """
        # Нормализация
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()

        if not t1 or not t2:
            return 0.0

        # SequenceMatcher для более точной оценки
        return SequenceMatcher(None, t1, t2).ratio()

    def calculate_word_accuracy(self, ocr_text: str, ground_truth: str) -> float:
        """
        Точность на уровне слов.

        Args:
            ocr_text: Распознанный текст.
            ground_truth: Эталонный текст.

        Returns:
            Процент правильно распознанных слов.
        """
        ocr_words = set(ocr_text.lower().split())
        truth_words = set(ground_truth.lower().split())

        if not truth_words:
            return 0.0

        correct_words = ocr_words.intersection(truth_words)
        return len(correct_words) / len(truth_words)

    def calculate_char_accuracy(self, ocr_text: str, ground_truth: str) -> float:
        """
        Точность на уровне символов.

        Args:
            ocr_text: Распознанный текст.
            ground_truth: Эталонный текст.

        Returns:
            Процент правильно распознанных символов.
        """
        if not ground_truth:
            return 0.0

        ocr_chars = list(ocr_text.lower())
        truth_chars = list(ground_truth.lower())

        matches = sum(1 for i in range(min(len(ocr_chars), len(truth_chars)))
                     if ocr_chars[i] == truth_chars[i])

        return matches / len(truth_chars)

    def extract_text_from_xlsx(self, file_path: Path) -> str:
        """
        Извлечение текста из Excel файла.

        Args:
            file_path: Путь к .xlsx файлу.

        Returns:
            Текст из ячеек.
        """
        if not PANDAS_AVAILABLE:
            logger.warning("Pandas не установлен. Пропуск .xlsx файла.")
            return ""

        try:
            df = pd.read_excel(file_path)
            # Конвертируем все ячейки в текст
            text_parts = []
            for col in df.columns:
                for value in df[col].astype(str):
                    if value and value != 'nan':
                        text_parts.append(str(value))
            return '\n'.join(text_parts)
        except Exception as e:
            logger.error(f"Ошибка чтения XLSX: {e}")
            return ""

    def extract_text_from_pdf(self, file_path: Path) -> Tuple[str, str]:
        """
        Извлечение текста из PDF (OCR + прямой текст если доступен).

        Args:
            file_path: Путь к PDF файлу.

        Returns:
            Кортеж (OCR текст, прямой текст если есть).
        """
        direct_text = ""

        # Пробуем извлечь прямой текст если PyMuPDF доступен
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                text_pages = []
                for page in doc:
                    text_pages.append(page.get_text())
                direct_text = '\n'.join(text_pages)
                doc.close()
                logger.info(f"Извлечён прямой текст из PDF ({len(direct_text)} символов)")
            except Exception as e:
                logger.warning(f"Не удалось извлечь прямой текст из PDF: {e}")

        # Используем OCR для распознавания
        logger.info("Запуск OCR для PDF...")
        results = self.doc_ocr.process_pdf(file_path)
        ocr_text = self.doc_ocr.get_full_text(results)

        return ocr_text, direct_text

    def test_file(
        self,
        file_path: Path,
        ground_truth: str
    ) -> TestResult:
        """
        Тестирование одного файла.

        Args:
            file_path: Путь к файлу.
            ground_truth: Эталонный текст.

        Returns:
            TestResult.
        """
        import time
        start_time = time.time()

        file_type = file_path.suffix.lower()
        ocr_text = ""
        confidence = 0.0
        errors = []

        try:
            if file_type in self.SUPPORTED_IMAGE_FORMATS:
                # Изображение
                logger.info(f"Обработка изображения: {file_path.name}")
                result = self.ocr_engine.recognize(file_path, preprocess=True)
                ocr_text = result.text
                confidence = result.confidence

            elif file_type == '.pdf':
                # PDF документ
                logger.info(f"Обработка PDF: {file_path.name}")
                ocr_text, direct_text = self.extract_text_from_pdf(file_path)
                # Если есть прямой текст, используем его для сравнения уверенности
                if direct_text:
                    confidence = self.calculate_similarity(ocr_text, direct_text)
                else:
                    confidence = 0.5  # Средняя уверенность если нет прямого текста

            elif file_type == '.txt':
                # Текстовый файл (сравниваем напрямую)
                logger.info(f"Чтение текстового файла: {file_path.name}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    ocr_text = f.read()
                confidence = 1.0  # Для .txt точность 100%

            elif file_type == '.xlsx':
                # Excel файл
                logger.info(f"Чтение XLSX: {file_path.name}")
                ocr_text = self.extract_text_from_xlsx(file_path)
                confidence = 1.0  # Для .xlsx точность 100%

            else:
                errors.append(f"Неподдерживаемый формат: {file_type}")

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Ошибка обработки файла {file_path.name}: {e}")

        processing_time = time.time() - start_time

        # Вычисляем метрики
        similarity = self.calculate_similarity(ocr_text, ground_truth)
        word_accuracy = self.calculate_word_accuracy(ocr_text, ground_truth)
        char_accuracy = self.calculate_char_accuracy(ocr_text, ground_truth)

        return TestResult(
            file_name=file_path.name,
            file_type=file_type,
            ocr_text=ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text,
            ground_truth=ground_truth[:200] + "..." if len(ground_truth) > 200 else ground_truth,
            similarity=similarity,
            word_accuracy=word_accuracy,
            char_accuracy=char_accuracy,
            processing_time=processing_time,
            confidence=confidence,
            errors=errors,
            timestamp=datetime.now().isoformat()
        )

    def run_tests(
        self,
        test_data_dir: Path,
        ground_truth_file: Path
    ) -> TestReport:
        """
        Запуск серии тестов.

        Args:
            test_data_dir: Директория с тестовыми файлами.
            ground_truth_file: Файл с эталонным текстом.

        Returns:
            TestReport.
        """
        if not self.ocr_engine:
            raise RuntimeError("OCR движок не инициализирован")

        # Читаем эталонный текст
        logger.info(f"Чтение эталонного текста из {ground_truth_file}")
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            ground_truth = f.read()

        # Находим все поддерживаемые файлы
        test_files = []
        for ext in list(self.SUPPORTED_IMAGE_FORMATS) + list(self.SUPPORTED_DOC_FORMATS):
            test_files.extend(test_data_dir.glob(f'*{ext}'))
            test_files.extend(test_data_dir.glob(f'*{ext.upper()}'))

        if not test_files:
            raise ValueError(f"Тестовые файлы не найдены в {test_data_dir}")

        logger.info(f"Найдено {len(test_files)} файлов для тестирования")

        # Запускаем тесты
        results: List[TestResult] = []
        for file_path in test_files:
            logger.info(f"\n{'='*60}")
            logger.info(f"Тест: {file_path.name}")
            result = self.test_file(file_path, ground_truth)
            results.append(result)
            logger.info(
                f"Результат: схожесть={result.similarity:.2%}, "
                f"слова={result.word_accuracy:.2%}, символы={result.char_accuracy:.2%}"
            )

        # Создаём отчёт
        total_time = sum(r.processing_time for r in results)

        report = TestReport(
            total_files=len(results),
            avg_similarity=sum(r.similarity for r in results) / len(results),
            avg_word_accuracy=sum(r.word_accuracy for r in results) / len(results),
            avg_char_accuracy=sum(r.char_accuracy for r in results) / len(results),
            avg_confidence=sum(r.confidence for r in results) / len(results),
            total_time=total_time,
            results=results,
            timestamp=datetime.now().isoformat()
        )

        return report

    def run_demo(self) -> TestReport:
        """
        Запуск демонстрационного теста с созданием тестовых данных.

        Returns:
            TestReport.
        """
        logger.info("Запуск демонстрационного теста...")

        # Создаём временную директорию
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Эталонный текст (медицинский документ)
            ground_truth = """
            ЗАКЛЮЧЕНИЕ ПАТОЛОГОАНАТОМИЧЕСКОГО ИССЛЕДОВАНИЯ

            Пациент: Иванов Иван Петрович
            Дата рождения: 15.03.1965
            История болезни: №12345/2024

            ДИАГНОЗ:
            Рак молочной железы T2N1M0, II стадия
            Люминальный B тип, HER2-негативный

            РЕКОМЕНДАЦИИ:
            1. Адъювантная химиотерапия по схеме AC-T
            2. Лучевая терапия на область молочной железы
            3. Антигормональная терапия (тамоксифен 20 мг/сут)
            4. Наблюдение онколога каждые 3 месяца

            Врач-патолог: Петрова А.С.
            Дата: 20.02.2024
            """.strip()

            # Сохраняем эталонный текст
            ground_truth_file = tmpdir / 'ground_truth.txt'
            with open(ground_truth_file, 'w', encoding='utf-8') as f:
                f.write(ground_truth)

            # Создаём тестовый текстовый файл
            txt_file = tmpdir / 'test_document.txt'
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(ground_truth)

            logger.info(f"Создан тестовый файл: {txt_file}")

            # Запускаем тест
            return self.run_tests(tmpdir, ground_truth_file)


def print_report(report: TestReport):
    """Вывод отчёта в консоль."""
    print("\n" + "="*70)
    print("ОТЧЁТ ПО ТЕСТИРОВАНИЮ ТОЧНОСТИ OCR")
    print("="*70)
    print(f"Всего файлов: {report.total_files}")
    print(f"Общее время: {report.total_time:.2f} сек")
    print()
    print("СРЕДНИЕ ПОКАЗАТЕЛИ:")
    print(f"  • Схожесть текстов: {report.avg_similarity:.2%}")
    print(f"  • Точность слов: {report.avg_word_accuracy:.2%}")
    print(f"  • Точность символов: {report.avg_char_accuracy:.2%}")
    print(f"  • Средняя уверенность: {report.avg_confidence:.2%}")
    print()
    print("ДЕТАЛИ ПО ФАЙЛАМ:")
    print("-"*70)

    for result in report.results:
        print(f"\nФайл: {result.file_name} ({result.file_type})")
        print(f"  Схожесть: {result.similarity:.2%}")
        print(f"  Точность слов: {result.word_accuracy:.2%}")
        print(f"  Точность символов: {result.char_accuracy:.2%}")
        print(f"  Уверенность OCR: {result.confidence:.2%}")
        print(f"  Время обработки: {result.processing_time:.2f} сек")

        if result.errors:
            print(f"  Ошибки: {', '.join(result.errors)}")

    print("\n" + "="*70)


def save_report(report: TestReport, output_file: Path):
    """Сохранение отчёта в JSON."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
    logger.info(f"Отчёт сохранён в {output_file}")


def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(
        description='Тест точности OCR для различных форматов файлов'
    )
    parser.add_argument(
        '--test-data',
        type=Path,
        help='Директория с тестовыми файлами'
    )
    parser.add_argument(
        '--ground-truth',
        type=Path,
        help='Файл с эталонным текстом'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Запустить демонстрационный тест'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Сохранить отчёт в JSON файл'
    )
    parser.add_argument(
        '--languages',
        nargs='+',
        default=['ru', 'en'],
        help='Языки для OCR (по умолчанию: ru en)'
    )
    parser.add_argument(
        '--use-gpu',
        action='store_true',
        help='Использовать GPU для ускорения'
    )

    args = parser.parse_args()

    # Создаём тестировщик
    tester = OCRAccuracyTester(
        languages=args.languages,
        use_gpu=args.use_gpu
    )

    try:
        if args.demo:
            # Демонстрационный тест
            report = tester.run_demo()
        elif args.test_data and args.ground_truth:
            # Тест с указанными данными
            report = tester.run_tests(args.test_data, args.ground_truth)
        else:
            parser.error("Укажите --test-data и --ground-truth или используйте --demo")
            return

        # Вывод отчёта
        print_report(report)

        # Сохранение если нужно
        if args.output:
            save_report(report, args.output)

    except Exception as e:
        logger.error(f"Ошибка тестирования: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
