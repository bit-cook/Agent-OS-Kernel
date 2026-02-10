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
import httpx
import structlog

logger = structlog.get_logger(__name__)


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
    top_p: float = 1.0
    timeout: float = 60.0
    max_retries: int = 3
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LLMConfig':
        """从字典创建配置"""
        provider_value = data.get('provider', 'openai')
        if isinstance(provider_value, str):
            provider = ProviderType.from_string(provider_value)
        else:
            provider = provider_value
        
        api_key_env_map = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'groq': 'GROQ_API_KEY',
            'kimi': 'KIMI_API_KEY',
            'minimax': 'MINIMAX_API_KEY',
            'qwen': 'DASHSCOPE_API_KEY',
        }
        
        env_key = api_key_env_map.get(provider_value.lower() if isinstance(provider_value, str) else '', '')
        api_key = data.get('api_key') or os.getenv(env_key) if env_key else data.get('api_key')
        
        return cls(
            provider=provider,
            model=data.get('model', 'gpt-3.5-turbo'),
            api_key=api_key,
            base_url=data.get('base_url'),
            max_tokens=data.get('max_tokens', 4096),
            temperature=data.get('temperature', 0.7),
            top_p=data.get('top_p', 1.0),
            timeout=data.get('timeout', 60.0),
            max_retries=data.get('max_retries', 3),
            extra_params=data.get('extra_params', {})
        )


@dataclass
class Message:
    """消息"""
    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


class LLMResponse:
    """LLM 响应"""
    
    def __init__(
        self,
        content: str,
        model: str,
        usage: Dict[str, int] = None,
        finish_reason: str = "stop",
        tool_calls: List[Dict] = None
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.finish_reason = finish_reason
        self.tool_calls = tool_calls or []
    
    def __str__(self) -> str:
        return self.content


class StreamResponse:
    """流式响应"""
    
    def __init__(self, chunks: AsyncIterator[str], model: str):
        self.chunks = chunks
        self.model = model


class LLMProvider(ABC):
    """LLM Provider 基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Provider 类型"""
        pass
    
    @property
    def model(self) -> str:
        """模型名称"""
        return self.config.model
    
    @property
    def max_tokens(self) -> int:
        """最大 token 数"""
        return self.config.max_tokens
    
    @abstractmethod
    async def initialize(self):
        """初始化 Provider"""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """关闭 Provider"""
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        tools: List[Dict] = None,
        stream: bool = False
    ) -> LLMResponse:
        """同步完成"""
        pass
    
    @abstractmethod
    async def stream_complete(
        self,
        messages: List[Message],
        tools: List[Dict] = None
    ) -> StreamResponse:
        """流式完成"""
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """计算 token 数"""
        pass
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()
    
    def _create_client(self) -> httpx.AsyncClient:
        """创建 HTTP 客户端"""
        timeout = httpx.Timeout(self.config.timeout)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        return httpx.AsyncClient(timeout=timeout, limits=limits)
    
    async def _aretry_request(self, request_func, *args, **kwargs):
        """带重试的请求"""
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await request_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Request attempt {attempt + 1} failed: {e}",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries
                )
                if attempt < self.config.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
        
        raise last_exception
    
    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        """格式化消息"""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
                **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {})
            }
            for msg in messages
        ]
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.initialize()
            await self.shutdown()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# 注册表
_provider_registry: Dict[ProviderType, type] = {}


def register_provider(provider_type: ProviderType, cls: type):
    """注册 Provider"""
    _provider_registry[provider_type] = cls


def get_provider(provider_type: ProviderType) -> Optional[type]:
    """获取 Provider 类"""
    return _provider_registry.get(provider_type)


def register_provider_by_value(provider_value: str, cls: type):
    """按值注册 Provider"""
    try:
        ptype = ProviderType(provider_value)
    except ValueError:
        ptype = ProviderType.CUSTOM
    _provider_registry[ptype] = cls
