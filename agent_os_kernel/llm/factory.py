# -*- coding: utf-8 -*-
"""LLM Provider Factory - Provider 管理工厂

参考 AIOS 设计，提供统一的 Provider 创建接口。
"""

import os
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from .provider import (
    LLMProvider, LLMConfig, Message,
    ProviderType, register_provider, get_provider
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
            type=ProviderType("openai"),
            name="OpenAI",
            description="GPT-4, GPT-4 Turbo, GPT-3.5 Turbo",
            requires_api_key=True,
            default_model="gpt-4o"
        ),
        "anthropic": ProviderInfo(
            type=ProviderType("anthropic"),
            name="Anthropic",
            description="Claude 3.5, Claude 3, Claude 2",
            requires_api_key=True,
            default_model="claude-sonnet-4-20250514"
        ),
        "deepseek": ProviderInfo(
            type=ProviderType("deepseek"),
            name="DeepSeek",
            description="DeepSeek Chat, DeepSeek Reasoner",
            requires_api_key=True,
            default_model="deepseek-chat"
        ),
        "groq": ProviderInfo(
            type=ProviderType("groq"),
            name="Groq",
            description="高速推理 (Llama, Gemma, Mixtral)",
            requires_api_key=True,
            default_model="llama-3.3-70b-versatile"
        ),
        "ollama": ProviderInfo(
            type=ProviderType("ollama"),
            name="Ollama",
            description="本地 LLM 运行 (Qwen, Llama, Mistral)",
            requires_api_key=False,
            local=True,
            default_model="qwen2.5:7b"
        ),
        "vllm": ProviderInfo(
            type=ProviderType("vllm"),
            name="vLLM",
            description="高性能推理引擎",
            requires_api_key=False,
            local=True,
            default_model="meta-llama/Llama-3.1-8B-Instruct"
        ),
        # 🇨🇳 中国模型
        "kimi": ProviderInfo(
            type=ProviderType("kimi"),
            name="Kimi (Moonshot AI)",
            description="Kimi 长文本模型，支持超长上下文",
            requires_api_key=True,
            default_model="moonshot-v1-8k"
        ),
        "minimax": ProviderInfo(
            type=ProviderType("minimax"),
            name="MiniMax",
            description="MiniMax 聊天模型",
            requires_api_key=True,
            default_model="abab6.5s-chat"
        ),
        "qwen": ProviderInfo(
            type=ProviderType("qwen"),
            name="Qwen (Alibaba)",
            description="通义千问 Qwen-Max, Qwen-Plus",
            requires_api_key=True,
            default_model="qwen-turbo"
        ),
    }
    
    def __init__(self):
        self._active_providers: Dict[str, LLMProvider] = {}
        self._default_provider: Optional[str] = None
    
    def create(self, config: LLMConfig) -> LLMProvider:
        """创建 Provider 实例"""
        provider_class = get_provider(config.provider)
        
        if not provider_class:
            raise ValueError(f"Unknown provider type: {config.provider}")
        
        provider = provider_class(config)
        logger.info(f"Created provider: {config.provider.value} ({config.model})")
        
        return provider
    
    def create_from_dict(self, config_data: Dict) -> LLMProvider:
        """从字典创建 Provider"""
        config = LLMConfig.from_dict(config_data)
        return self.create(config)
    
    def create_from_yaml(self, yaml_data: Dict) -> LLMProvider:
        """从 YAML 配置创建 Provider"""
        provider_data = yaml_data.copy()
        
        provider_type = ProviderType(provider_data.get('provider', 'openai'))
        
        api_key_env_map = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'groq': 'GROQ_API_KEY',
            'kimi': 'KIMI_API_KEY',
            'minimax': 'MINIMAX_API_KEY',
            'qwen': 'DASHSCOPE_API_KEY',
        }
        
        env_key = api_key_env_map.get(provider_data.get('provider', '').lower(), '')
        
        if not provider_data.get('api_key') and env_key:
            provider_data['api_key'] = os.getenv(env_key)
        
        return self.create(LLMConfig(
            provider=provider_type,
            model=provider_data.get('model', self.PROVIDERS.get(
                provider_data.get('provider', 'openai'), ProviderInfo(
                    type=provider_type, name="", description=""
                )
            ).default_model),
            api_key=provider_data.get('api_key'),
            base_url=provider_data.get('base_url'),
            max_tokens=provider_data.get('max_tokens', 4096),
            temperature=provider_data.get('temperature', 0.7),
            timeout=provider_data.get('timeout', 60.0),
            max_retries=provider_data.get('max_retries', 3),
            extra_params=provider_data.get('extra_params', {})
        ))
    
    async def create_and_initialize(self, config: LLMConfig) -> LLMProvider:
        """创建并初始化 Provider"""
        provider = self.create(config)
        await provider.initialize()
        
        provider_id = f"{config.provider.value}:{config.model}"
        self._active_providers[provider_id] = provider
        
        if self._default_provider is None:
            self._default_provider = provider_id
        
        return provider
    
    async def shutdown_all(self):
        """关闭所有 Provider"""
        for provider_id, provider in self._active_providers.items():
            try:
                await provider.shutdown()
                logger.info(f"Shutdown provider: {provider_id}")
            except Exception as e:
                logger.error(f"Failed to shutdown {provider_id}: {e}")
        
        self._active_providers.clear()
    
    async def get_provider(self, provider_id: str) -> Optional[LLMProvider]:
        """获取 Provider"""
        return self._active_providers.get(provider_id)
    
    async def get_default(self) -> Optional[LLMProvider]:
        """获取默认 Provider"""
        if self._default_provider:
            return self._active_providers.get(self._default_provider)
        return None
    
    async def switch_provider(self, provider_id: str) -> bool:
        """切换默认 Provider"""
        if provider_id in self._active_providers:
            self._default_provider = provider_id
            logger.info(f"Switched to provider: {provider_id}")
            return True
        return False
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """列出所有 Provider 配置"""
        return [
            {
                'id': ptype,
                'name': info.name,
                'description': info.description,
                'requires_api_key': info.requires_api_key,
                'local': info.local,
                'default_model': info.default_model,
                'active': any(
                    cfg.provider.value == ptype
                    for cfg in self._active_providers.values()
                )
            }
            for ptype, info in self.PROVIDERS.items()
        ]
    
    def get_provider_info(self, provider_type: str) -> Optional[ProviderInfo]:
        """获取 Provider 信息"""
        return self.PROVIDERS.get(provider_type)
    
    def get_chinese_providers(self) -> List[ProviderInfo]:
        """获取中国模型 Provider"""
        return [
            self.PROVIDERS[p]
            for p in ['deepseek', 'kimi', 'minimax', 'qwen']
        ]
    
    def get_local_providers(self) -> List[ProviderInfo]:
        """获取本地模型 Provider"""
        return [
            info for info in self.PROVIDERS.values()
            if info.local
        ]


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
