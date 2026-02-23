"""
=============================================================================
OCR_ENGINE.PY - Движок оптического распознавания символов (OCR)
=============================================================================
Модуль для распознавания текста из изображений и сканов медицинских документов.

Поддерживаемые форматы:
- Изображения: JPG, PNG, TIFF, BMP
- PDF (через конвертацию в изображения)

Используемые технологии:
- EasyOCR для распознавания текста
- OpenCV для предобработки изображений
- Pillow для работы с изображениями
=============================================================================
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import tempfile
import os

from PIL import Image
import numpy as np

# EasyOCR
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("EasyOCR не установлен. Установите: pip install easyocr")


logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Результат OCR распознавания."""
    text: str
    confidence: float
    language: str
    processing_time: float
    image_info: Dict[str, Any] = field(default_factory=dict)
    text_blocks: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def word_count(self) -> int:
        """Количество слов в распознанном тексте."""
        return len(self.text.split())
    
    @property
    def char_count(self) -> int:
        """Количество символов в тексте."""
        return len(self.text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'text': self.text,
            'confidence': self.confidence,
            'language': self.language,
            'processing_time': self.processing_time,
            'word_count': self.word_count,
            'char_count': self.char_count,
            'text_blocks': self.text_blocks,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class TextBlock:
    """Блок текста с координатами."""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    polygon: Optional[List[Tuple[int, int]]] = None


class OCREngine:
    """
    Движок для OCR распознавания медицинских документов.
    
    Использование:
        engine = OCREngine(languages=['ru', 'en'])
        result = engine.recognize('image.jpg')
        print(result.text)
    """
    
    def __init__(
        self,
        languages: Optional[List[str]] = None,
        use_gpu: bool = False,
        confidence_threshold: float = 0.7,
        download_enabled: bool = True
    ):
        """
        Инициализация OCR движка.
        
        Args:
            languages: Список языков для распознавания (например ['ru', 'en']).
            use_gpu: Использовать GPU для ускорения.
            confidence_threshold: Порог уверенности для фильтрации результатов.
            download_enabled: Разрешить загрузку моделей при первом запуске.
        """
        if not EASYOCR_AVAILABLE:
            raise ImportError(
                "EasyOCR не установлен. Установите: pip install easyocr"
            )
        
        self.languages = languages or ['ru', 'en']
        self.use_gpu = use_gpu
        self.confidence_threshold = confidence_threshold
        self.download_enabled = download_enabled
        
        self._reader: Optional[easyocr.Reader] = None
        
        logger.info(
            f"Инициализация OCREngine: языки={self.languages}, GPU={self.use_gpu}"
        )
    
    @property
    def reader(self) -> easyocr.Reader:
        """Получить или создать Reader."""
        if self._reader is None:
            self._reader = easyocr.Reader(
                self.languages,
                gpu=self.use_gpu,
                download_enabled=self.download_enabled,
                verbose=False
            )
            logger.info("EasyOCR Reader инициализирован")
        return self._reader
    
    def recognize(
        self,
        image_source: Union[str, Path, bytes, Image.Image],
        preprocess: bool = True
    ) -> OCRResult:
        """
        Распознать текст из изображения.
        
        Args:
            image_source: Изображение (путь, байты, или PIL Image).
            preprocess: Применять предобработку изображения.
            
        Returns:
            OCRResult с распознанным текстом.
        """
        import time
        start_time = time.time()
        
        # Загружаем изображение
        image = self._load_image(image_source)
        
        # Предобработка если нужно
        if preprocess:
            image = self._preprocess_image(image)
        
        # Получаем информацию об изображении
        image_info = {
            'width': image.width,
            'height': image.height,
            'mode': image.mode,
            'format': image.format or 'unknown'
        }
        
        # Конвертируем в numpy array для EasyOCR
        image_array = np.array(image)
        
        # Распознавание
        logger.info(f"Запуск OCR распознавания ({image.width}x{image.height})")
        results = self.reader.readtext(
            image_array,
            confidence_threshold=self.confidence_threshold,
            detail=1  # Возвращать координаты и уверенность
        )
        
        # Обрабатываем результаты
        text_blocks = self._process_results(results)
        full_text = self._combine_text(text_blocks)
        
        # Средняя уверенность
        avg_confidence = (
            sum(b.confidence for b in text_blocks) / len(text_blocks)
            if text_blocks else 0.0
        )
        
        processing_time = time.time() - start_time
        
        logger.info(
            f"OCR завершён: {len(text_blocks)} блоков, "
            f"уверенность={avg_confidence:.2f}, время={processing_time:.2f}с"
        )
        
        return OCRResult(
            text=full_text,
            confidence=avg_confidence,
            language=','.join(self.languages),
            processing_time=processing_time,
            image_info=image_info,
            text_blocks=[
                {
                    'text': b.text,
                    'confidence': b.confidence,
                    'bbox': b.bbox
                }
                for b in text_blocks
            ]
        )
    
    def recognize_batch(
        self,
        image_sources: List[Union[str, Path, bytes, Image.Image]],
        preprocess: bool = True
    ) -> List[OCRResult]:
        """
        Распознать текст из нескольких изображений.
        
        Args:
            image_sources: Список изображений.
            preprocess: Применять предобработку.
            
        Returns:
            Список OCRResult.
        """
        results = []
        for i, source in enumerate(image_sources):
            logger.info(f"Обработка изображения {i+1}/{len(image_sources)}")
            result = self.recognize(source, preprocess=preprocess)
            results.append(result)
        return results
    
    def _load_image(
        self,
        source: Union[str, Path, bytes, Image.Image]
    ) -> Image.Image:
        """
        Загрузить изображение из источника.
        
        Args:
            source: Источник изображения.
            
        Returns:
            PIL Image.
        """
        if isinstance(source, Image.Image):
            return source.convert('RGB')
        
        if isinstance(source, (str, Path)):
            # Путь к файлу
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Файл не найден: {path}")
            return Image.open(path).convert('RGB')
        
        if isinstance(source, bytes):
            # Байты
            from io import BytesIO
            return Image.open(BytesIO(source)).convert('RGB')
        
        raise ValueError(f"Неподдерживаемый тип источника: {type(source)}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Предобработка изображения для улучшения распознавания.
        
        Применяемые техники:
        - Увеличение контраста
        - Удаление шума
        - Бинаризация (если нужно)
        
        Args:
            image: Исходное изображение.
            
        Returns:
            Обработанное изображение.
        """
        import cv2
        
        # Конвертируем в OpenCV формат
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 1. Удаление шума (denoising)
        image_cv = cv2.fastNlMeansDenoisingColored(image_cv, None, 10, 10, 7, 21)
        
        # 2. Увеличение резкости
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        image_cv = cv2.filter2D(image_cv, -1, kernel)
        
        # 3. Конвертация обратно в RGB
        image_cv = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
        
        return Image.fromarray(image_cv)
    
    def _process_results(self, results: List) -> List[TextBlock]:
        """
        Обработать результаты от EasyOCR.
        
        Args:
            results: Сырые результаты от readtext().
            
        Returns:
            Список TextBlock.
        """
        text_blocks = []
        
        for bbox, text, confidence in results:
            # bbox может быть списком из 4 точек или 4 координат
            if len(bbox) == 4 and all(isinstance(p, (int, float)) for p in bbox):
                # Формат: [x1, y1, x2, y2, x3, y3, x4, y4]
                x_coords = [bbox[i] for i in range(0, len(bbox), 2)]
                y_coords = [bbox[i] for i in range(1, len(bbox), 2)]
                rect_bbox = (
                    int(min(x_coords)),
                    int(min(y_coords)),
                    int(max(x_coords)),
                    int(max(y_coords))
                )
            else:
                # Формат: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                rect_bbox = (
                    int(min(x_coords)),
                    int(min(y_coords)),
                    int(max(x_coords)),
                    int(max(y_coords))
                )
            
            text_blocks.append(TextBlock(
                text=text.strip(),
                confidence=float(confidence),
                bbox=rect_bbox,
                polygon=bbox if isinstance(bbox[0], list) else None
            ))
        
        # Сортируем по вертикальной позиции (сверху вниз)
        text_blocks.sort(key=lambda b: b.bbox[1])
        
        return text_blocks
    
    def _combine_text(self, text_blocks: List[TextBlock]) -> str:
        """
        Объединить текстовые блоки в один текст.
        
        Args:
            text_blocks: Список блоков.
            
        Returns:
            Объединённый текст.
        """
        if not text_blocks:
            return ""
        
        # Группируем блоки по строкам (близкие по Y)
        lines = []
        current_line = []
        current_y = None
        line_threshold = 20  # пикселей
        
        for block in text_blocks:
            y_center = (block.bbox[1] + block.bbox[3]) / 2
            
            if current_y is None or abs(y_center - current_y) > line_threshold:
                # Новая строка
                if current_line:
                    # Сортируем текущую строку по X и объединяем
                    current_line.sort(key=lambda b: b.bbox[0])
                    lines.append(' '.join(b.text for b in current_line))
                current_line = [block]
                current_y = y_center
            else:
                current_line.append(block)
        
        # Добавляем последнюю строку
        if current_line:
            current_line.sort(key=lambda b: b.bbox[0])
            lines.append(' '.join(b.text for b in current_line))
        
        return '\n'.join(lines)


class MedicalDocumentOCR:
    """
    Специализированный OCR для медицинских документов.
    
    Добавляет:
    - Обработку многостраничных PDF
    - Сохранение структуры документа
    - Фильтрацию артефактов
    """
    
    def __init__(self, ocr_engine: Optional[OCREngine] = None, **kwargs):
        """
        Инициализация.
        
        Args:
            ocr_engine: Существующий OCREngine или параметры для создания.
            **kwargs: Параметры для OCREngine.
        """
        self.ocr = ocr_engine or OCREngine(**kwargs)
    
    def process_pdf(
        self,
        pdf_path: Union[str, Path],
        dpi: int = 300,
        pages: Optional[List[int]] = None
    ) -> List[OCRResult]:
        """
        Обработать многостраничный PDF.
        
        Args:
            pdf_path: Путь к PDF файлу.
            dpi: Разрешение конвертации.
            pages: Список страниц для обработки (None = все).
            
        Returns:
            Список OCRResult для каждой страницы.
        """
        from .pdf_parser import PDFParser
        
        parser = PDFParser()
        images = parser.pdf_to_images(pdf_path, dpi=dpi, pages=pages)
        
        results = []
        for i, image in enumerate(images):
            page_num = pages[i] if pages else i + 1
            logger.info(f"Обработка страницы {page_num}")
            
            result = self.ocr.recognize(image, preprocess=True)
            result.image_info['page'] = page_num
            results.append(result)
        
        return results
    
    def process_file(
        self,
        file_path: Union[str, Path]
    ) -> Union[OCRResult, List[OCRResult]]:
        """
        Обработать файл (изображение или PDF).
        
        Args:
            file_path: Путь к файлу.
            
        Returns:
            OCRResult для изображений или список для PDF.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp']:
            return self.ocr.recognize(path)
        elif suffix == '.pdf':
            return self.process_pdf(path)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {suffix}")
    
    def get_full_text(
        self,
        results: Union[OCRResult, List[OCRResult]]
    ) -> str:
        """
        Получить полный текст из результатов.
        
        Args:
            results: Результат(ы) OCR.
            
        Returns:
            Полный текст.
        """
        if isinstance(results, OCRResult):
            return results.text
        
        # Список результатов (многостраничный документ)
        texts = []
        for i, result in enumerate(results):
            header = f"=== СТРАНИЦА {result.image_info.get('page', i+1)} ==="
            texts.append(f"{header}\n{result.text}")
        
        return '\n\n'.join(texts)


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------

def recognize_text(
    image_path: Union[str, Path],
    languages: Optional[List[str]] = None
) -> str:
    """
    Быстрое распознавание текста из изображения.
    
    Args:
        image_path: Путь к изображению.
        languages: Языки распознавания.
        
    Returns:
        Распознанный текст.
    """
    engine = OCREngine(languages=languages)
    result = engine.recognize(image_path)
    return result.text


def create_ocr_engine(
    languages: Optional[List[str]] = None,
    use_gpu: bool = False
) -> OCREngine:
    """
    Создать OCR движок с настройками.
    
    Args:
        languages: Языки.
        use_gpu: Использовать GPU.
        
    Returns:
        OCREngine.
    """
    return OCREngine(languages=languages, use_gpu=use_gpu)
