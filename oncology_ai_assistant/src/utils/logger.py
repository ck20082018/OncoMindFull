"""
=============================================================================
LOGGER.PY - Настройка логирования
=============================================================================
Модуль для настройки логирования приложения с учётом безопасности:
- Логирование в файл и консоль
- Санитизация чувствительных данных в логах
- Ротация логов
- Разные уровни логирования для разных модулей

ИСПРАВЛЕНИЯ БЕЗОПАСНОСТИ:
- Добавлена санитизация API ключей и IAM токенов
- Улучшена санитизация чувствительных данных
"""

import logging
import sys
import re
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
# ИСПРАВЛЕНИЕ: Добавлены паттерны для токенов
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
    (r'\+7\s*\d{3}\s*\d{3}-\d{2}-\d{2}', '[REDACTED_PHONE]'),
    (r'8\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2}', '[REDACTED_PHONE]'),
    # Email
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[REDACTED_EMAIL]'),
    
    # ИСПРАВЛЕНИЕ: Токены и ключи доступа
    # Yandex API Key
    (r'Api-Key\s+[A-Za-z0-9_-]{20,}', 'Api-Key [REDACTED_API_KEY]'),
    (r'API_KEY[\'"]?\s*[:=]\s*[\'"]?[A-Za-z0-9_-]{20,}[\'"]?', 'API_KEY=[REDACTED_API_KEY]'),
    
    # IAM токен
    (r't1\.[A-Za-z0-9._-]{20,}', '[REDACTED_IAM_TOKEN]'),
    (r'iam_token[\'"]?\s*[:=]\s*[\'"]?[A-Za-z0-9._-]{20,}[\'"]?', 'iam_token=[REDACTED_IAM_TOKEN]'),
    
    # Сервисный ключ
    (r'sa_key[\'"]?\s*[:=]\s*[\'"]?[A-Za-z0-9._/-]+[\'"]?', 'sa_key=[REDACTED_SA_KEY]'),
    
    # Bearer токен
    (r'Bearer\s+[A-Za-z0-9._-]{20,}', 'Bearer [REDACTED_TOKEN]'),
    
    # Authorization header
    (r'Authorization[\'"]?\s*[:=]\s*[\'"]?[A-Za-z0-9._-]{20,}[\'"]?', 'Authorization=[REDACTED_AUTH]'),
    
    # Секретные ключи (общий паттерн)
    (r'secret[_-]?key[\'"]?\s*[:=]\s*[\'"]?[A-Za-z0-9_-]{16,}[\'"]?', 'secret_key=[REDACTED_SECRET]'),
    
    # Пароли в логах
    (r'password[\'"]?\s*[:=]\s*[\'"]?[^\'"\s]{4,}[\'"]?', 'password=[REDACTED_PASSWORD]'),
    (r'passwd[\'"]?\s*[:=]\s*[\'"]?[^\'"\s]+[\'"]?', 'passwd=[REDACTED]'),
]


def sanitize_message(message: str) -> str:
    """
    Удалить чувствительные данные из сообщения.
    
    ИСПОЛЬЗОВАНИЕ: Вызывать перед записью в логи.

    Args:
        message: Исходное сообщение.

    Returns:
        Санитизированное сообщение.
    """
    sanitized = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

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

    # Консольный вывод с санитизацией
    if sanitize:
        logger.add(
            sys.stderr,
            format=DEFAULT_LOG_FORMAT,
            level=level,
            colorize=True,
            filter=lambda record: sanitize_message(record["message"])
        )
    else:
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
        enqueue=True,  # Асинхронная запись
        filter=lambda record: sanitize_message(record["message"]) if sanitize else True
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

    # Файловый обработчик с санитизацией
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
            # ИСПРАВЛЕНИЕ: Санитизация сообщения об ошибке
            error_msg = sanitize_message(f"{exc_type.__name__}: {exc_val}")
            self.logger.error(
                f"Ошибка: {self.operation} - {error_msg}"
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
            # ИСПРАВЛЕНИЕ: Санитизация аргументов
            safe_args = sanitize_message(str(args[:3]))
            logger.info(f"Начало: {operation} ({func.__name__})({safe_args})")
            start_time = datetime.now()

            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"Завершено: {operation} ({duration:.2f}с)")
                return result
            except Exception as e:
                # ИСПРАВЛЕНИЕ: Санитизация ошибки
                logger.error(f"Ошибка: {operation} - {sanitize_message(str(e))}")
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
        # ИСПРАВЛЕНИЕ: Санитизация аргументов
        safe_args = sanitize_message(str(args[:3]))
        logger.debug(f"Вызов {func.__name__}({safe_args})")
        return func(*args, **kwargs)

    return wrapper


# -----------------------------------------------------------------------------
# Функции для безопасного логирования
# -----------------------------------------------------------------------------

def log_safe(logger: logging.Logger, level: int, message: str, **kwargs):
    """
    Безопасное логирование с санитизацией.
    
    Args:
        logger: Logger.
        level: Уровень логирования.
        message: Сообщение.
        **kwargs: Дополнительные аргументы.
    """
    safe_message = sanitize_message(message)
    safe_kwargs = {k: sanitize_message(str(v)) if isinstance(v, str) else v for k, v in kwargs.items()}
    logger.log(level, safe_message, **safe_kwargs)


def log_api_request(logger: logging.Logger, endpoint: str, method: str, 
                    headers: dict, body: Optional[str] = None):
    """
    Безопасное логирование API запроса.
    
    Args:
        logger: Logger.
        endpoint: URL endpoint.
        method: HTTP метод.
        headers: Заголовки.
        body: Тело запроса.
    """
    # Санитизация заголовков
    safe_headers = {}
    for key, value in headers.items():
        if key.lower() in ['authorization', 'api-key', 'x-api-key', 'cookie']:
            safe_headers[key] = '[REDACTED]'
        else:
            safe_headers[key] = sanitize_message(str(value))
    
    logger.info(f"API Request: {method} {endpoint}")
    logger.debug(f"Headers: {safe_headers}")
    
    if body:
        safe_body = sanitize_message(body)
        logger.debug(f"Body: {safe_body}")


def log_api_response(logger: logging.Logger, endpoint: str, status: int, 
                     body: Optional[str] = None):
    """
    Безопасное логирование API ответа.
    
    Args:
        logger: Logger.
        endpoint: URL endpoint.
        status: HTTP статус.
        body: Тело ответа.
    """
    logger.info(f"API Response: {endpoint} - {status}")
    
    if body:
        safe_body = sanitize_message(body)
        logger.debug(f"Body: {safe_body}")
