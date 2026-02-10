"""测试 LLM Provider"""

import pytest
from agent_os_kernel.llm.provider import LLMConfig, LLMProvider, ProviderType


class TestLLMConfig:
    """测试 LLM 配置"""
    
    def test_create_config(self):
        config = LLMConfig(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            api_key="test-key"
        )
        
        assert config.provider == ProviderType.OPENAI
        assert config.model == "gpt-4"
        assert config.api_key == "test-key"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
    
    def test_config_from_dict(self):
        data = {
            'provider': 'anthropic',
            'model': 'claude-3',
            'api_key': 'key123',
            'max_tokens': 8192,
            'temperature': 0.5
        }
        
        config = LLMConfig.from_dict(data)
        
        assert config.provider == ProviderType.ANTHROPIC
        assert config.model == 'claude-3'
        assert config.max_tokens == 8192
    
    def test_config_to_dict(self):
        config = LLMConfig(
            provider=ProviderType.DEEPSEEK,
            model="deepseek-chat",
            temperature=0.8
        )
        
        data = config.to_dict()
        
        assert data['provider'] == 'deepseek'
        assert data['model'] == 'deepseek-chat'
        assert data['temperature'] == 0.8


class TestProviderType:
    """测试 Provider 类型"""
    
    def test_provider_types(self):
        """测试所有 Provider 类型"""
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.DEEPSEEK.value == "deepseek"
        assert ProviderType.GROQ.value == "groq"
        assert ProviderType.OLLAMA.value == "ollama"
        assert ProviderType.VLLM.value == "vllm"
        assert ProviderType.KIMI.value == "kimi"
        assert ProviderType.MINIMAX.value == "minimax"
        assert ProviderType.QWEN.value == "qwen"
    
    def test_from_string(self):
        """测试从字符串创建"""
        pt = ProviderType.from_string("openai")
        assert pt == ProviderType.OPENAI
        
        pt = ProviderType.from_string("unknown")
        assert pt == ProviderType.CUSTOM
    
    def test_from_string_case_insensitive(self):
        """测试大小写不敏感"""
        pt = ProviderType.from_string("openai")
        assert pt == ProviderType.OPENAI
        
        pt = ProviderType.from_string("deepseek")
        assert pt == ProviderType.DEEPSEEK
