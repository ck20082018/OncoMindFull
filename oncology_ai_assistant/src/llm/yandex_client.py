"""
=============================================================================
YANDEX_CLIENT.PY - Клиент для работы с YandexGPT через Yandex Cloud API
=============================================================================
Модуль предоставляет интерфейс для взаимодействия с языковой моделью
YandexGPT Pro через gRPC API Yandex Cloud.

Основные функции:
- Аутентификация через сервисный аккаунт/IAM-токен
- Отправка запросов с системными промптами
- Поддержка JSON режима ответа
- Обработка ошибок и повторные попытки
- Валидация ответов
=============================================================================
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import grpc
import yaml
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# Импорты Yandex Cloud SDK
try:
    from yandexcloud import SDK
    from yandex.cloud.ai.llm.v1.llm_service import LlmService
    from yandex.cloud.ai.llm.v1.llm_service_pb2 import (
        CompletionRequest,
        CompletionResponse,
    )
    from yandex.cloud.ai.llm.v1.generation_pb2 import (
        GenerationOptions,
        TextGenerationOptions,
    )
    YANDEX_SDK_AVAILABLE = True
except ImportError:
    YANDEX_SDK_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Yandex Cloud SDK не установлен. Установите: pip install yandexcloud")


logger = logging.getLogger(__name__)


@dataclass
class YandexGPTConfig:
    """Конфигурация подключения к YandexGPT."""
    folder_id: str
    iam_token: Optional[str] = None
    service_account_key_path: Optional[str] = None
    api_key: Optional[str] = None
    model_name: str = "yandexgpt-pro"
    model_version: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60
    endpoint: str = "llm.api.cloud.yandex.net:443"
    
    def __post_init__(self):
        """Валидация конфигурации после инициализации."""
        if not self.folder_id:
            raise ValueError("folder_id обязателен для подключения к Yandex Cloud")
        
        # Проверяем наличие хотя бы одного способа аутентификации
        auth_methods = [
            self.iam_token,
            self.service_account_key_path,
            self.api_key
        ]
        if not any(auth_methods):
            raise ValueError(
                "Требуется хотя бы один способ аутентификации: "
                "iam_token, service_account_key_path или api_key"
            )


@dataclass
class LLMResponse:
    """Ответ от языковой модели."""
    text: str
    usage: Dict[str, int] = field(default_factory=dict)
    model_version: str = ""
    finish_reason: str = ""
    raw_response: Optional[Any] = None
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def input_tokens(self) -> int:
        """Количество токенов во входном запросе."""
        return self.usage.get('input_tokens', 0)
    
    @property
    def output_tokens(self) -> int:
        """Количество токенов в ответе."""
        return self.usage.get('output_tokens', 0)
    
    @property
    def total_tokens(self) -> int:
        """Общее количество использованных токенов."""
        return self.input_tokens + self.output_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'text': self.text,
            'usage': self.usage,
            'model_version': self.model_version,
            'finish_reason': self.finish_reason,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp.isoformat()
        }
    
    def parse_json(self) -> Optional[Dict[str, Any]]:
        """
        Попытаться распарсить ответ как JSON.
        
        Returns:
            Распарсенный JSON или None если не удалось.
        """
        try:
            # Пытаемся найти JSON в тексте (может быть обёрнут в markdown)
            text = self.text.strip()
            
            # Удаляем markdown code blocks если есть
            if text.startswith('```'):
                lines = text.split('\n')
                # Находим первую и последнюю строки с ```
                start_idx = 0
                end_idx = len(lines) - 1
                
                for i, line in enumerate(lines):
                    if line.startswith('```json') or line.startswith('```'):
                        if start_idx == 0:
                            start_idx = i + 1
                        else:
                            end_idx = i
                            break
                
                text = '\n'.join(lines[start_idx:end_idx]).strip()
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Не удалось распарсить JSON: {e}")
            return None


class YandexGPTClient:
    """
    Клиент для работы с YandexGPT.
    
    Использование:
        config = YandexGPTConfig(folder_id="b1c...", iam_token="t1...")
        client = YandexGPTClient(config)
        response = client.complete("Привет!", system_prompt="Ты помощник.")
    """
    
    def __init__(self, config: Union[YandexGPTConfig, Dict[str, Any]]):
        """
        Инициализация клиента.
        
        Args:
            config: Конфигурация подключения.
        """
        if not YANDEX_SDK_AVAILABLE:
            raise ImportError(
                "Yandex Cloud SDK не установлен. "
                "Установите: pip install yandexcloud"
            )
        
        # Преобразуем словарь в конфиг если нужно
        if isinstance(config, dict):
            config = YandexGPTConfig(**config)
        
        self.config = config
        self._sdk: Optional[SDK] = None
        self._llm_service: Optional[LlmService] = None
        
        # Инициализируем подключение
        self._initialize()
    
    def _initialize(self) -> None:
        """Инициализация SDK и сервиса."""
        logger.info(f"Инициализация подключения к Yandex Cloud (folder_id: {self.config.folder_id})")
        
        # Создаём SDK с нужным методом аутентификации
        if self.config.service_account_key_path:
            # Аутентификация через сервисный аккаунт
            key_path = Path(self.config.service_account_key_path)
            if not key_path.exists():
                raise FileNotFoundError(
                    f"Файл ключа сервисного аккаунта не найден: {key_path}"
                )
            
            logger.info(f"Аутентификация через сервисный аккаунт: {key_path}")
            self._sdk = SDK(service_account_key=str(key_path))
            
        elif self.config.iam_token:
            # Аутентификация через IAM-токен
            logger.info("Аутентификация через IAM-токен")
            self._sdk = SDK(iam_token=self.config.iam_token)
            
        elif self.config.api_key:
            # Аутентификация через API-ключ
            logger.info("Аутентификация через API-ключ")
            self._sdk = SDK(api_key=self.config.api_key)
        
        # Получаем сервис LLM
        self._llm_service = self._sdk.client(LlmService)
        
        logger.info("Подключение к Yandex Cloud успешно инициализировано")
    
    @property
    def sdk(self) -> SDK:
        """Получить SDK (инициализирует если нужно)."""
        if self._sdk is None:
            self._initialize()
        return self._sdk
    
    @property
    def llm_service(self) -> LlmService:
        """Получить сервис LLM."""
        if self._llm_service is None:
            self._initialize()
        return self._llm_service
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((grpc.RpcError, ConnectionError))
    )
    def complete(
        self,
        user_text: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Отправить запрос к YandexGPT и получить ответ.
        
        Args:
            user_text: Текст запроса от пользователя.
            system_prompt: Системный промпт (роль модели).
            temperature: Температура генерации (переопределяет конфиг).
            max_tokens: Максимум токенов в ответе (переопределяет конфиг).
            json_mode: Если True, модель будет стараться выдавать JSON.
            
        Returns:
            LLMResponse с ответом модели.
            
        Raises:
            grpc.RpcError: При ошибке подключения к API.
            ValueError: При некорректных параметрах.
        """
        start_time = time.time()
        
        # Параметры генерации
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        logger.info(
            f"Отправка запроса к YandexGPT (model: {self.config.model_name}, "
            f"temp: {temp}, max_tokens: {tokens})"
        )
        
        # Формируем сообщения
        messages = []
        
        if system_prompt:
            messages.append({
                'role': 'system',
                'text': system_prompt
            })
        
        messages.append({
            'role': 'user',
            'text': user_text
        })
        
        # Добавляем инструкцию для JSON режима
        if json_mode:
            messages.append({
                'role': 'system',
                'text': (
                    "Важно: ответ должен быть в формате строгого JSON. "
                    "Не используйте markdown, код или другие обёртки. "
                    "Только чистый JSON."
                )
            })
        
        try:
            # Создаём запрос
            request = CompletionRequest(
                model_uri=f"gpt://{self.config.folder_id}/{self.config.model_name}",
                completion_options=CompletionOptions(
                    temperature=temp,
                    max_tokens=tokens,
                ),
                messages=messages
            )
            
            # Отправляем запрос
            response = self.llm_service.Completion(request)
            
            # Обрабатываем ответ
            result = self._process_response(response, start_time)
            
            logger.info(
                f"Запрос завершён успешно. Токены: {result.total_tokens}, "
                f"время: {result.processing_time:.2f}с"
            )
            
            return result
            
        except grpc.RpcError as e:
            logger.error(f"gRPC ошибка при запросе к YandexGPT: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе к YandexGPT: {e}")
            raise
    
    def _process_response(self, response: CompletionResponse, start_time: float) -> LLMResponse:
        """
        Обработать ответ от API.
        
        Args:
            response: Сырой ответ от API.
            start_time: Время начала запроса.
            
        Returns:
            LLMResponse.
        """
        # Извлекаем текст из ответа
        text = ""
        if response.result and response.result.alternatives:
            # Берём первую альтернативу
            alternative = response.result.alternatives[0]
            text = alternative.message.content
        
        # Информация об использовании токенов
        usage = {}
        if response.result and response.result.usage:
            usage = {
                'input_tokens': response.result.usage.input_text_tokens,
                'output_tokens': response.result.usage.cached_tokens + 
                                response.result.usage.generated_tokens
            }
        
        # Версия модели
        model_version = ""
        if response.result and response.result.model_version:
            model_version = response.result.model_version
        
        # Причина завершения
        finish_reason = ""
        if response.result and response.result.alternatives:
            alternative = response.result.alternatives[0]
            finish_reason = alternative.status.name if alternative.status else ""
        
        return LLMResponse(
            text=text,
            usage=usage,
            model_version=model_version,
            finish_reason=finish_reason,
            raw_response=response,
            processing_time=time.time() - start_time
        )
    
    def complete_json(
        self,
        user_text: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Отправить запрос и получить ответ в формате JSON.
        
        Args:
            user_text: Текст запроса.
            system_prompt: Системный промпт.
            schema: Ожидаемая JSON-схема (для документации).
            **kwargs: Дополнительные параметры для complete().
            
        Returns:
            Распарсенный JSON или None.
        """
        response = self.complete(
            user_text=user_text,
            system_prompt=system_prompt,
            json_mode=True,
            **kwargs
        )
        
        return response.parse_json()
    
    def health_check(self) -> bool:
        """
        Проверить доступность сервиса.
        
        Returns:
            True если сервис доступен.
        """
        try:
            # Простой тестовый запрос
            response = self.complete(
                user_text="Ответь одним словом: тест успешен?",
                temperature=0.1,
                max_tokens=10
            )
            return response.text.strip().lower() in ['да', 'yes', 'успешен']
        except Exception as e:
            logger.error(f"Health check не пройден: {e}")
            return False
    
    def get_token_count(self, text: str) -> int:
        """
        Оценить количество токенов в тексте.
        
        Примечание: Это приблизительная оценка. Точное количество
        можно получить только через API Yandex Cloud.
        
        Args:
            text: Текст для оценки.
            
        Returns:
            Примерное количество токенов.
        """
        # Грубая оценка: ~4 символа на токен для русского языка
        return len(text) // 4


def load_config_from_yaml(config_path: str) -> YandexGPTConfig:
    """
    Загрузить конфигурацию из YAML файла.
    
    Args:
        config_path: Путь к YAML файлу.
        
    Returns:
        YandexGPTConfig.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    # Извлекаем настройки Yandex Cloud
    yc_config = config_data.get('yandex_cloud', {})
    
    return YandexGPTConfig(
        folder_id=yc_config.get('folder_id', ''),
        iam_token=yc_config.get('auth', {}).get('iam_token'),
        service_account_key_path=yc_config.get('auth', {}).get('service_account_key_path'),
        api_key=yc_config.get('auth', {}).get('api_key'),
        model_name=yc_config.get('model', {}).get('name', 'yandexgpt-pro'),
        model_version=yc_config.get('model', {}).get('version'),
        temperature=yc_config.get('model', {}).get('temperature', 0.1),
        max_tokens=yc_config.get('model', {}).get('max_tokens', 4000),
        timeout=yc_config.get('request', {}).get('timeout', 60),
        endpoint=yc_config.get('endpoint', {}).get('llm_api', 'llm.api.cloud.yandex.net:443')
    )


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------
def create_client_from_env() -> YandexGPTClient:
    """
    Создать клиент из переменных окружения.
    
    Ожидаемые переменные:
    - YC_FOLDER_ID: ID каталога
    - YC_IAM_TOKEN: IAM-токен
    - YC_SERVICE_ACCOUNT_KEY: Путь к ключу сервисного аккаунта
    - YC_API_KEY: API-ключ
    
    Returns:
        Настроенный YandexGPTClient.
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    folder_id = os.getenv('YC_FOLDER_ID', '')
    iam_token = os.getenv('YC_IAM_TOKEN')
    sa_key_path = os.getenv('YC_SERVICE_ACCOUNT_KEY')
    api_key = os.getenv('YC_API_KEY')
    
    config = YandexGPTConfig(
        folder_id=folder_id,
        iam_token=iam_token,
        service_account_key_path=sa_key_path,
        api_key=api_key
    )
    
    return YandexGPTClient(config)
