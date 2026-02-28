"""
Упрощённый клиент YandexGPT через новый API (ai.api.cloud.yandex.net)
"""

import requests
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class YandexGPTConfig:
    """Конфигурация подключения к YandexGPT через API Key."""
    api_key: str
    folder_id: str
    model_name: str = "yandexgpt/rc"
    temperature: float = 0.3
    max_tokens: int = 4000
    
    @property
    def model_uri(self) -> str:
        return f"gpt://{self.folder_id}/{self.model_name}"


@dataclass
class LLMResponse:
    """Ответ от языковой модели."""
    text: str
    usage: Dict[str, int] = field(default_factory=dict)
    model_version: str = ""
    finish_reason: str = ""
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def input_tokens(self) -> int:
        return self.usage.get('input_tokens', 0)
    
    @property
    def output_tokens(self) -> int:
        return self.usage.get('output_tokens', 0)
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'usage': self.usage,
            'model_version': self.model_version,
            'processing_time': self.processing_time
        }
    
    def parse_json(self) -> Optional[Dict[str, Any]]:
        try:
            import json
            text = self.text.strip()
            if text.startswith('```'):
                lines = text.split('\n')
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
        except json.JSONDecodeError:
            logger.error("Не удалось распарсить JSON")
            return None


class YandexGPTClient:
    """Клиент для работы с YandexGPT через новый API."""
    
    def __init__(self, config: YandexGPTConfig):
        self.config = config
        self.base_url = "https://ai.api.cloud.yandex.net/v1/responses"
        logger.info(f"Инициализация YandexGPTClient (folder_id: {config.folder_id})")
    
    def health_check(self) -> bool:
        """Проверка работоспособности."""
        try:
            response = requests.post(
                self.base_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Api-Key {self.config.api_key}',
                    'OpenAI-Project': self.config.folder_id
                },
                json={
                    "model": self.config.model_uri,
                    "instructions": "Test",
                    "input": "Test",
                    "temperature": 0.3,
                    "max_output_tokens": 10
                },
                timeout=10
            )
            return response.status_code in [200, 400]  # 400 OK для теста
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def complete(
        self,
        user_text: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> LLMResponse:
        """Отправить запрос к YandexGPT."""
        start_time = time.time()
        
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        logger.info(f"Отправка запроса к YandexGPT (temp: {temp}, max_tokens: {tokens})")
        
        # Формируем запрос
        instructions = system_prompt or "Ты полезный ассистент."
        
        response = requests.post(
            self.base_url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Api-Key {self.config.api_key}',
                'OpenAI-Project': self.config.folder_id
            },
            json={
                "model": self.config.model_uri,
                "instructions": instructions,
                "input": user_text,
                "temperature": temp,
                "max_output_tokens": tokens
            },
            timeout=60
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Обрабатываем ответ
        result = data.get('result', {})
        text = result.get('alternatives', [{}])[0].get('message', {}).get('text', '')
        usage = result.get('usage', {})
        
        llm_response = LLMResponse(
            text=text,
            usage={
                'input_tokens': int(usage.get('inputTextTokens', 0)),
                'output_tokens': int(usage.get('completionTokens', 0))
            },
            model_version=result.get('modelVersion', ''),
            finish_reason=result.get('alternatives', [{}])[0].get('status', ''),
            processing_time=time.time() - start_time
        )
        
        logger.info(f"Получен ответ ({llm_response.total_tokens} токенов, {llm_response.processing_time:.2f}s)")
        return llm_response
