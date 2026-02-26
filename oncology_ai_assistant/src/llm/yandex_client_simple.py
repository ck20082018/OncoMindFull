"""
Упрощённый клиент YandexGPT через REST API
"""

import json
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


@dataclass
class YandexGPTConfig:
    """Конфигурация подключения к YandexGPT."""
    folder_id: str
    iam_token: Optional[str] = None
    service_account_key_path: Optional[str] = None
    model_name: str = "yandexgpt-lite"
    temperature: float = 0.1
    max_tokens: int = 4000
    
    def get_iam_token(self) -> str:
        """Получить IAM токен."""
        if self.iam_token:
            return self.iam_token
        
        if self.service_account_key_path:
            with open(self.service_account_key_path, 'r') as f:
                key_data = json.load(f)
            
            import jwt
            now = int(time.time())
            payload = {
                'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                'iss': key_data['id'],
                'iat': now,
                'exp': now + 3600
            }
            token = jwt.encode(
                payload,
                key_data['private_key'],
                algorithm='PS256',
                headers={'kid': key_data['id']}
            )
            
            response = requests.post(
                'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                json={'jwt': token}
            )
            response.raise_for_status()
            return response.json()['iamToken']
        
        raise ValueError("Не удалось получить IAM токен")


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
    """Клиент для работы с YandexGPT через REST API."""
    
    def __init__(self, config):
        self.config = config
        self._iam_token = None
        self._initialized = False
        logger.info(f"Инициализация YandexGPTClient (folder_id: {config.folder_id})")
    
    def _get_iam_token(self) -> str:
        """Получить IAM токен."""
        if self._iam_token:
            return self._iam_token
        
        self._iam_token = self.config.get_iam_token()
        return self._iam_token
    
    def health_check(self) -> bool:
        """Проверка работоспособности LLM."""
        try:
            # Просто проверяем, что можем получить токен
            self._get_iam_token()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
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
        
        # Формируем сообщения
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'text': system_prompt})
        messages.append({'role': 'user', 'text': user_text})
        
        if json_mode:
            messages.append({
                'role': 'system',
                'text': "Ответ должен быть в формате строгого JSON."
            })
        
        # Отправляем запрос
        iam_token = self._get_iam_token()
        
        response = requests.post(
            'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {iam_token}',
                'x-folder-id': self.config.folder_id
            },
            json={
                'modelUri': f"gpt://{self.config.folder_id}/{self.config.model_name}",
                'completionOptions': {
                    'temperature': temp,
                    'maxTokens': tokens
                },
                'messages': messages
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
