"""
=============================================================================
PIPELINE.PY - Основной пайплайн обработки медицинских данных
=============================================================================
Модуль реализует полный цикл обработки запроса:
1. Загрузка файла (PDF, изображение, Excel)
2. OCR распознавание текста
3. Анонимизация персональных данных
4. RAG поиск релевантных клинических рекомендаций
5. Запрос к YandexGPT для анализа
6. Валидация и возврат результата

Пайплайн гарантирует что анонимизация выполняется ДО отправки в облако.
=============================================================================
"""

import logging
import time
import os
import shutil
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..anonymization.anonymizer import Anonymizer, AnonymizationResult
from ..llm.yandex_client_new import YandexGPTConfig, YandexGPTClient, LLMResponse
from ..llm.prompt_templates import (
    get_system_prompt,
    create_doctor_prompt,
    create_patient_prompt
)
from ..llm.json_validator import JSONValidator, ValidationResultDetail
from ..ocr.ocr_engine import OCREngine, MedicalDocumentOCR
from ..ocr.pdf_parser import PDFParser, ExcelParser
from ..knowledge_base.rag_search import RAGSearchEngine, SearchResult
from ..knowledge_base.guideline_manager import GuidelineManager


logger = logging.getLogger(__name__)


@dataclass
class PipelineInput:
    """Входные данные пайплайна."""
    file_path: str
    file_type: str  # 'pdf', 'image', 'excel'
    patient_id: Optional[str] = None
    query: Optional[str] = None
    mode: str = 'doctor'  # 'doctor' или 'patient'
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'file_path': self.file_path,
            'file_type': self.file_type,
            'patient_id': self.patient_id,
            'query': self.query,
            'mode': self.mode
        }


@dataclass
class PipelineOutput:
    """Результат работы пайплайна."""
    success: bool
    mode: str
    data: Dict[str, Any] = field(default_factory=dict)
    anonymization_result: Optional[AnonymizationResult] = None
    rag_results: Optional[SearchResult] = None
    llm_response: Optional[LLMResponse] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_valid(self) -> bool:
        """Успешно ли выполнен пайплайн."""
        return self.success and self.data is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'success': self.success,
            'mode': self.mode,
            'data': self.data,
            'anonymization': {
                'matches_count': self.anonymization_result.matches_count if self.anonymization_result else 0,
                'pii_types': self.anonymization_result.pii_types if self.anonymization_result else []
            } if self.anonymization_result else None,
            'processing_time': self.processing_time,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PipelineStage:
    """Информация о стадии обработки."""
    name: str
    success: bool
    duration: float
    message: str = ""


class OncologyPipeline:
    """
    Основной пайплайн обработки онкологических данных.
    
    Использование:
        pipeline = OncologyPipeline(config)
        result = pipeline.process(file_path, mode='doctor')
    """
    
    def __init__(
        self,
        yandex_config: Union[YandexGPTConfig, Dict[str, Any]],
        data_dir: str = "knowledge_base_data/minzdrav",
        temp_dir: str = "temp",
        anonymization_strict: bool = True
    ):
        """
        Инициализация пайплайна.
        
        Args:
            yandex_config: Конфигурация Yandex Cloud.
            data_dir: Директория с клиническими рекомендациями.
            temp_dir: Директория для временных файлов.
            anonymization_strict: Строгий режим анонимизации.
        """
        self.yandex_config = yandex_config
        self.data_dir = Path(data_dir)
        self.temp_dir = Path(temp_dir)
        self.anonymization_strict = anonymization_strict
        
        # Компоненты (ленивая инициализация)
        self._anonymizer: Optional[Anonymizer] = None
        self._ocr_engine: Optional[OCREngine] = None
        self._guideline_manager: Optional[GuidelineManager] = None
        self._llm_client: Optional[YandexGPTClient] = None
        self._json_validator: Optional[JSONValidator] = None
        
        # Создаём temp директорию
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("OncologyPipeline инициализирован")
    
    @property
    def anonymizer(self) -> Anonymizer:
        """Получить анонимайзер."""
        if self._anonymizer is None:
            self._anonymizer = Anonymizer(strict_mode=self.anonymization_strict)
        return self._anonymizer
    
    @property
    def ocr_engine(self) -> OCREngine:
        """Получить OCR движок."""
        if self._ocr_engine is None:
            self._ocr_engine = OCREngine(languages=['ru', 'en'])
        return self._ocr_engine
    
    @property
    def guideline_manager(self) -> GuidelineManager:
        """Получить менеджер рекомендаций."""
        if self._guideline_manager is None:
            self._guideline_manager = GuidelineManager(
                data_dir=str(self.data_dir)
            )
            self._guideline_manager.load_local_guidelines()
        return self._guideline_manager
    
    @property
    def llm_client(self) -> YandexGPTClient:
        """Получить LLM клиент."""
        if self._llm_client is None:
            self._llm_client = YandexGPTClient(self.yandex_config)
        return self._llm_client
    
    @property
    def json_validator(self) -> JSONValidator:
        """Получить JSON валидатор."""
        if self._json_validator is None:
            self._json_validator = JSONValidator()
        return self._json_validator
    
    def process(
        self,
        file_path: Union[str, Path],
        mode: str = 'doctor',
        query: Optional[str] = None
    ) -> PipelineOutput:
        """
        Обработать файл и получить результат.

        Args:
            file_path: Путь к файлу.
            mode: Режим ('doctor' или 'patient').
            query: Дополнительный запрос.

        Returns:
            PipelineOutput.
        """
        start_time = time.time()
        file_path = Path(file_path)

        # Сохраняем mode в объекте для использования в других методах
        self.mode = mode

        logger.info(f"Запуск пайплайна: {file_path}, режим={mode}")

        output = PipelineOutput(
            success=False,
            mode=mode
        )
        
        stages: List[PipelineStage] = []
        
        try:
            # Этап 1: Извлечение текста (OCR)
            stage_start = time.time()
            text = self._extract_text(file_path)
            stages.append(PipelineStage(
                name="OCR",
                success=True,
                duration=time.time() - stage_start,
                message=f"Извлечено {len(text)} символов"
            ))
            
            # Этап 2: Анонимизация
            stage_start = time.time()
            anon_result = self.anonymizer.anonymize(text)
            anonymized_text = anon_result.anonymized_text
            output.anonymization_result = anon_result
            stages.append(PipelineStage(
                name="Анонимизация",
                success=True,
                duration=time.time() - stage_start,
                message=f"Найдено {anon_result.matches_count} PII"
            ))
            
            # Этап 3: RAG поиск
            stage_start = time.time()
            rag_results = self.guideline_manager.search(
                query=query or self._auto_detect_query(anonymized_text),
                top_k=5
            )
            output.rag_results = rag_results
            stages.append(PipelineStage(
                name="RAG поиск",
                success=True,
                duration=time.time() - stage_start,
                message=f"Найдено {len(rag_results.matches)} совпадений"
            ))
            
            # Этап 4: Формирование промпта
            stage_start = time.time()
            system_prompt = get_system_prompt(mode)
            user_prompt = self._build_user_prompt(
                text=anonymized_text,
                rag_context=rag_results.get_formatted_context(),
                query=query
            )
            stages.append(PipelineStage(
                name="Промпт",
                success=True,
                duration=time.time() - stage_start
            ))
            
            # Этап 5: Запрос к LLM
            stage_start = time.time()
            llm_response = self.llm_client.complete(
                user_text=user_prompt,
                system_prompt=system_prompt,
                json_mode=True
            )
            output.llm_response = llm_response
            stages.append(PipelineStage(
                name="LLM",
                success=True,
                duration=time.time() - stage_start,
                message=f"{llm_response.total_tokens} токенов"
            ))
            
            # Этап 6: Валидация JSON
            stage_start = time.time()
            validation = self.json_validator.validate(
                llm_response.text,
                schema_type=mode
            )
            stages.append(PipelineStage(
                name="Валидация",
                success=validation.is_valid,
                duration=time.time() - stage_start
            ))
            
            if not validation.is_valid:
                output.error_message = f"Валидация не пройдена: {validation.errors}"
                logger.warning(f"Валидация не пройдена: {validation.errors}")
            
            output.data = validation.data
            output.success = validation.is_valid
            
        except Exception as e:
            logger.error(f"Ошибка пайплайна: {e}", exc_info=True)
            output.error_message = str(e)
            output.success = False
        
        output.processing_time = time.time() - start_time
        
        logger.info(
            f"Пайплайн завершён: успех={output.success}, "
            f"время={output.processing_time:.2f}с"
        )
        
        return output
    
    def _extract_text(self, file_path: Path) -> str:
        """Извлечь текст из файла."""
        suffix = file_path.suffix.lower()

        if suffix in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp']:
            # Изображение
            result = self.ocr_engine.recognize(str(file_path))
            return result.text

        elif suffix == '.pdf':
            # PDF
            parser = PDFParser()
            doc = parser.parse(str(file_path))

            if doc.has_text:
                return doc.full_text
            else:
                # Скан - используем OCR
                logger.info("PDF без текста, используем OCR")
                ocr = MedicalDocumentOCR()
                results = ocr.process_pdf(str(file_path))
                return ocr.get_full_text(results)

        elif suffix in ['.xls', '.xlsx']:
            # Excel
            parser = ExcelParser()
            return parser.to_text(str(file_path))

        elif suffix == '.docx':
            # DOCX
            logger.info(f"Чтение DOCX файла: {file_path}")
            from ..ocr.pdf_parser import extract_text_from_docx
            text = extract_text_from_docx(str(file_path))
            if not text:
                logger.warning("Не удалось извлечь текст из DOCX")
            return text

        else:
            raise ValueError(f"Неподдерживаемый формат: {suffix}")
    
    def _auto_detect_query(self, text: str) -> str:
        """
        Автоматически определить поисковый запрос из текста.
        
        Args:
            text: Анонимизированный текст.
            
        Returns:
            Поисковый запрос.
        """
        # Ищем упоминания заболеваний
        cancer_keywords = [
            'рак молочной железы', 'рак лёгкого', 'меланома',
            'лимфома', 'лейкоз', 'рак желудка', 'рак кишечника'
        ]
        
        text_lower = text.lower()
        for keyword in cancer_keywords:
            if keyword in text_lower:
                return f"лечение {keyword}"
        
        # По умолчанию
        return "онкология лечение рекомендации"
    
    def _build_user_prompt(
        self,
        text: str,
        rag_context: str,
        query: Optional[str] = None
    ) -> str:
        """
        Построить пользовательский промпт.
        
        Args:
            text: Анонимизированный текст пациента.
            rag_context: Контекст из RAG.
            query: Запрос.
            
        Returns:
            Промпт.
        """
        if self.mode == 'doctor':
            return create_doctor_prompt(
                patient_id="анонимизированный",
                clinical_data=text[:2000],  # Ограничиваем размер
                examination_results="",
                current_treatment=text[:2000],
                guideline_excerpts=rag_context
            )
        else:
            return create_patient_prompt(
                patient_data=text[:1000],
                diagnosis=text[:500],
                treatment_plan=text[:1000]
            )
    
    def process_doctor(
        self,
        file_path: Union[str, Path],
        query: Optional[str] = None
    ) -> PipelineOutput:
        """Обработать файл для врача."""
        return self.process(file_path, mode='doctor', query=query)
    
    def process_patient(
        self,
        file_path: Union[str, Path],
        query: Optional[str] = None
    ) -> PipelineOutput:
        """Обработать файл для пациента."""
        return self.process(file_path, mode='patient', query=query)
    
    def cleanup_temp(self) -> int:
        """
        Очистить временные файлы.
        
        Returns:
            Количество удалённых файлов.
        """
        deleted = 0
        for file_path in self.temp_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
                deleted += 1
        logger.info(f"Очищено {deleted} временных файлов")
        return deleted


class PipelineBuilder:
    """Билдер для создания пайплайна с конфигурацией."""
    
    def __init__(self):
        """Инициализация билдера."""
        self._config: Optional[YandexGPTConfig] = None
        self._data_dir = "knowledge_base_data/minzdrav"
        self._temp_dir = "temp"
        self._anonymization_strict = True
    
    def with_yandex_config(
        self,
        config: Union[YandexGPTConfig, Dict[str, Any]]
    ) -> 'PipelineBuilder':
        """Установить конфигурацию Yandex."""
        if isinstance(config, dict):
            self._config = YandexGPTConfig(**config)
        else:
            self._config = config
        return self
    
    def with_yandex_credentials(
        self,
        folder_id: str,
        iam_token: Optional[str] = None,
        service_account_key: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> 'PipelineBuilder':
        """Установить учётные данные Yandex."""
        self._config = YandexGPTConfig(
            folder_id=folder_id,
            iam_token=iam_token,
            service_account_key_path=service_account_key,
            api_key=api_key
        )
        return self
    
    def with_data_dir(self, path: str) -> 'PipelineBuilder':
        """Установить директорию данных."""
        self._data_dir = path
        return self
    
    def with_temp_dir(self, path: str) -> 'PipelineBuilder':
        """Установить временную директорию."""
        self._temp_dir = path
        return self
    
    def with_strict_anonymization(self, strict: bool = True) -> 'PipelineBuilder':
        """Установить строгость анонимизации."""
        self._anonymization_strict = strict
        return self
    
    def build(self) -> OncologyPipeline:
        """
        Построить пайплайн.
        
        Returns:
            OncologyPipeline.
        """
        if self._config is None:
            raise ValueError("Требуется конфигурация Yandex Cloud")
        
        return OncologyPipeline(
            yandex_config=self._config,
            data_dir=self._data_dir,
            temp_dir=self._temp_dir,
            anonymization_strict=self._anonymization_strict
        )


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------

def create_pipeline_from_env() -> OncologyPipeline:
    """
    Создать пайплайн из переменных окружения.
    
    Returns:
        OncologyPipeline.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    folder_id = os.getenv('YC_FOLDER_ID', '')
    iam_token = os.getenv('YC_IAM_TOKEN')
    sa_key = os.getenv('YC_SERVICE_ACCOUNT_KEY')
    
    builder = PipelineBuilder()
    builder.with_yandex_credentials(
        folder_id=folder_id,
        iam_token=iam_token,
        service_account_key=sa_key
    )
    
    return builder.build()


def process_file_quick(
    file_path: str,
    mode: str = 'doctor'
) -> PipelineOutput:
    """
    Быстрая обработка файла (требует настроенного окружения).
    
    Args:
        file_path: Путь к файлу.
        mode: Режим.
        
    Returns:
        PipelineOutput.
    """
    pipeline = create_pipeline_from_env()
    return pipeline.process(file_path, mode=mode)
