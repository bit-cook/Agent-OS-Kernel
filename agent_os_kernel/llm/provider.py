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

# 尝试导入可选依赖
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


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
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名称"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表"""
        pass
    
    @abstractmethod
    def get_config(self) -> LLMConfig:
        """获取配置"""
        pass
    
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
        pass
    
    async def initialize(self):
        """初始化 Provider"""
        pass
    
    async def shutdown(self):
        """关闭 Provider"""
        pass
    
    async def embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """获取嵌入向量"""
        raise NotImplementedError("Embeddings not supported")
    
    async def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """计算 token 数量"""
        return len(text) // 4
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取使用指标"""
        return {"total_requests": 0, "total_tokens": 0}
    
    def reset_metrics(self):
        """重置指标"""
        pass


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
