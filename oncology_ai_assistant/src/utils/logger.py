"""
=============================================================================
LOGGER.PY - Настройка логирования
=============================================================================
Модуль для настройки логирования приложения с учётом безопасности:
- Логирование в файл и консоль
- Санитизация чувствительных данных в логах
- Ротация логов
- Разные уровни логирования для разных модулей
=============================================================================
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    logger = None


# -----------------------------------------------------------------------------
# Конфигурация логирования
# -----------------------------------------------------------------------------
DEFAULT_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

FILE_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)


# -----------------------------------------------------------------------------
# Список чувствительных паттернов для санитизации
# -----------------------------------------------------------------------------
SENSITIVE_PATTERNS = [
    # Паспортные данные
    (r'\d{4}\s*\d{6}', '[REDACTED_PASSPORT]'),
    # Полис ОМС
    (r'\d{16}', '[REDACTED_POLICY]'),
    # СНИЛС
    (r'\d{3}-\d{3}-\d{3} \d{2}', '[REDACTED_SNILS]'),
    # Телефоны
    (r'\+7\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2}', '[REDACTED_PHONE]'),
    # Email
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[REDACTED_EMAIL]'),
]


def sanitize_message(message: str) -> str:
    """
    Удалить чувствительные данные из сообщения.
    
    Args:
        message: Исходное сообщение.
        
    Returns:
        Санитизированное сообщение.
    """
    import re
    
    sanitized = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    
    return sanitized


class SanitizingFilter(logging.Filter):
    """Фильтр для санитизации логов."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Санитизировать сообщение перед логированием."""
        if isinstance(record.msg, str):
            record.msg = sanitize_message(record.msg)
        if record.args:
            record.args = tuple(
                sanitize_message(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


def setup_loguru_logging(
    log_file: str = "logs/app.log",
    level: str = "INFO",
    rotation: str = "100 MB",
    retention: str = "30 days",
    sanitize: bool = True
) -> None:
    """
    Настроить логирование через loguru.
    
    Args:
        log_file: Путь к файлу логов.
        level: Уровень логирования.
        rotation: Размер ротации файла.
        retention: Срок хранения логов.
        sanitize: Санитизировать чувствительные данные.
    """
    if not LOGURU_AVAILABLE:
        return
    
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Консольный вывод
    logger.add(
        sys.stderr,
        format=DEFAULT_LOG_FORMAT,
        level=level,
        colorize=True
    )
    
    # Файловый вывод
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        str(log_path),
        format=FILE_LOG_FORMAT,
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True  # Асинхронная запись
    )
    
    logger.info("Логирование loguru настроено")


def setup_standard_logging(
    log_file: str = "logs/app.log",
    level: int = logging.INFO,
    sanitize: bool = True
) -> logging.Logger:
    """
    Настроить стандартное логирование Python.
    
    Args:
        log_file: Путь к файлу логов.
        level: Уровень логирования.
        sanitize: Санитизировать чувствительные данные.
        
    Returns:
        Настроенный logger.
    """
    # Создаём корневой logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Очищаем существующие обработчики
    root_logger.handlers.clear()
    
    # Форматтер
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Файловый обработчик
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    if sanitize:
        file_handler.addFilter(SanitizingFilter())
    
    root_logger.addHandler(file_handler)
    
    # Логгер приложения
    app_logger = logging.getLogger("oncology_ai")
    app_logger.setLevel(level)
    
    app_logger.info("Стандартное логирование настроено")
    
    return app_logger


def setup_logging(
    log_file: str = "logs/app.log",
    level: str = "INFO",
    backend: str = "auto",
    sanitize: bool = True
) -> logging.Logger:
    """
    Настроить логирование приложения.
    
    Args:
        log_file: Путь к файлу логов.
        level: Уровень логирования.
        backend: 'loguru', 'standard', или 'auto'.
        sanitize: Санитизировать чувствительные данные.
        
    Returns:
        Logger.
    """
    # Конвертируем уровень
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if backend == "auto":
        backend = "loguru" if LOGURU_AVAILABLE else "standard"
    
    if backend == "loguru" and LOGURU_AVAILABLE:
        setup_loguru_logging(
            log_file=log_file,
            level=level,
            sanitize=sanitize
        )
        # Возвращаем стандартный logger для совместимости
        return logging.getLogger("oncology_ai")
    else:
        return setup_standard_logging(
            log_file=log_file,
            level=log_level,
            sanitize=sanitize
        )


def get_logger(name: str) -> logging.Logger:
    """
    Получить logger для модуля.
    
    Args:
        name: Имя модуля.
        
    Returns:
        Logger.
    """
    return logging.getLogger(f"oncology_ai.{name}")


class LogContext:
    """Контекстный менеджер для логирования выполнения."""
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        level: int = logging.INFO
    ):
        """
        Инициализация контекста.
        
        Args:
            logger: Logger для использования.
            operation: Название операции.
            level: Уровень логирования.
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        """Начало операции."""
        self.start_time = datetime.now()
        self.logger.log(self.level, f"Начало: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Завершение операции."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.log(
                self.level,
                f"Завершено: {self.operation} ({duration:.2f}с)"
            )
        else:
            self.logger.error(
                f"Ошибка: {self.operation} - {exc_type.__name__}: {exc_val}"
            )
        
        return False  # Не подавляем исключения


def log_operation(logger: logging.Logger, operation: str):
    """
    Декоратор для логирования выполнения функции.
    
    Args:
        logger: Logger.
        operation: Название операции.
        
    Returns:
        Декоратор.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(f"Начало: {operation} ({func.__name__})")
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"Завершено: {operation} ({duration:.2f}с)")
                return result
            except Exception as e:
                logger.error(f"Ошибка: {operation} - {e}")
                raise
        
        return wrapper
    return decorator


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------

def log_execution_time(func):
    """Декоратор для логирования времени выполнения."""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = datetime.now()
        result = func(*args, **kwargs)
        duration = (datetime.now() - start).total_seconds()
        logging.getLogger(func.__module__).info(
            f"{func.__name__} выполнено за {duration:.2f}с"
        )
        return result
    
    return wrapper


def log_function_call(func):
    """Декоратор для логирования вызовов функции."""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        args_str = ', '.join(
            [repr(a) for a in args[:3]] +  # Только первые 3 аргумента
            [f'{k}={repr(v)}' for k, v in list(kwargs.items())[:3]]
        )
        logger.debug(f"Вызов {func.__name__}({args_str})")
        return func(*args, **kwargs)
    
    return wrapper
