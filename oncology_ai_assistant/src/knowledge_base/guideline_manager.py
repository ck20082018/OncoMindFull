"""
=============================================================================
GUIDELINE_MANAGER.PY - Менеджер клинических рекомендаций
=============================================================================
Модуль для управления базой знаний клинических рекомендаций:
- Загрузка локальных PDF рекомендаций Минздрава РФ
- Парсинг и структурирование документов
- Интеграция с RAG поиском
- Кэширование и версионирование
=============================================================================
"""

import logging
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import shutil

from .rag_search import RAGSearchEngine, DocumentChunk, SearchResult


logger = logging.getLogger(__name__)


@dataclass
class GuidelineDocument:
    """Клиническая рекомендация."""
    id: str
    title: str
    source: str  # Минздрав РФ, NCCN, ESMO
    disease_area: str  # Онкология, конкретная локализация
    version: str
    approval_date: Optional[str] = None
    file_path: Optional[str] = None
    content: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def full_id(self) -> str:
        """Полный идентификатор."""
        return f"{self.source}:{self.id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'id': self.id,
            'title': self.title,
            'source': self.source,
            'disease_area': self.disease_area,
            'version': self.version,
            'approval_date': self.approval_date,
            'file_path': self.file_path,
            'content': self.content,
            'sections': self.sections,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GuidelineDocument':
        """Создать из словаря."""
        return cls(**data)


@dataclass
class GuidelineCatalog:
    """Каталог клинических рекомендаций."""
    documents: List[GuidelineDocument] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    
    def add(self, doc: GuidelineDocument) -> None:
        """Добавить документ."""
        self.documents.append(doc)
        self.last_updated = datetime.now()
    
    def get_by_id(self, doc_id: str) -> Optional[GuidelineDocument]:
        """Получить документ по ID."""
        for doc in self.documents:
            if doc.id == doc_id or doc.full_id == doc_id:
                return doc
        return None
    
    def get_by_disease(self, disease: str) -> List[GuidelineDocument]:
        """Получить документы по заболеванию."""
        disease_lower = disease.lower()
        return [
            doc for doc in self.documents
            if disease_lower in doc.disease_area.lower() or
               disease_lower in doc.title.lower()
        ]
    
    def get_by_source(self, source: str) -> List[GuidelineDocument]:
        """Получить документы по источнику."""
        return [doc for doc in self.documents if doc.source == source]
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'documents': [doc.to_dict() for doc in self.documents],
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class GuidelineManager:
    """
    Менеджер клинических рекомендаций.
    
    Использование:
        manager = GuidelineManager(data_dir="knowledge_base_data/minzdrav")
        manager.load_local_guidelines()
        results = manager.search("лечение меланомы")
    """
    
    def __init__(
        self,
        data_dir: str = "knowledge_base_data/minzdrav",
        index_dir: str = "knowledge_base_data/index",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        auto_index: bool = True
    ):
        """
        Инициализация менеджера.
        
        Args:
            data_dir: Директория с документами рекомендаций.
            index_dir: Директория для RAG индекса.
            embedding_model: Модель для эмбеддингов.
            auto_index: Автоматически индексировать при загрузке.
        """
        self.data_dir = Path(data_dir)
        self.index_dir = Path(index_dir)
        self.embedding_model = embedding_model
        self.auto_index = auto_index
        
        self.catalog = GuidelineCatalog()
        self.rag_engine: Optional[RAGSearchEngine] = None
        
        # Создаём директории если не существуют
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"GuidelineManager инициализирован: data_dir={self.data_dir}")
    
    def load_local_guidelines(
        self,
        file_pattern: str = "*.pdf"
    ) -> int:
        """
        Загрузить локальные клинические рекомендации.

        Args:
            file_pattern: Шаблон для поиска файлов.

        Returns:
            Количество загруженных документов.
        """
        logger.info(f"Загрузка рекомендаций из {self.data_dir}")

        if not self.data_dir.exists():
            logger.warning(f"Директория не найдена: {self.data_dir}")
            return 0

        # Ищем PDF и HTML файлы
        pdf_files = list(self.data_dir.glob("*.pdf"))
        html_files = list(self.data_dir.glob("*.html"))
        all_files = pdf_files + html_files
        logger.info(f"Найдено {len(all_files)} файлов ({len(pdf_files)} PDF, {len(html_files)} HTML)")

        loaded_count = 0
        for file_path in all_files:
            try:
                if file_path.suffix.lower() == '.html':
                    doc = self._parse_guideline_html(file_path)
                else:
                    doc = self._parse_guideline_pdf(file_path)
                if doc:
                    self.catalog.add(doc)
                    loaded_count += 1
            except Exception as e:
                logger.error(f"Ошибка при загрузке {file_path}: {e}")

        # Индексируем если включено
        if self.auto_index and loaded_count > 0:
            self._build_index()

        logger.info(f"Загружено {loaded_count} рекомендаций")
        return loaded_count

    def _parse_guideline_html(self, html_path: Path) -> Optional[GuidelineDocument]:
        """
        Распарсить HTML клинической рекомендации.

        Args:
            html_path: Путь к HTML.

        Returns:
            GuidelineDocument или None.
        """
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Извлекаем заголовок из HTML
            import re
            title_match = re.search(r'<title>([^<]+)</title>', content)
            title = title_match.group(1).strip() if title_match else html_path.stem
            
            # Извлекаем основной текст
            body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
            body_text = body_match.group(1) if body_match else content
            
            # Удаляем HTML теги
            from html import unescape
            text = re.sub(r'<[^>]+>', '', body_text)
            text = unescape(text)
            
            # Создаём ID из имени файла
            file_id = html_path.stem
            
            # Пытаемся извлечь метаданные
            disease_area = self._extract_disease_area(text[:1000])
            version = self._extract_version(text)
            
            guideline = GuidelineDocument(
                id=file_id,
                title=title,
                source="Минздрав РФ",
                disease_area=disease_area,
                version=version or "2026",
                approval_date=None,
                file_path=str(html_path),
                content=text,
                metadata={'format': 'html'}
            )
            
            logger.info(f"Загружена рекомендация: {title}")
            return guideline
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке HTML {html_path}: {e}")
            return None
    
    def _parse_guideline_pdf(self, pdf_path: Path) -> Optional[GuidelineDocument]:
        """
        Распарсить PDF клинической рекомендации.
        
        Args:
            pdf_path: Путь к PDF.
            
        Returns:
            GuidelineDocument или None.
        """
        from ..ocr.pdf_parser import PDFParser
        
        parser = PDFParser(extract_tables=False)
        
        try:
            doc = parser.parse(pdf_path)
        except Exception as e:
            logger.error(f"Ошибка парсинга PDF {pdf_path}: {e}")
            return None
        
        # Создаём ID из имени файла
        file_id = pdf_path.stem
        
        # Пытаемся извлечь метаданные из имени файла и контента
        title = self._extract_title(file_id, doc.full_text[:500])
        disease_area = self._extract_disease_area(doc.full_text[:1000])
        version = self._extract_version(doc.full_text)
        approval_date = self._extract_approval_date(doc.full_text)
        
        # Разбиваем на секции
        sections = self._split_into_sections(doc.full_text)
        
        guideline = GuidelineDocument(
            id=file_id,
            title=title,
            source="Минздрав РФ",
            disease_area=disease_area,
            version=version,
            approval_date=approval_date,
            file_path=str(pdf_path),
            content=doc.full_text,
            sections=sections,
            metadata={
                'total_pages': doc.total_pages,
                'word_count': len(doc.full_text.split()),
                'parsed_at': datetime.now().isoformat()
            }
        )
        
        logger.info(f"Распарсена рекомендация: {guideline.title}")
        return guideline
    
    def _extract_title(self, file_id: str, text_sample: str) -> str:
        """Извлечь заголовок."""
        # Пытаемся найти заголовок в тексте
        lines = text_sample.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 20 and line.isupper():
                return line
        
        # Если не нашли, используем имя файла
        return file_id.replace('_', ' ').replace('-', ' ').title()
    
    def _extract_disease_area(self, text_sample: str) -> str:
        """Извлечь область заболевания."""
        # Ключевые слова для определения локализации
        cancer_keywords = {
            'молочная железа': 'Рак молочной железы',
            'легкое': 'Рак лёгкого',
            'желудок': 'Рак желудка',
            'кишечник': 'Рак кишечника',
            'толстая кишка': 'Рак толстой кишки',
            'прямая кишка': 'Рак прямой кишки',
            'меланома': 'Меланома',
            'лимфома': 'Лимфома',
            'лейкоз': 'Лейкоз',
            'простата': 'Рак простаты',
            'яичник': 'Рак яичников',
            'шейка матки': 'Рак шейки матки',
            'матка': 'Рак матки',
            'печень': 'Рак печени',
            'поджелудочная': 'Рак поджелудочной железы',
            'почка': 'Рак почки',
            'мочевой пузырь': 'Рак мочевого пузыря',
            'головы и шеи': 'Опухоли головы и шеи',
            'мозг': 'Опухоли мозга',
            'щитовидная': 'Рак щитовидной железы',
        }
        
        text_lower = text_sample.lower()
        for keyword, disease in cancer_keywords.items():
            if keyword in text_lower:
                return disease
        
        return "Онкология (общая)"
    
    def _extract_version(self, text: str) -> str:
        """Извлечь версию рекомендации."""
        import re
        
        # Ищем паттерны версии
        patterns = [
            r'версия\s*(\d+\.\d+)',
            r'redaction\s*(\d{4})',
            r'редакция\s*(\d{4})',
            r'(\d{4})\s*год',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "актуальная"
    
    def _extract_approval_date(self, text: str) -> Optional[str]:
        """Извлечь дату утверждения."""
        import re
        
        # Ищем даты в различных форматах
        patterns = [
            r'(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _split_into_sections(self, text: str) -> Dict[str, str]:
        """
        Разбить текст на секции.
        
        Args:
            text: Полный текст документа.
            
        Returns:
            Словарь {название_секции: текст}.
        """
        sections = {}
        
        # Ключевые слова для секций
        section_keywords = [
            'ОПРЕДЕЛЕНИЕ',
            'ЭТИОЛОГИЯ',
            'КЛАССИФИКАЦИЯ',
            'ДИАГНОСТИКА',
            'ЛЕЧЕНИЕ',
            'ПРОФИЛАКТИКА',
            'РЕАБИЛИТАЦИЯ',
            'ПРОГНОЗ',
            'СПИСОК СОКРАЩЕНИЙ',
            'ПРИЛОЖЕНИЕ',
            'ЛИТЕРАТУРА',
        ]
        
        lines = text.split('\n')
        current_section = 'Введение'
        current_text = []
        
        for line in lines:
            stripped = line.strip()
            
            # Проверяем является ли строка заголовком секции
            is_section_header = False
            for keyword in section_keywords:
                if keyword in stripped.upper():
                    # Сохраняем предыдущую секцию
                    if current_text:
                        sections[current_section] = '\n'.join(current_text)
                    current_section = stripped
                    current_text = []
                    is_section_header = True
                    break
            
            if not is_section_header:
                current_text.append(line)
        
        # Добавляем последнюю секцию
        if current_text:
            sections[current_section] = '\n'.join(current_text)
        
        return sections
    
    def _build_index(self) -> None:
        """Построить RAG индекс."""
        logger.info("Построение RAG индекса")
        
        # Готовим документы для индексации
        documents = []
        for guideline in self.catalog.documents:
            doc_data = {
                'text': guideline.content,
                'source': guideline.full_id,
                'sections': guideline.sections
            }
            documents.append(doc_data)
        
        # Создаём и строим индекс
        self.rag_engine = RAGSearchEngine(
            embedding_model=self.embedding_model,
            index_dir=str(self.index_dir)
        )
        self.rag_engine.index_documents(documents)
        
        logger.info(f"RAG индекс построен: {self.rag_engine.indexed_chunks_count} чанков")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_source: Optional[str] = None
    ) -> SearchResult:
        """
        Поиск по клиническим рекомендациям.
        
        Args:
            query: Поисковый запрос.
            top_k: Количество результатов.
            filter_source: Фильтр по источнику.
            
        Returns:
            SearchResult.
        """
        if self.rag_engine is None:
            # Пытаемся загрузить существующий индекс
            if not self._load_index():
                logger.warning("RAG индекс не загружен. Запустите load_local_guidelines().")
                return SearchResult(query=query)
        
        return self.rag_engine.search(
            query=query,
            top_k=top_k,
            filter_source=filter_source
        )
    
    def _load_index(self) -> bool:
        """Загрузить существующий RAG индекс."""
        if self.rag_engine is None:
            self.rag_engine = RAGSearchEngine(
                embedding_model=self.embedding_model,
                index_dir=str(self.index_dir)
            )
        
        return self.rag_engine.load_index()
    
    def get_relevant_excerpts(
        self,
        query: str,
        top_k: int = 3
    ) -> str:
        """
        Получить релевантные выдержки для промпта.
        
        Args:
            query: Запрос.
            top_k: Количество выдержек.
            
        Returns:
            Текст выдержек.
        """
        results = self.search(query, top_k=top_k)
        return results.get_formatted_context(max_matches=top_k)
    
    def get_guideline_for_cancer(self, cancer_type: str) -> List[GuidelineDocument]:
        """
        Получить рекомендации для типа рака.
        
        Args:
            cancer_type: Тип рака.
            
        Returns:
            Список рекомендаций.
        """
        return self.catalog.get_by_disease(cancer_type)
    
    def save_catalog(self, path: Optional[str] = None) -> None:
        """Сохранить каталог."""
        save_path = Path(path) if path else (self.data_dir / "catalog.json")
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self.catalog.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Каталог сохранён: {save_path}")
    
    def load_catalog(self, path: Optional[str] = None) -> int:
        """
        Загрузить каталог.
        
        Args:
            path: Путь к каталогу.
            
        Returns:
            Количество загруженных документов.
        """
        load_path = Path(path) if path else (self.data_dir / "catalog.json")
        
        if not load_path.exists():
            logger.warning(f"Каталог не найден: {load_path}")
            return 0
        
        with open(load_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.catalog = GuidelineCatalog(
            documents=[
                GuidelineDocument.from_dict(d)
                for d in data.get('documents', [])
            ],
            last_updated=(
                datetime.fromisoformat(data['last_updated'])
                if data.get('last_updated') else None
            )
        )
        
        logger.info(f"Каталог загружен: {len(self.catalog.documents)} документов")
        return len(self.catalog.documents)
    
    def clear_cache(self) -> None:
        """Очистить кэш и индекс."""
        if self.index_dir.exists():
            shutil.rmtree(self.index_dir)
            self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.rag_engine = None
        logger.info("Кэш очищен")


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------

def create_guideline_manager(
    data_dir: str = "knowledge_base_data/minzdrav",
    index_dir: str = "knowledge_base_data/index"
) -> GuidelineManager:
    """
    Создать менеджер клинических рекомендаций.
    
    Args:
        data_dir: Директория с документами.
        index_dir: Директория для индекса.
        
    Returns:
        GuidelineManager.
    """
    return GuidelineManager(
        data_dir=data_dir,
        index_dir=index_dir,
        auto_index=True
    )
