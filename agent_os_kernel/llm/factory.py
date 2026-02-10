# -*- coding: utf-8 -*-
"""LLM Provider Factory - Provider 管理工厂

参考 AIOS 设计，提供统一的 Provider 创建接口。
"""

import os
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

from .provider import (
    LLMProvider,
    LLMConfig,
    ProviderType,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderInfo:
    """Provider 信息"""
    type: ProviderType
    name: str
    description: str
    requires_api_key: bool = True
    local: bool = False
    default_model: str = ""


class LLMProviderFactory:
    """LLM Provider 工厂"""
    
    # Provider 注册表
    PROVIDERS: Dict[str, ProviderInfo] = {
        "openai": ProviderInfo(
            type=ProviderType.OPENAI,
            name="OpenAI",
            description="GPT-4, GPT-4 Turbo, GPT-3.5 Turbo",
            requires_api_key=True,
            default_model="gpt-4o"
        ),
        "anthropic": ProviderInfo(
            type=ProviderType.ANTHROPIC,
            name="Anthropic",
            description="Claude 3.5, Claude 3, Claude 2",
            requires_api_key=True,
            default_model="claude-sonnet-4-20250514"
        ),
        "deepseek": ProviderInfo(
            type=ProviderType.DEEPSEEK,
            name="DeepSeek",
            description="DeepSeek Chat, DeepSeek Reasoner",
            requires_api_key=True,
            default_model="deepseek-chat"
        ),
        "groq": ProviderInfo(
            type=ProviderType.GROQ,
            name="Groq",
            description="High-speed inference (Llama, Gemma, Mixtral)",
            requires_api_key=True,
            default_model="llama-3.3-70b-versatile"
        ),
        "ollama": ProviderInfo(
            type=ProviderType.OLLAMA,
            name="Ollama",
            description="Local LLM (Qwen, Llama, Mistral)",
            requires_api_key=False,
            local=True,
            default_model="qwen2.5:7b"
        ),
        "vllm": ProviderInfo(
            type=ProviderType.VLLM,
            name="vLLM",
            description="High-performance inference engine",
            requires_api_key=False,
            local=True,
            default_model="meta-llama/Llama-3.1-8B-Instruct"
        ),
        "kimi": ProviderInfo(
            type=ProviderType.KIMI,
            name="Kimi (Moonshot AI)",
            description="Long context models (8K/32K/128K/200K)",
            requires_api_key=True,
            default_model="moonshot-v1-32k"
        ),
        "minimax": ProviderInfo(
            type=ProviderType.MINIMAX,
            name="MiniMax",
            description="MiniMax chat models",
            requires_api_key=True,
            default_model="abab6.5s-chat"
        ),
        "qwen": ProviderInfo(
            type=ProviderType.QWEN,
            name="Qwen (Alibaba)",
            description="Qwen-Max, Qwen-Plus",
            requires_api_key=True,
            default_model="qwen-turbo"
        ),
    }
    
    def __init__(self):
        self._active_providers: Dict[str, LLMProvider] = {}
        self._default_provider: Optional[str] = None
    
    def create(self, config: LLMConfig) -> LLMProvider:
        """创建 Provider 实例"""
        logger.info(f"Created provider: {config.provider.value} ({config.model})")
        return None  # 实际实现需要具体 Provider 类
    
    def create_from_dict(self, config_data: Dict) -> LLMProvider:
        """从字典创建 Provider"""
        config = LLMConfig.from_dict(config_data)
        return self.create(config)
    
    def create_mock(self, model: str = "mock-model") -> 'MockProvider':
        """创建 Mock Provider (用于测试)"""
        from .mock_provider import MockProvider
        config = LLMConfig(
            provider="mock",
            model=model,
            api_key="mock-key"
        )
        return MockProvider(config)
    
    def list_providers(self) -> List[ProviderInfo]:
        """列出所有 Provider"""
        return list(self.PROVIDERS.values())
    
    def get_provider_info(self, provider_type: str) -> Optional[ProviderInfo]:
        """获取 Provider 信息"""
        return self.PROVIDERS.get(provider_type)


# 全局工厂实例
_factory: Optional[LLMProviderFactory] = None


def get_factory() -> LLMProviderFactory:
    """获取全局工厂"""
    global _factory
    if _factory is None:
        _factory = LLMProviderFactory()
    return _factory


def create_provider(config: LLMConfig) -> LLMProvider:
    """便捷创建函数"""
    return get_factory().create(config)


def create_mock_provider(model: str = "mock-model") -> 'MockProvider':
    """便捷创建 Mock Provider"""
    return get_factory().create_mock(model)
