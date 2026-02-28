"""
=============================================================================
JSON_VALIDATOR.PY - Валидация и исправление JSON ответов от LLM
=============================================================================
Модуль для проверки, исправления и валидации JSON-ответов от языковой модели.

Основные функции:
- Извлечение JSON из текста (удаление markdown, лишнего текста)
- Валидация структуры JSON по схеме
- Попытки исправления некорректного JSON
- Проверка обязательных полей
=============================================================================
"""

import json
import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, ValidationError, create_model


logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Результат валидации."""
    VALID = "valid"
    INVALID_JSON = "invalid_json"
    INVALID_SCHEMA = "invalid_schema"
    MISSING_FIELDS = "missing_fields"
    FIXED = "fixed"


@dataclass
class ValidationResultDetail:
    """Детали валидации JSON."""
    is_valid: bool
    status: ValidationResult
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fixed_json: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'is_valid': self.is_valid,
            'status': self.status.value,
            'data': self.data,
            'errors': self.errors,
            'warnings': self.warnings,
            'fixed_json': self.fixed_json
        }


# -----------------------------------------------------------------------------
# Схемы ответов (Pydantic модели)
# -----------------------------------------------------------------------------

class DoctorVerdictSchema(BaseModel):
    """Схема ответа для врача."""
    verdict: Optional[str] = None
    confidence_score: Optional[float] = None
    diagnosis_analysis: Optional[Dict[str, Any]] = None
    treatment_analysis: Optional[Dict[str, Any]] = None
    guideline_references: Optional[List[Dict[str, Any]]] = None
    risks: Optional[List[Dict[str, Any]]] = None
    additional_tests_needed: Optional[List[str]] = None
    summary: Optional[str] = None
    disclaimer: Optional[str] = None
    # Дополнительные поля для YandexGPT (новый API)
    analysis: Optional[str] = None
    recommendations: Optional[str] = None
    compliance: Optional[bool] = None


class PatientExplanationSchema(BaseModel):
    """Схема ответа для пациента."""
    diagnosis_explained: str
    stage_explained: str
    treatment_plan: Dict[str, str]
    medications: List[Dict[str, str]]
    side_effects: List[Dict[str, str]]
    next_steps: List[str]
    questions_for_doctor: List[str]
    support_message: str


class ExtractionSchema(BaseModel):
    """Схема для извлечённых данных."""
    patient: Dict[str, Any]
    diagnosis: Dict[str, Any]
    histology: Dict[str, Any]
    biomarkers: Dict[str, Any]
    treatment_history: List[Dict[str, Any]]
    current_status: Dict[str, Any]
    lab_results: List[Dict[str, Any]]
    imaging_results: List[Dict[str, Any]]


# Словарь схем
SCHEMAS = {
    'doctor': DoctorVerdictSchema,
    'patient': PatientExplanationSchema,
    'extraction': ExtractionSchema
}


class JSONValidator:
    """
    Валидатор JSON ответов от LLM.
    
    Использование:
        validator = JSONValidator()
        result = validator.validate(json_text, schema_type='doctor')
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Инициализация валидатора.
        
        Args:
            strict_mode: Если True, отклонять JSON с предупреждениями.
        """
        self.strict_mode = strict_mode
        self._fix_attempts = 0
        self._max_fix_attempts = 3
    
    def validate(
        self,
        json_text: str,
        schema_type: Optional[str] = None,
        custom_schema: Optional[type[BaseModel]] = None
    ) -> ValidationResultDetail:
        """
        Валидировать JSON текст.
        
        Args:
            json_text: Текст для валидации.
            schema_type: Тип схемы ('doctor', 'patient', 'extraction').
            custom_schema: Пользовательская Pydantic схема.
            
        Returns:
            ValidationResultDetail с результатами.
        """
        result = ValidationResultDetail(
            is_valid=False,
            status=ValidationResult.INVALID_JSON
        )
        
        # Шаг 1: Извлечь JSON из текста
        cleaned_json = self._extract_json(json_text)
        if not cleaned_json:
            result.errors.append("Не удалось извлечь JSON из текста")
            return result
        
        # Шаг 2: Попытаться распарсить JSON
        parsed_data = self._parse_json(cleaned_json)
        if parsed_data is None:
            # Пытаемся исправить
            fixed_json = self._try_fix_json(cleaned_json)
            if fixed_json:
                parsed_data = self._parse_json(fixed_json)
                if parsed_data:
                    result.status = ValidationResult.FIXED
                    result.fixed_json = fixed_json
                    result.warnings.append("JSON был исправлен автоматически")
        
        if parsed_data is None:
            result.errors.append("Не удалось распарсить JSON")
            return result
        
        result.data = parsed_data
        
        # Шаг 3: Валидация по схеме если указана
        if schema_type or custom_schema:
            schema = custom_schema or SCHEMAS.get(schema_type)
            if schema:
                schema_result = self._validate_schema(parsed_data, schema)
                result.errors.extend(schema_result['errors'])
                result.warnings.extend(schema_result['warnings'])
                
                if schema_result['is_valid']:
                    result.status = ValidationResult.VALID
                    result.is_valid = True
                else:
                    result.status = ValidationResult.INVALID_SCHEMA
                    result.is_valid = not self.strict_mode or len(schema_result['errors']) == 0
            else:
                # Схема не найдена, считаем валидным если JSON распаршен
                result.status = ValidationResult.VALID
                result.is_valid = True
        else:
            # Без схемы
            result.status = ValidationResult.VALID
            result.is_valid = True
        
        return result
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        Извлечь JSON из текста (удалить markdown, лишний текст).

        Args:
            text: Исходный текст.

        Returns:
            Очищенный JSON или None.
        """
        if not text:
            return None

        text = text.strip()

        # Удаляем markdown code blocks (```json ... ``` или ``` ... ```)
        if text.startswith('```'):
            # Находим содержимое между ```
            pattern = r'```(?:json)?\s*(.*?)\s*```'
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
            else:
                # Удаляем только первые и последние ```
                lines = text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                text = '\n'.join(lines).strip()

        # Пытаемся найти JSON по скобкам
        text = text.strip()

        # Если текст начинается с { и заканчивается на }
        if text.startswith('{') and text.endswith('}'):
            return text

        # Ищем первую { и последнюю }
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1

        if start_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx]

        return text
    
    def _parse_json(self, json_text: str) -> Optional[Dict[str, Any]]:
        """
        Распарсить JSON.
        
        Args:
            json_text: Текст JSON.
            
        Returns:
            Распарсенный словарь или None.
        """
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.debug(f"Ошибка парсинга JSON: {e}")
            return None
    
    def _try_fix_json(self, json_text: str) -> Optional[str]:
        """
        Попытаться исправить некорректный JSON.
        
        Args:
            json_text: Некорректный JSON.
            
        Returns:
            Исправленный JSON или None.
        """
        self._fix_attempts = 0
        return self._recursive_fix(json_text)
    
    def _recursive_fix(self, json_text: str) -> Optional[str]:
        """Рекурсивное исправление JSON."""
        if self._fix_attempts >= self._max_fix_attempts:
            return None
        
        self._fix_attempts += 1
        fixed = json_text
        
        # Исправление 1: Недостающие закрывающие скобки
        open_braces = fixed.count('{')
        close_braces = fixed.count('}')
        if open_braces > close_braces:
            fixed = fixed + '}' * (open_braces - close_braces)
        
        # Исправление 2: Недостающие закрывающие квадратные скобки
        open_brackets = fixed.count('[')
        close_brackets = fixed.count(']')
        if open_brackets > close_brackets:
            # Находим место для вставки (перед последней })
            last_brace = fixed.rfind('}')
            if last_brace != -1:
                missing = ']' * (open_brackets - close_brackets)
                fixed = fixed[:last_brace] + missing + fixed[last_brace:]
            else:
                fixed = fixed + ']' * (open_brackets - close_brackets)
        
        # Исправление 3: Заменить одинарные кавычки на двойные
        # (только если это не внутри строк)
        if "'" in fixed:
            try:
                # Простая замена если JSON использует одинарные кавычки
                fixed = fixed.replace("'", '"')
            except:
                pass
        
        # Исправление 4: Удалить trailing commas
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)
        
        # Исправление 5: Добавить кавычки к ключам без кавычек
        fixed = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', fixed)
        
        # Проверяем получилось ли
        try:
            json.loads(fixed)
            logger.info(f"JSON исправлен после {self._fix_attempts} попыток")
            return fixed
        except json.JSONDecodeError:
            # Пытаемся ещё раз
            if fixed != json_text:
                return self._recursive_fix(fixed)
            return None
    
    def _validate_schema(
        self,
        data: Dict[str, Any],
        schema: type[BaseModel]
    ) -> Dict[str, Any]:
        """
        Валидировать данные по Pydantic схеме.
        
        Args:
            data: Данные для валидации.
            schema: Pydantic модель.
            
        Returns:
            Словарь с результатами валидации.
        """
        result = {
            'is_valid': False,
            'errors': [],
            'warnings': []
        }
        
        try:
            schema(**data)
            result['is_valid'] = True
        except ValidationError as e:
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                
                # Определяем тип проблемы
                if error['type'] in ('missing', 'value_error.missing'):
                    result['errors'].append(f"Отсутствует обязательное поле: {field}")
                elif error['type'] in ('type_error', 'type_error.integer', 'type_error.float'):
                    result['errors'].append(f"Неверный тип поля {field}: {msg}")
                else:
                    result['warnings'].append(f"Поле {field}: {msg}")
        
        return result
    
    def validate_and_get(
        self,
        json_text: str,
        schema_type: str,
        default: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Валидировать и вернуть данные.
        
        Args:
            json_text: Текст JSON.
            schema_type: Тип схемы.
            default: Значение по умолчанию при ошибке.
            
        Returns:
            Кортеж (успех, данные).
        """
        result = self.validate(json_text, schema_type=schema_type)
        
        if result.is_valid and result.data:
            return True, result.data
        
        return False, default


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Извлечь JSON из текста.
    
    Args:
        text: Исходный текст.
        
    Returns:
        Распарсенный JSON или None.
    """
    validator = JSONValidator()
    result = validator.validate(text)
    return result.data


def validate_doctor_response(json_text: str) -> ValidationResultDetail:
    """
    Валидировать ответ для врача.
    
    Args:
        json_text: Текст ответа.
        
    Returns:
        Результат валидации.
    """
    validator = JSONValidator()
    return validator.validate(json_text, schema_type='doctor')


def validate_patient_response(json_text: str) -> ValidationResultDetail:
    """
    Валидировать ответ для пациента.
    
    Args:
        json_text: Текст ответа.
        
    Returns:
        Результат валидации.
    """
    validator = JSONValidator()
    return validator.validate(json_text, schema_type='patient')


def fix_broken_json(json_text: str) -> Optional[str]:
    """
    Попытаться исправить сломанный JSON.
    
    Args:
        json_text: Некорректный JSON.
        
    Returns:
        Исправленный JSON или None.
    """
    validator = JSONValidator()
    return validator._try_fix_json(json_text)
