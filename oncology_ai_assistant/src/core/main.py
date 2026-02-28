"""
=============================================================================
MAIN.PY - Точка входа FastAPI приложения
=============================================================================
Основной модуль приложения, предоставляющий REST API для:
- Загрузки медицинских документов
- Проверки лечения на соответствие рекомендациям
- Получения объяснений для пациентов
- Управления базой знаний
=============================================================================
"""
from dotenv import load_dotenv
load_dotenv()

import logging
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .pipeline import OncologyPipeline, PipelineBuilder, PipelineOutput
from ..llm.yandex_client_new import YandexGPTConfig, YandexGPTClient
from ..knowledge_base.guideline_manager import GuidelineManager
from ..knowledge_base.guideline_updater import GuidelineUpdater
from ..utils.logger import setup_logging
from ..utils.validators import validate_file_type, validate_file_size


# -----------------------------------------------------------------------------
# Конфигурация логирования
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Pydantic модели для API
# -----------------------------------------------------------------------------
class HealthResponse(BaseModel):
    """Ответ health check."""
    status: str
    version: str
    components: Dict[str, bool]


class AnalysisRequest(BaseModel):
    """Запрос на анализ."""
    mode: str = Field(default='doctor', description='doctor или patient')
    query: Optional[str] = Field(default=None, description='Дополнительный запрос')


class AnalysisResponse(BaseModel):
    """Ответ анализа."""
    success: bool
    mode: str
    data: Optional[Dict[str, Any]]
    processing_time: float
    anonymization_info: Optional[Dict[str, Any]]
    error_message: Optional[str]


class GuidelineSearchRequest(BaseModel):
    """Запрос поиска рекомендаций."""
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class GuidelineSearchResponse(BaseModel):
    """Ответ поиска рекомендаций."""
    query: str
    matches: List[Dict[str, Any]]
    total_found: int


class UpdateCheckResponse(BaseModel):
    """Ответ проверки обновлений."""
    updates_available: bool
    new_versions_count: int
    details: Dict[str, Any]


# -----------------------------------------------------------------------------
# Глобальные переменные
# -----------------------------------------------------------------------------
pipeline: Optional[OncologyPipeline] = None
guideline_manager: Optional[GuidelineManager] = None
guideline_updater: Optional[GuidelineUpdater] = None

APP_VERSION = "1.0.0"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.xls', '.xlsx'}


# -----------------------------------------------------------------------------
# Lifecycle события
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация и очистка приложения."""
    global pipeline, guideline_manager, guideline_updater

    # Инициализация
    logger.info("Инициализация приложения...")

    try:
        # Настройка логирования
        setup_logging()

        # Загрузка конфигурации из .env
        # Используем API Key вместо IAM токена
        api_key = os.getenv('YC_API_KEY', '')
        folder_id = os.getenv('YC_FOLDER_ID', '')
        
        if not api_key:
            logger.warning("YC_API_KEY не указан, используем IAM токен")
            yandex_config = YandexGPTConfig(
                folder_id=folder_id,
                api_key=""  # Будет использоваться старый клиент
            )
        else:
            yandex_config = YandexGPTConfig(
                folder_id=folder_id,
                api_key=api_key
            )

        # Создание пайплайна
        builder = PipelineBuilder()
        builder.with_yandex_config(yandex_config)
        builder.with_data_dir("knowledge_base_data/minzdrav")
        builder.with_temp_dir("temp")
        pipeline = builder.build()

        # Менеджер рекомендаций
        guideline_manager = GuidelineManager(
            data_dir="knowledge_base_data/minzdrav",
            index_dir="knowledge_base_data/index"
        )
        guideline_manager.load_local_guidelines()

        # Обновлятор рекомендаций
        guideline_updater = GuidelineUpdater(
            data_dir="knowledge_base_data/minzdrav"
        )

        logger.info("Приложение успешно инициализировано")

    except Exception as e:
        logger.error(f"Ошибка инициализации: {e}", exc_info=True)
        raise

    yield
    
    # Очистка при завершении
    logger.info("Завершение работы приложения...")
    if pipeline:
        pipeline.cleanup_temp()
    logger.info("Приложение завершено")


# -----------------------------------------------------------------------------
# Создание FastAPI приложения
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Oncology AI Assistant",
    description="AI-помощник для проверки лечения онкопациентов",
    version=APP_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/", tags=["main"])
async def root():
    """Корневой endpoint."""
    return {
        "name": "Oncology AI Assistant",
        "version": APP_VERSION,
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse, tags=["main"])
async def health_check():
    """Проверка здоровья приложения."""
    components = {
        "api": True,
        "pipeline": pipeline is not None,
        "knowledge_base": guideline_manager is not None
    }
    
    # Проверяем LLM если пайплайн создан
    if pipeline:
        try:
            components["llm"] = pipeline.llm_client.health_check()
        except:
            components["llm"] = False
    
    all_healthy = all(components.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version=APP_VERSION,
        components=components
    )


@app.post(
    "/api/analyze",
    response_model=AnalysisResponse,
    tags=["analysis"]
)
async def analyze_document(
    file: UploadFile = File(..., description="Медицинский документ"),
    mode: str = Form(default='doctor', description='doctor или patient'),
    query: Optional[str] = Form(default=None, description='Дополнительный запрос')
):
    """
    Анализ медицинского документа.
    
    - **file**: Файл для анализа (PDF, изображение, Excel)
    - **mode**: Режим анализа (doctor или patient)
    - **query**: Дополнительный запрос (опционально)
    """
    # Валидация файла
    error = validate_file_type(file.filename, ALLOWED_EXTENSIONS)
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    error = validate_file_size(file.size, MAX_FILE_SIZE)
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # Сохраняем файл во временную директорию
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    with tempfile.NamedTemporaryFile(
        dir=str(temp_dir),
        suffix=Path(file.filename or "").suffix,
        delete=False
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        temp_path = tmp.name
    
    try:
        # Запускаем пайплайн
        if pipeline is None:
            raise HTTPException(status_code=503, detail="Пайплайн не инициализирован")
        
        result = pipeline.process(
            file_path=temp_path,
            mode=mode,
            query=query
        )
        
        if not result.success:
            return AnalysisResponse(
                success=False,
                mode=mode,
                data=None,
                processing_time=result.processing_time,
                anonymization_info=None,
                error_message=result.error_message
            )
        
        return AnalysisResponse(
            success=True,
            mode=mode,
            data=result.data,
            processing_time=result.processing_time,
            anonymization_info={
                'matches_count': result.anonymization_result.matches_count if result.anonymization_result else 0,
                'pii_types': result.anonymization_result.pii_types if result.anonymization_result else []
            },
            error_message=None
        )
        
    except Exception as e:
        logger.error(f"Ошибка анализа: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Удаляем временный файл
        try:
            os.unlink(temp_path)
        except:
            pass


@app.post(
    "/api/analyze/json",
    response_model=AnalysisResponse,
    tags=["analysis"]
)
async def analyze_json(request: AnalysisRequest):
    """
    Анализ предварительно загруженного файла.
    
    Используйте этот endpoint если файл уже загружен и вы хотите
    получить анализ в определённом режиме.
    """
    # Этот endpoint требует дополнительной реализации
    # для работы с ранее загруженными файлами
    raise HTTPException(
        status_code=501,
        detail="Endpoint требует реализации кэширования файлов"
    )


@app.post(
    "/api/guidelines/search",
    response_model=GuidelineSearchResponse,
    tags=["guidelines"]
)
async def search_guidelines(request: GuidelineSearchRequest):
    """
    Поиск по клиническим рекомендациям.
    """
    if guideline_manager is None:
        raise HTTPException(status_code=503, detail="База знаний не инициализирована")
    
    results = guideline_manager.search(
        query=request.query,
        top_k=request.top_k
    )
    
    return GuidelineSearchResponse(
        query=request.query,
        matches=[m.to_dict() for m in results.matches],
        total_found=len(results.matches)
    )


@app.get(
    "/api/guidelines/list",
    tags=["guidelines"]
)
async def list_guidelines():
    """Список всех загруженных рекомендаций."""
    if guideline_manager is None:
        raise HTTPException(status_code=503, detail="База знаний не инициализирована")
    
    return {
        "guidelines": [
            doc.to_dict() for doc in guideline_manager.catalog.documents
        ],
        "total": len(guideline_manager.catalog.documents)
    }


@app.post(
    "/api/guidelines/update/check",
    response_model=UpdateCheckResponse,
    tags=["guidelines"]
)
async def check_guideline_updates():
    """Проверить наличие обновлений рекомендаций."""
    if guideline_updater is None:
        raise HTTPException(status_code=503, detail="Обновлятор не инициализирован")
    
    result = guideline_updater.check_for_updates()
    
    return UpdateCheckResponse(
        updates_available=result.updates_available,
        new_versions_count=len(result.new_versions),
        details=result.to_dict()
    )


@app.post(
    "/api/guidelines/update/download",
    tags=["guidelines"]
)
async def download_guideline_updates():
    """Скачать доступные обновления рекомендаций."""
    if guideline_updater is None:
        raise HTTPException(status_code=503, detail="Обновлятор не инициализирован")
    
    result = guideline_updater.check_for_updates()
    
    if not result.updates_available:
        return {"message": "Обновлений нет", "downloaded": []}
    
    downloaded = guideline_updater.download_updates(result.new_versions)
    
    # Переиндексируем рекомендации
    if guideline_manager and downloaded:
        guideline_manager.load_local_guidelines()
    
    return {
        "message": f"Скачано {len(downloaded)} обновлений",
        "downloaded": [str(p) for p in downloaded]
    }


@app.delete(
    "/api/cache/cleanup",
    tags=["maintenance"]
)
async def cleanup_cache():
    """Очистить кэш и временные файлы."""
    cleaned = 0
    
    if pipeline:
        cleaned = pipeline.cleanup_temp()
    
    # Очищаем директорию temp
    temp_dir = Path("temp")
    if temp_dir.exists():
        for f in temp_dir.glob("*"):
            if f.is_file():
                f.unlink()
                cleaned += 1
    
    return {"message": f"Очищено {cleaned} файлов"}


@app.get(
    "/api/stats",
    tags=["maintenance"]
)
async def get_stats():
    """Получить статистику работы."""
    stats = {
        "version": APP_VERSION,
        "guidelines_loaded": 0,
        "temp_files": 0
    }
    
    if guideline_manager:
        stats["guidelines_loaded"] = len(guideline_manager.catalog.documents)
    
    temp_dir = Path("temp")
    if temp_dir.exists():
        stats["temp_files"] = len(list(temp_dir.glob("*")))
    
    return stats


# -----------------------------------------------------------------------------
# Обработка ошибок
# -----------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Обработчик HTTP исключений."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Обработчик общих исключений."""
    logger.error(f"Необработанная ошибка: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Внутренняя ошибка сервера",
            "details": str(exc) if app.debug else None
        }
    )


# -----------------------------------------------------------------------------
# Запуск приложения
# -----------------------------------------------------------------------------
def main():
    """Точка входа для запуска через uvicorn."""
    import uvicorn
    
    uvicorn.run(
        "src.core.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
