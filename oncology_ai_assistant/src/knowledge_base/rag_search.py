"""
=============================================================================
RAG_SEARCH.PY - RAG поиск по клиническим рекомендациям
=============================================================================
Модуль для семантического поиска релевантных фрагментов клинических
рекомендаций с использованием векторных эмбеддингов.

Технологии:
- Sentence Transformers для создания эмбеддингов
- FAISS для векторного поиска
- Поддержка русских медицинских текстов (ruBert)
=============================================================================
"""

import logging
import os
import pickle
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib

import numpy as np

# Sentence Transformers для эмбеддингов
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("sentence-transformers не установлен")

# FAISS для векторного поиска
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("faiss не установлен")


logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Фрагмент документа для индексации."""
    id: str
    text: str
    source: str  # Путь к исходному документу
    section: str  # Раздел документа
    page: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'id': self.id,
            'text': self.text,
            'source': self.source,
            'section': self.section,
            'page': self.page,
            'metadata': self.metadata
        }


@dataclass
class SearchMatch:
    """Результат поиска."""
    chunk: DocumentChunk
    score: float
    rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'chunk': self.chunk.to_dict(),
            'score': self.score,
            'rank': self.rank
        }


@dataclass
class SearchResult:
    """Результаты RAG поиска."""
    query: str
    matches: List[SearchMatch] = field(default_factory=list)
    search_time: float = 0.0
    total_chunks_searched: int = 0
    
    @property
    def top_match(self) -> Optional[SearchMatch]:
        """Лучшее совпадение."""
        return self.matches[0] if self.matches else None
    
    def get_formatted_context(self, max_matches: int = 5) -> str:
        """
        Получить форматированный контекст для промпта.
        
        Args:
            max_matches: Максимальное количество совпадений.
            
        Returns:
            Текст контекста.
        """
        texts = []
        for match in self.matches[:max_matches]:
            source_name = Path(match.chunk.source).stem
            texts.append(
                f"[Источник: {source_name}, Раздел: {match.chunk.section}]\n"
                f"{match.chunk.text}"
            )
        return '\n\n---\n\n'.join(texts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'query': self.query,
            'matches': [m.to_dict() for m in self.matches],
            'search_time': self.search_time,
            'total_chunks_searched': self.total_chunks_searched
        }


class RAGSearchEngine:
    """
    RAG поисковый движок для клинических рекомендаций.
    
    Использование:
        engine = RAGSearchEngine()
        engine.index_documents(documents)
        results = engine.search("лечение рака молочной железы")
    """
    
    def __init__(
        self,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        index_dir: Optional[str] = None,
        similarity_threshold: float = 0.7
    ):
        """
        Инициализация RAG движка.
        
        Args:
            embedding_model: Модель для эмбеддингов.
            chunk_size: Размер чанка в символах.
            chunk_overlap: Перекрытие между чанками.
            index_dir: Директория для сохранения индекса.
            similarity_threshold: Порог схожести.
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers не установлен. "
                "Установите: pip install sentence-transformers"
            )
        
        if not FAISS_AVAILABLE:
            raise ImportError(
                "faiss не установлен. "
                "Установите: pip install faiss-cpu"
            )
        
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.index_dir = Path(index_dir) if index_dir else None
        self.similarity_threshold = similarity_threshold
        
        self._model: Optional[SentenceTransformer] = None
        self._index: Optional[faiss.IndexFlatIP] = None
        self._chunks: List[DocumentChunk] = []
        self._chunk_embeddings: Optional[np.ndarray] = None
        
        logger.info(f"Инициализация RAGSearchEngine: модель={embedding_model}")
    
    @property
    def model(self) -> SentenceTransformer:
        """Получить или загрузить модель эмбеддингов."""
        if self._model is None:
            logger.info(f"Загрузка модели эмбеддингов: {self.embedding_model_name}")
            self._model = SentenceTransformer(self.embedding_model_name)
            logger.info("Модель загружена")
        return self._model
    
    def _create_chunk_id(self, text: str, source: str, index: int) -> str:
        """Создать уникальный ID для чанка."""
        content = f"{source}:{index}:{text[:100]}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def chunk_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """
        Разбить документы на чанки.
        
        Args:
            documents: Список документов с полями:
                      - text: текст
                      - source: источник
                      - sections: разделы (опционально)
                      
        Returns:
            Список DocumentChunk.
        """
        chunks = []
        
        for doc in documents:
            text = doc.get('text', '')
            source = doc.get('source', 'unknown')
            sections = doc.get('sections', {})
            
            if not text:
                continue
            
            # Если есть разделы, чанкуем по разделам
            if sections:
                for section_name, section_text in sections.items():
                    section_chunks = self._chunk_text(
                        section_text, source, section_name
                    )
                    chunks.extend(section_chunks)
            else:
                # Чанкуем весь документ
                doc_chunks = self._chunk_text(text, source, 'main')
                chunks.extend(doc_chunks)
        
        logger.info(f"Создано {len(chunks)} чанков из {len(documents)} документов")
        return chunks
    
    def _chunk_text(
        self,
        text: str,
        source: str,
        section: str
    ) -> List[DocumentChunk]:
        """
        Разбить текст на перекрывающиеся чанки.
        
        Args:
            text: Текст для разбиения.
            source: Источник.
            section: Раздел.
            
        Returns:
            Список чанков.
        """
        chunks = []
        
        # Разбиваем по предложениям
        sentences = self._split_into_sentences(text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size:
                # Создаём чанк
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunk = DocumentChunk(
                        id=self._create_chunk_id(chunk_text, source, len(chunks)),
                        text=chunk_text,
                        source=source,
                        section=section
                    )
                    chunks.append(chunk)
                
                # Начинаем новый чанк с перекрытием
                overlap_chunks = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_chunks.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break
                
                current_chunk = overlap_chunks
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Добавляем последний чанк
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk = DocumentChunk(
                id=self._create_chunk_id(chunk_text, source, len(chunks)),
                text=chunk_text,
                source=source,
                section=section
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Разбить текст на предложения.
        
        Args:
            text: Текст.
            
        Returns:
            Список предложений.
        """
        import re
        
        # Простой сплит по концам предложений
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        rebuild: bool = True
    ) -> int:
        """
        Индексировать документы.
        
        Args:
            documents: Документы для индексации.
            rebuild: Перестроить индекс если существует.
            
        Returns:
            Количество проиндексированных чанков.
        """
        import time
        start_time = time.time()
        
        # Создаём чанки
        self._chunks = self.chunk_documents(documents)
        
        if not self._chunks:
            logger.warning("Нет чанков для индексации")
            return 0
        
        # Создаём эмбеддинги
        logger.info(f"Создание эмбеддингов для {len(self._chunks)} чанков")
        texts = [chunk.text for chunk in self._chunks]
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        self._chunk_embeddings = embeddings.astype('float32')
        
        # Создаём FAISS индекс (используем Inner Product для нормализованных векторов)
        dimension = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dimension)
        self._index.add(self._chunk_embeddings)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Индексирование завершено: {len(self._chunks)} чанков, "
            f"время={elapsed:.2f}с"
        )
        
        # Сохраняем индекс если указана директория
        if self.index_dir:
            self.save_index()
        
        return len(self._chunks)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_source: Optional[str] = None
    ) -> SearchResult:
        """
        Поиск релевантных чанков.
        
        Args:
            query: Поисковый запрос.
            top_k: Количество результатов.
            filter_source: Фильтр по источнику.
            
        Returns:
            SearchResult.
        """
        import time
        start_time = time.time()
        
        if self._index is None or len(self._chunks) == 0:
            logger.warning("Индекс пуст. Сначала проиндексируйте документы.")
            return SearchResult(query=query)
        
        # Создаём эмбеддинг запроса
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype('float32')
        
        # Поиск
        scores, indices = self._index.search(query_embedding, top_k * 2)
        
        # Обрабатываем результаты
        matches = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < 0 or idx >= len(self._chunks):
                continue
            
            chunk = self._chunks[idx]
            
            # Фильтр по источнику
            if filter_source and filter_source not in chunk.source:
                continue
            
            # Порог схожести
            if score < self.similarity_threshold:
                continue
            
            match = SearchMatch(
                chunk=chunk,
                score=float(score),
                rank=len(matches) + 1
            )
            matches.append(match)
        
        # Ограничиваем до top_k
        matches = matches[:top_k]
        
        search_time = time.time() - start_time
        
        return SearchResult(
            query=query,
            matches=matches,
            search_time=search_time,
            total_chunks_searched=len(self._chunks)
        )
    
    def search_with_context(
        self,
        query: str,
        top_k: int = 5
    ) -> Tuple[str, SearchResult]:
        """
        Поиск с готовым контекстом для промпта.
        
        Args:
            query: Запрос.
            top_k: Количество результатов.
            
        Returns:
            Кортеж (контекст, результаты).
        """
        results = self.search(query, top_k=top_k)
        context = results.get_formatted_context(max_matches=top_k)
        return context, results
    
    def save_index(self, path: Optional[str] = None) -> None:
        """
        Сохранить индекс на диск.
        
        Args:
            path: Путь для сохранения.
        """
        if self._index is None:
            logger.warning("Нет индекса для сохранения")
            return
        
        save_path = Path(path) if path else (self.index_dir or Path("./rag_index"))
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем FAISS индекс
        faiss.write_index(self._index, str(save_path / "index.faiss"))
        
        # Сохраняем чанки
        with open(save_path / "chunks.pkl", 'wb') as f:
            pickle.dump(self._chunks, f)
        
        # Сохраняем метаданные
        metadata = {
            'embedding_model': self.embedding_model_name,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'num_chunks': len(self._chunks),
            'indexed_at': datetime.now().isoformat()
        }
        with open(save_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Индекс сохранён: {save_path}")
    
    def load_index(self, path: Optional[str] = None) -> bool:
        """
        Загрузить индекс с диска.
        
        Args:
            path: Путь к индексу.
            
        Returns:
            True если успешно загружено.
        """
        load_path = Path(path) if path else (self.index_dir or Path("./rag_index"))
        
        if not load_path.exists():
            logger.warning(f"Индекс не найден: {load_path}")
            return False
        
        index_file = load_path / "index.faiss"
        chunks_file = load_path / "chunks.pkl"
        
        if not index_file.exists() or not chunks_file.exists():
            logger.warning("Файлы индекса не найдены")
            return False
        
        # Загружаем FAISS индекс
        self._index = faiss.read_index(str(index_file))
        
        # Загружаем чанки
        with open(chunks_file, 'rb') as f:
            self._chunks = pickle.load(f)
        
        logger.info(f"Индекс загружен: {len(self._chunks)} чанков")
        return True
    
    @property
    def is_indexed(self) -> bool:
        """Есть ли проиндексированные документы."""
        return self._index is not None and len(self._chunks) > 0
    
    @property
    def indexed_chunks_count(self) -> int:
        """Количество проиндексированных чанков."""
        return len(self._chunks)


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------

def create_rag_engine(
    index_dir: Optional[str] = None,
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
) -> RAGSearchEngine:
    """
    Создать RAG движок.
    
    Args:
        index_dir: Директория индекса.
        embedding_model: Модель эмбеддингов.
        
    Returns:
        RAGSearchEngine.
    """
    return RAGSearchEngine(
        index_dir=index_dir,
        embedding_model=embedding_model
    )


def index_clinical_guidelines(
    documents: List[Dict[str, Any]],
    index_dir: str,
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
) -> RAGSearchEngine:
    """
    Проиндексировать клинические рекомендации.
    
    Args:
        documents: Документы для индексации.
        index_dir: Директория для сохранения индекса.
        embedding_model: Модель эмбеддингов.
        
    Returns:
        RAGSearchEngine с проиндексированными документами.
    """
    engine = RAGSearchEngine(
        index_dir=index_dir,
        embedding_model=embedding_model
    )
    engine.index_documents(documents)
    return engine
