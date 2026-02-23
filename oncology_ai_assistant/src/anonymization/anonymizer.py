"""
=============================================================================
ANONYMIZER.PY - Модуль анонимизации персональных данных пациентов
=============================================================================
Модуль выполняет обнаружение и замену персональной информации (PII) в
медицинских текстах перед отправкой в языковую модель.

Основные функции:
- Поиск PII с помощью regex-паттернов
- Замена на плейсхолдеры ([ФИО], [ПАСПОРТ], [ПОЛИС] и т.д.)
- Ведение журнала замен для возможного восстановления
- Проверка качества анонимизации
=============================================================================
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .patterns import PATTERNS, PatternConfig, get_all_patterns


logger = logging.getLogger(__name__)


@dataclass
class AnonymizationMatch:
    """Представляет найденное совпадение PII."""
    pattern_name: str
    original_text: str
    placeholder: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0


@dataclass
class AnonymizationResult:
    """Результат анонимизации текста."""
    original_text: str
    anonymized_text: str
    matches: List[AnonymizationMatch] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    processed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def matches_count(self) -> int:
        """Количество найденных PII."""
        return len(self.matches)
    
    @property
    def pii_types(self) -> List[str]:
        """Уникальные типы найденных PII."""
        return list(set(m.pattern_name for m in self.matches))
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация результата в словарь."""
        return {
            'original_text': self.original_text,
            'anonymized_text': self.anonymized_text,
            'matches_count': self.matches_count,
            'pii_types': self.pii_types,
            'matches': [
                {
                    'type': m.pattern_name,
                    'original': m.original_text,
                    'placeholder': m.placeholder,
                    'position': (m.start_pos, m.end_pos)
                }
                for m in self.matches
            ],
            'success': self.success,
            'processed_at': self.processed_at.isoformat()
        }


class Anonymizer:
    """
    Класс для анонимизации персональных данных в медицинских текстах.
    
    Использование:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize(text)
        print(result.anonymized_text)
    """
    
    def __init__(
        self,
        patterns: Optional[Dict[str, PatternConfig]] = None,
        use_placeholders: bool = True,
        strict_mode: bool = True,
        custom_placeholders: Optional[Dict[str, str]] = None
    ):
        """
        Инициализация анонимайзера.
        
        Args:
            patterns: Словарь паттернов для использования. Если None, используются
                     паттерны по умолчанию из patterns.py
            use_placeholders: Если True, заменять PII на плейсхолдеры.
                             Если False, удалять PII полностью.
            strict_mode: Если True, поднимать исключение при неудачной анонимизации.
            custom_placeholders: Пользовательские плейсхолдеры для типов PII.
        """
        self.patterns = patterns or get_all_patterns()
        self.use_placeholders = use_placeholders
        self.strict_mode = strict_mode
        self.custom_placeholders = custom_placeholders or {}
        
        # Статистика анонимизации
        self._stats = {
            'total_processed': 0,
            'total_matches': 0,
            'matches_by_type': {}
        }
    
    def anonymize(self, text: str) -> AnonymizationResult:
        """
        Анонимизировать текст, удаляя все персональные данные.
        
        Args:
            text: Исходный текст для анонимизации.
            
        Returns:
            AnonymizationResult с анонимизированным текстом и информацией о заменах.
        """
        if not text or not isinstance(text, str):
            return AnonymizationResult(
                original_text=text or '',
                anonymized_text=text or '',
                success=False,
                error_message='Пустой или некорректный текст'
            )
        
        matches: List[AnonymizationMatch] = []
        anonymized_text = text
        
        # Сортируем паттерны по приоритету (более специфичные первыми)
        priority_order = [
            'passport', 'passport_issue', 'policy_oms', 'snils', 'inn',
            'medical_record', 'case_history', 'birth_date', 'full_name',
            'full_name_initials', 'address', 'address_short', 'phone', 'email'
        ]
        
        sorted_patterns = sorted(
            self.patterns.items(),
            key=lambda x: (
                priority_order.index(x[0]) if x[0] in priority_order else len(priority_order)
            )
        )
        
        # Применяем паттерны по очереди
        for pattern_name, pattern_config in sorted_patterns:
            matches_found = self._apply_pattern(
                text=anonymized_text,
                pattern_config=pattern_config,
                previous_matches=matches
            )
            matches.extend(matches_found)
            
            # Применяем замены к тексту
            for match in matches_found:
                anonymized_text = (
                    anonymized_text[:match.start_pos] +
                    match.placeholder +
                    anonymized_text[match.end_pos:]
                )
        
        # Обновляем статистику
        self._update_stats(matches)
        
        result = AnonymizationResult(
            original_text=text,
            anonymized_text=anonymized_text,
            matches=matches
        )
        
        # Проверка в строгом режиме
        if self.strict_mode and not result.success:
            raise ValueError(f"Анонимизация не выполнена: {result.error_message}")
        
        logger.info(
            f"Анонимизация завершена: найдено {result.matches_count} PII, "
            f"типы: {result.pii_types}"
        )
        
        return result
    
    def _apply_pattern(
        self,
        text: str,
        pattern_config: PatternConfig,
        previous_matches: List[AnonymizationMatch]
    ) -> List[AnonymizationMatch]:
        """
        Применить один паттерн к тексту.
        
        Args:
            text: Текст для обработки.
            pattern_config: Конфигурация паттерна.
            previous_matches: Ранее найденные совпадения (для исключения перекрытий).
            
        Returns:
            Список новых совпадений.
        """
        matches = []
        
        # Получаем плейсхолдер (кастомный или из паттерна)
        placeholder = self.custom_placeholders.get(
            pattern_config.name,
            pattern_config.placeholder
        )
        
        # Ищем все совпадения
        for match_iter in pattern_config.pattern.finditer(text):
            start_pos = match_iter.start()
            end_pos = match_iter.end()
            original_text = match_iter.group(0)
            
            # Проверяем перекрытия с предыдущими совпадениями
            if self._has_overlap(start_pos, end_pos, previous_matches):
                logger.debug(f"Пропущено перекрытие: {original_text[:20]}...")
                continue
            
            # Создаём объект совпадения
            anon_match = AnonymizationMatch(
                pattern_name=pattern_config.name,
                original_text=original_text,
                placeholder=placeholder,
                start_pos=start_pos,
                end_pos=end_pos
            )
            matches.append(anon_match)
        
        return matches
    
    def _has_overlap(
        self,
        start_pos: int,
        end_pos: int,
        existing_matches: List[AnonymizationMatch]
    ) -> bool:
        """
        Проверить наличие перекрытий с существующими совпадениями.
        
        Args:
            start_pos: Начало нового совпадения.
            end_pos: Конец нового совпадения.
            existing_matches: Список существующих совпадений.
            
        Returns:
            True если есть перекрытие.
        """
        for existing in existing_matches:
            # Проверка на любое перекрытие
            if not (end_pos <= existing.start_pos or start_pos >= existing.end_pos):
                return True
        return False
    
    def _update_stats(self, matches: List[AnonymizationMatch]) -> None:
        """Обновить статистику анонимизации."""
        self._stats['total_processed'] += 1
        self._stats['total_matches'] += len(matches)
        
        for match in matches:
            pattern_name = match.pattern_name
            if pattern_name not in self._stats['matches_by_type']:
                self._stats['matches_by_type'][pattern_name] = 0
            self._stats['matches_by_type'][pattern_name] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику анонимизации.
        
        Returns:
            Словарь со статистикой.
        """
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Сбросить статистику."""
        self._stats = {
            'total_processed': 0,
            'total_matches': 0,
            'matches_by_type': {}
        }
    
    def validate_anonymization(self, text: str) -> Tuple[bool, List[str]]:
        """
        Проверить текст на наличие неанонимизированных PII.
        
        Args:
            text: Текст для проверки.
            
        Returns:
            Кортеж (успех, список проблем).
        """
        problems = []
        
        # Проверяем каждым паттерном
        for pattern_name, pattern_config in self.patterns.items():
            matches = list(pattern_config.pattern.finditer(text))
            if matches:
                for match in matches:
                    # Игнорируем уже заменённые плейсхолдеры
                    if match.group(0).startswith('[') and match.group(0).endswith(']'):
                        continue
                    problems.append(
                        f"Найдено неанонимизированное {pattern_name}: "
                        f"'{match.group(0)[:30]}...'"
                    )
        
        is_valid = len(problems) == 0
        return is_valid, problems


class AnonymizerFactory:
    """Фабрика для создания анонимайзеров с предустановленными конфигурациями."""
    
    @staticmethod
    def create_default() -> Anonymizer:
        """Создать анонимайзер с настройками по умолчанию."""
        return Anonymizer()
    
    @staticmethod
    def create_strict() -> Anonymizer:
        """Создать строгий анонимайзер (поднимает исключения при ошибках)."""
        return Anonymizer(strict_mode=True)
    
    @staticmethod
    def create_minimal() -> Anonymizer:
        """
        Создать анонимайзер только с основными паттернами.
        
        Используется для быстрой обработки когда важны только:
        - ФИО
        - Паспорт
        - Полис
        - СНИЛС
        """
        from .patterns import get_pattern
        
        minimal_patterns = {}
        for name in ['full_name', 'full_name_initials', 'passport', 'policy_oms', 'snils']:
            try:
                minimal_patterns[name] = get_pattern(name)
            except KeyError:
                pass
        
        return Anonymizer(patterns=minimal_patterns, strict_mode=False)
    
    @staticmethod
    def create_custom(pattern_names: List[str]) -> Anonymizer:
        """
        Создать анонимайзер с выбранными паттернами.
        
        Args:
            pattern_names: Список имён паттернов для использования.
            
        Returns:
            Настроенный анонимайзер.
        """
        from .patterns import get_pattern
        
        custom_patterns = {}
        for name in pattern_names:
            try:
                custom_patterns[name] = get_pattern(name)
            except KeyError:
                logger.warning(f"Паттерн '{name}' не найден, пропускается")
        
        return Anonymizer(patterns=custom_patterns)


# -----------------------------------------------------------------------------
# Утилитные функции для быстрого использования
# -----------------------------------------------------------------------------
def anonymize_text(text: str, strict: bool = False) -> str:
    """
    Быстрая анонимизация текста.
    
    Args:
        text: Текст для анонимизации.
        strict: Строгий режим (исключение при ошибках).
        
    Returns:
        Анонимизированный текст.
    """
    anonymizer = Anonymizer(strict_mode=strict)
    result = anonymizer.anonymize(text)
    return result.anonymized_text


def validate_text(text: str) -> Tuple[bool, List[str]]:
    """
    Проверить текст на наличие PII.
    
    Args:
        text: Текст для проверки.
        
    Returns:
        Кортеж (безопасен, список проблем).
    """
    anonymizer = Anonymizer()
    return anonymizer.validate_anonymization(text)
