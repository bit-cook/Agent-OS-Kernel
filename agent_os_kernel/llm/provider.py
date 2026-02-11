# -*- coding: utf-8 -*-
"""LLM Provider Base Class - 多模型 LLM 抽象层

参考 AIOS 架构设计，支持多种 LLM Provider。
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, AsyncIterator
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Provider 类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    GROQ = "groq"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    VLLM = "vllm"
    NOVITA = "novita"
    GEMINI = "gemini"
    KIMI = "kimi"
    MINIMAX = "minimax"
    QWEN = "qwen"
    AI21 = "ai21"
    CEREBRAS = "cerebras"
    CLOUDFLARE = "cloudflare"
    CUSTOM = "custom"
    
    @classmethod
    def from_string(cls, value: str) -> 'ProviderType':
        """从字符串创建 ProviderType"""
        try:
            return cls(value)
        except ValueError:
            return cls.CUSTOM


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: ProviderType
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 60.0
    max_retries: int = 3
    extra_params: Dict = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LLMConfig':
        """从字典创建配置"""
        provider = ProviderType.from_string(data.get('provider', 'openai'))
        return cls(
            provider=provider,
            model=data.get('model', 'gpt-4o'),
            api_key=data.get('api_key'),
            base_url=data.get('base_url'),
            max_tokens=data.get('max_tokens', 4096),
            temperature=data.get('temperature', 0.7),
            timeout=data.get('timeout', 60.0),
            max_retries=data.get('max_retries', 3),
            extra_params=data.get('extra_params', {})
        )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'provider': self.provider.value,
            'model': self.model,
            'api_key': self.api_key,
            'base_url': self.base_url,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'timeout': self.timeout,
            'max_retries': self.max_retries,
            'extra_params': self.extra_params
        }


@dataclass
class Message:
    """消息基类"""
    role: str
    content: str


@dataclass
class ChatMessage(Message):
    """聊天消息"""
    name: Optional[str] = None
    function_call: Optional[Dict] = None


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str = "stop"
    tool_calls: Optional[List[Dict]] = None


@dataclass
class Function:
    """函数定义"""
    name: str
    description: str
    parameters: Dict


class StreamEventType(Enum):
    """流式事件类型"""
    CONTENT = "content"
    DONE = "done"
    ERROR = "error"


@dataclass
class StreamEvent:
    """流式事件"""
    event_type: StreamEventType
    data: Dict


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""
    
    def __init__(self, config: LLMConfig):
        """初始化"""
        self.config = config
        self._initialized = False
        self._metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "failed_requests": 0
        }
        logger.info(f"LLMProvider initialized: {self.provider_name}")
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名称"""
        raise NotImplementedError("Subclasses must implement provider_name")
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        raise NotImplementedError("Subclasses must implement supported_models")
    
    @abstractmethod
    def get_config(self) -> LLMConfig:
        """获取配置"""
        return self.config
    
    async def initialize(self):
        """初始化 Provider"""
        self._initialized = True
        logger.info(f"Provider initialized: {self.provider_name}")
    
    async def shutdown(self):
        """关闭 Provider"""
        self._initialized = False
        logger.info(f"Provider shutdown: {self.provider_name}")
    
    async def embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """获取嵌入向量"""
        import random
        # 返回随机嵌入向量作为默认实现
        dim = 1536
        return [[random.uniform(-1, 1) for _ in range(dim)] for _ in texts]
    
    async def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """计算 token 数量"""
        # 简化的 token 计算：约 4 个字符 = 1 个 token
        return len(text) // 4
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取使用指标"""
        return self._metrics.copy()
    
    def reset_metrics(self):
        """重置指标"""
        self._metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "failed_requests": 0
        }
    
    def _update_metrics(self, tokens: int = 0, success: bool = True):
        """更新指标"""
        self._metrics["total_requests"] += 1
        if success:
            self._metrics["total_tokens"] += tokens
        else:
            self._metrics["failed_requests"] += 1

    def _create_client(self) -> 'httpx.AsyncClient':
        """创建 HTTP 客户端"""
        import httpx
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        return httpx.AsyncClient(
            timeout=self.config.timeout,
            limits=limits
        )

    async def _aretry_request(self, request_func):
        """带重试的请求"""
        import httpx
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return await request_func()
            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # 指数退避
        raise last_error or Exception("Request failed")

    def _format_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """格式化消息列表"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """发送聊天请求"""
        raise NotImplementedError("Subclasses must implement chat method")


# Provider 注册表
_PROVIDERS: Dict[str, type] = {}


def register_provider(provider_type: str, provider_class: type):
    """注册 Provider"""
    global _PROVIDERS
    _PROVIDERS[provider_type] = provider_class
    logger.info(f"Provider registered: {provider_type}")


def get_provider(provider_type: str) -> Optional[type]:
    """获取 Provider 类"""
    return _PROVIDERS.get(provider_type)


def list_providers() -> List[str]:
    """列出所有已注册的 Provider"""
    return list(_PROVIDERS.keys())
