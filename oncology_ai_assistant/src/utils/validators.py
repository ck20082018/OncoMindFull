"""
=============================================================================
VALIDATORS.PY - Валидаторы данных и файлов
=============================================================================
Модуль содержит функции для валидации:
- Типов и размеров файлов
- Переменных окружения
- Конфигурационных данных
- Медицинских данных (базовая валидация)
=============================================================================
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from pathlib import Path
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Константы
# -----------------------------------------------------------------------------
# Максимальные размеры файлов (в байтах)
MAX_FILE_SIZE_IMAGE = 20 * 1024 * 1024  # 20 MB для изображений
MAX_FILE_SIZE_PDF = 50 * 1024 * 1024    # 50 MB для PDF
MAX_FILE_SIZE_EXCEL = 30 * 1024 * 1024  # 30 MB для Excel

# Разрешённые расширения
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp'}
ALLOWED_PDF_EXTENSIONS = {'.pdf'}
ALLOWED_EXCEL_EXTENSIONS = {'.xls', '.xlsx'}
ALLOWED_WORD_EXTENSIONS = {'.doc', '.docx'}

ALL_ALLOWED_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS |
    ALLOWED_PDF_EXTENSIONS |
    ALLOWED_EXCEL_EXTENSIONS |
    ALLOWED_WORD_EXTENSIONS
)


# -----------------------------------------------------------------------------
# Перечисления
# -----------------------------------------------------------------------------
class FileType(Enum):
    """Тип файла."""
    IMAGE = "image"
    PDF = "pdf"
    EXCEL = "excel"
    WORD = "word"
    UNKNOWN = "unknown"


class ValidationResult(Enum):
    """Результат валидации."""
    VALID = "valid"
    INVALID_TYPE = "invalid_type"
    INVALID_SIZE = "invalid_size"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    CORRUPTED = "corrupted"
    EMPTY = "empty"


# -----------------------------------------------------------------------------
# Валидация файлов
# -----------------------------------------------------------------------------
def get_file_extension(filename: str) -> str:
    """
    Получить расширение файла в нижнем регистре.
    
    Args:
        filename: Имя файла.
        
    Returns:
        Расширение в нижнем регистре.
    """
    return Path(filename).suffix.lower()


def get_file_type(filename: str) -> FileType:
    """
    Определить тип файла по расширению.
    
    Args:
        filename: Имя файла.
        
    Returns:
        FileType.
    """
    ext = get_file_extension(filename)
    
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return FileType.IMAGE
    elif ext in ALLOWED_PDF_EXTENSIONS:
        return FileType.PDF
    elif ext in ALLOWED_EXCEL_EXTENSIONS:
        return FileType.EXCEL
    elif ext in ALLOWED_WORD_EXTENSIONS:
        return FileType.WORD
    else:
        return FileType.UNKNOWN


def validate_file_extension(
    filename: str,
    allowed_extensions: Optional[Set[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Проверить расширение файла.
    
    Args:
        filename: Имя файла.
        allowed_extensions: Разрешённые расширения.
        
    Returns:
        Кортеж (успех, сообщение об ошибке).
    """
    if not filename:
        return False, "Имя файла пустое"
    
    ext = get_file_extension(filename)
    
    if not ext:
        return False, "У файла нет расширения"
    
    if allowed_extensions is None:
        allowed_extensions = ALL_ALLOWED_EXTENSIONS
    
    if ext not in allowed_extensions:
        return False, f"Неподдерживаемый формат: {ext}. Разрешены: {allowed_extensions}"
    
    return True, None


def validate_file_size(
    file_size: Optional[int],
    max_size: int = MAX_FILE_SIZE_PDF
) -> Optional[str]:
    """
    Проверить размер файла.
    
    Args:
        file_size: Размер файла в байтах.
        max_size: Максимальный размер.
        
    Returns:
        Сообщение об ошибке или None.
    """
    if file_size is None:
        return "Размер файла не определён"
    
    if file_size <= 0:
        return "Размер файла должен быть больше 0"
    
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return f"Файл слишком большой. Максимум: {max_mb:.1f} MB"
    
    return None


def validate_file_type(
    filename: str,
    allowed_extensions: Optional[Set[str]] = None
) -> Optional[str]:
    """
    Проверить тип файла (расширение).
    
    Args:
        filename: Имя файла.
        allowed_extensions: Разрешённые расширения.
        
    Returns:
        Сообщение об ошибке или None.
    """
    _, error = validate_file_extension(filename, allowed_extensions)
    return error


def validate_file_exists(file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
    """
    Проверить существование файла.
    
    Args:
        file_path: Путь к файлу.
        
    Returns:
        Кортеж (существует, сообщение об ошибке).
    """
    path = Path(file_path)
    
    if not path.exists():
        return False, f"Файл не найден: {file_path}"
    
    if not path.is_file():
        return False, f"Это не файл: {file_path}"
    
    return True, None


def validate_file_readable(file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
    """
    Проверить доступность файла для чтения.
    
    Args:
        file_path: Путь к файлу.
        
    Returns:
        Кортеж (доступен, сообщение об ошибке).
    """
    exists, error = validate_file_exists(file_path)
    if not exists:
        return False, error
    
    try:
        with open(file_path, 'rb') as f:
            f.read(1)
        return True, None
    except PermissionError:
        return False, f"Нет прав на чтение: {file_path}"
    except Exception as e:
        return False, f"Ошибка чтения: {e}"


def validate_file_not_empty(file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
    """
    Проверить что файл не пустой.
    
    Args:
        file_path: Путь к файлу.
        
    Returns:
        Кортеж (не пустой, сообщение об ошибке).
    """
    exists, error = validate_file_exists(file_path)
    if not exists:
        return False, error
    
    size = Path(file_path).stat().st_size
    if size == 0:
        return False, "Файл пустой"
    
    return True, None


def validate_image_file(file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
    """
    Проверить файл изображения.
    
    Args:
        file_path: Путь к файлу.
        
    Returns:
        Кортеж (валиден, сообщение об ошибке).
    """
    # Проверка расширения
    valid, error = validate_file_extension(
        str(file_path),
        ALLOWED_IMAGE_EXTENSIONS
    )
    if not valid:
        return False, error
    
    # Проверка существования
    valid, error = validate_file_exists(file_path)
    if not valid:
        return False, error
    
    # Проверка размера
    size = Path(file_path).stat().st_size
    error = validate_file_size(size, MAX_FILE_SIZE_IMAGE)
    if error:
        return False, error
    
    # Проверка что не пустой
    valid, error = validate_file_not_empty(file_path)
    if not valid:
        return False, error
    
    return True, None


def validate_pdf_file(file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
    """
    Проверить PDF файл.
    
    Args:
        file_path: Путь к файлу.
        
    Returns:
        Кортеж (валиден, сообщение об ошибке).
    """
    valid, error = validate_file_extension(str(file_path), ALLOWED_PDF_EXTENSIONS)
    if not valid:
        return False, error
    
    valid, error = validate_file_exists(file_path)
    if not valid:
        return False, error
    
    size = Path(file_path).stat().st_size
    error = validate_file_size(size, MAX_FILE_SIZE_PDF)
    if error:
        return False, error
    
    # Проверка PDF заголовка
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                return False, "Файл не является корректным PDF"
    except Exception as e:
        return False, f"Ошибка чтения PDF: {e}"
    
    return True, None


# -----------------------------------------------------------------------------
# Валидация переменных окружения
# -----------------------------------------------------------------------------
def validate_yandex_cloud_config() -> Tuple[bool, List[str]]:
    """
    Проверить конфигурацию Yandex Cloud.
    
    Returns:
        Кортеж (валидно, список ошибок).
    """
    errors = []
    
    folder_id = os.getenv('YC_FOLDER_ID')
    if not folder_id:
        errors.append("Не указан YC_FOLDER_ID")
    elif not re.match(r'^b1[a-z0-9]{28}$', folder_id):
        errors.append("Некорректный формат YC_FOLDER_ID")
    
    # Проверяем наличие хотя бы одного метода аутентификации
    auth_methods = [
        ('YC_IAM_TOKEN', os.getenv('YC_IAM_TOKEN')),
        ('YC_SERVICE_ACCOUNT_KEY', os.getenv('YC_SERVICE_ACCOUNT_KEY')),
        ('YC_API_KEY', os.getenv('YC_API_KEY')),
    ]
    
    has_auth = any(value for _, value in auth_methods)
    if not has_auth:
        errors.append(
            "Не указан метод аутентификации: "
            "YC_IAM_TOKEN, YC_SERVICE_ACCOUNT_KEY или YC_API_KEY"
        )
    
    # Проверяем путь к ключу если указан
    sa_key_path = os.getenv('YC_SERVICE_ACCOUNT_KEY')
    if sa_key_path:
        if not Path(sa_key_path).exists():
            errors.append(f"Файл ключа не найден: {sa_key_path}")
    
    return len(errors) == 0, errors


def validate_env_variables() -> Tuple[bool, Dict[str, Any]]:
    """
    Проверить все переменные окружения.
    
    Returns:
        Кортеж (валидно, детали).
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'config': {}
    }
    
    # Yandex Cloud
    yc_valid, yc_errors = validate_yandex_cloud_config()
    if not yc_valid:
        result['valid'] = False
        result['errors'].extend(yc_errors)
    else:
        result['config']['yandex_cloud'] = True
    
    # Проверка путей
    required_dirs = [
        'knowledge_base_data/minzdrav',
        'temp',
        'logs'
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            result['warnings'].append(f"Директория не найдена: {dir_path}")
        elif not path.is_dir():
            result['errors'].append(f"Это не директория: {dir_path}")
            result['valid'] = False
    
    return result['valid'], result


# -----------------------------------------------------------------------------
# Валидация конфигурации
# -----------------------------------------------------------------------------
def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Проверить конфигурацию приложения.
    
    Args:
        config: Словарь конфигурации.
        
    Returns:
        Кортеж (валидно, список ошибок).
    """
    errors = []
    
    # Проверка обязательных секций
    required_sections = ['app', 'server', 'llm']
    for section in required_sections:
        if section not in config:
            errors.append(f"Отсутствует секция конфигурации: {section}")
    
    # Проверка LLM конфигурации
    if 'llm' in config:
        llm = config['llm']
        
        if 'model_name' not in llm:
            errors.append("Не указано llm.model_name")
        
        if 'temperature' in llm:
            temp = llm['temperature']
            if not (0 <= temp <= 1):
                errors.append(f"temperature должен быть от 0 до 1, получено: {temp}")
        
        if 'max_tokens' in llm:
            tokens = llm['max_tokens']
            if not (100 <= tokens <= 32000):
                errors.append(f"max_tokens должен быть от 100 до 32000")
    
    # Проверка безопасности
    if 'security' in config:
        sec = config['security']
        if sec.get('require_anonymization') is False:
            errors.append("Требовать анонимизацию должно быть включено")
    
    return len(errors) == 0, errors


# -----------------------------------------------------------------------------
# Валидация медицинских данных
# -----------------------------------------------------------------------------
def validate_tnm_stage(tnm: str) -> Tuple[bool, Optional[str]]:
    """
    Проверить стадию TNM.
    
    Args:
        tnm: Стадия в формате TNM.
        
    Returns:
        Кортеж (валидно, сообщение об ошибке).
    """
    if not tnm:
        return False, "Стадия TNM пустая"
    
    # Простая проверка формата
    pattern = r'^[Tt][0-4isx]\s*[Nn][0-3x]\s*[Mm][01x]$'
    if not re.match(pattern, tnm):
        # Допускаем более сложные форматы
        if not re.match(r'^[Tt].*[Nn].*[Mm]', tnm, re.IGNORECASE):
            return False, f"Некорректный формат TNM: {tnm}"
    
    return True, None


def validate_date(date_str: str, format: str = "%Y-%m-%d") -> Tuple[bool, Optional[str]]:
    """
    Проверить дату.
    
    Args:
        date_str: Строка даты.
        format: Ожидаемый формат.
        
    Returns:
        Кортеж (валидно, сообщение об ошибке).
    """
    if not date_str:
        return False, "Дата пустая"
    
    try:
        datetime.strptime(date_str, format)
        return True, None
    except ValueError:
        return False, f"Некорректный формат даты: {date_str}. Ожидается: {format}"


def validate_percentage(value: Any) -> Tuple[bool, Optional[str]]:
    """
    Проверить процентное значение.
    
    Args:
        value: Значение.
        
    Returns:
        Кортеж (валидно, сообщение об ошибке).
    """
    try:
        num = float(value)
        if not (0 <= num <= 100):
            return False, f"Процент должен быть от 0 до 100, получено: {num}"
        return True, None
    except (TypeError, ValueError):
        return False, f"Некорректное процентное значение: {value}"


# -----------------------------------------------------------------------------
# Валидация JSON ответов
# -----------------------------------------------------------------------------
def validate_doctor_response_json(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Проверить JSON ответ для врача.
    
    Args:
        data: Данные ответа.
        
    Returns:
        Кортеж (валидно, список ошибок).
    """
    errors = []
    
    # Обязательные поля
    required_fields = [
        'verdict', 'confidence_score', 'diagnosis_analysis',
        'treatment_analysis', 'guideline_references', 'risks',
        'additional_tests_needed', 'summary'
    ]
    
    for field in required_fields:
        if field not in data:
            errors.append(f"Отсутствует поле: {field}")
    
    # Проверка verdict
    valid_verdicts = [
        'соответствует', 'частично_соответствует',
        'не_соответствует', 'недостаточно_данных'
    ]
    if 'verdict' in data and data['verdict'] not in valid_verdicts:
        errors.append(f"Некорректный verdict: {data['verdict']}")
    
    # Проверка confidence_score
    if 'confidence_score' in data:
        score = data['confidence_score']
        if not isinstance(score, (int, float)) or not (0 <= score <= 1):
            errors.append("confidence_score должен быть от 0 до 1")
    
    return len(errors) == 0, errors


def validate_patient_response_json(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Проверить JSON ответ для пациента.
    
    Args:
        data: Данные ответа.
        
    Returns:
        Кортеж (валидно, список ошибок).
    """
    errors = []
    
    required_fields = [
        'diagnosis_explained', 'stage_explained', 'treatment_plan',
        'medications', 'side_effects', 'next_steps',
        'questions_for_doctor', 'support_message'
    ]
    
    for field in required_fields:
        if field not in data:
            errors.append(f"Отсутствует поле: {field}")
    
    return len(errors) == 0, errors


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------
def format_size(size_bytes: int) -> str:
    """
    Форматировать размер в человекочитаемый вид.
    
    Args:
        size_bytes: Размер в байтах.
        
    Returns:
        Форматированная строка.
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def create_validation_report(
    file_path: str,
    file_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Создать отчёт о валидации файла.
    
    Args:
        file_path: Путь к файлу.
        file_size: Размер файла.
        
    Returns:
        Отчёт о валидации.
    """
    report = {
        'file_path': file_path,
        'file_name': Path(file_path).name,
        'extension': get_file_extension(file_path),
        'file_type': get_file_type(file_path).value,
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Проверка существования
    exists, error = validate_file_exists(file_path)
    if not exists:
        report['valid'] = False
        report['errors'].append(error)
        return report
    
    # Размер
    if file_size is None:
        file_size = Path(file_path).stat().st_size
    
    report['file_size'] = file_size
    report['file_size_formatted'] = format_size(file_size)
    
    # Проверка размера
    max_size = MAX_FILE_SIZE_PDF if get_file_type(file_path) == FileType.PDF else MAX_FILE_SIZE_IMAGE
    error = validate_file_size(file_size, max_size)
    if error:
        report['valid'] = False
        report['errors'].append(error)
    
    return report
