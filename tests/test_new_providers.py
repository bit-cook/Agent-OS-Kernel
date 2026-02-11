"""测试新的 LLM Providers (AI21, Cerebras, Cloudflare)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent_os_kernel.llm.provider import LLMConfig, ProviderType, LLMProvider
from agent_os_kernel.llm.ai21_provider import AI21Provider
from agent_os_kernel.llm.cerebras_provider import CerebrasProvider
from agent_os_kernel.llm.cloudflare_provider import CloudflareProvider


class TestAI21Provider:
    """测试 AI21 Provider"""

    def test_provider_name(self):
        """测试 provider 名称"""
        config = LLMConfig(
            provider=ProviderType.AI21,
            model="j2-ultra",
            api_key="test-key"
        )
        provider = AI21Provider(config)
        assert provider.provider_name == "ai21"

    def test_provider_type(self):
        """测试 provider 类型"""
        config = LLMConfig(
            provider=ProviderType.AI21,
            model="j2-ultra",
            api_key="test-key"
        )
        provider = AI21Provider(config)
        assert provider.provider_type == ProviderType.AI21

    def test_supported_models(self):
        """测试支持的模型列表"""
        config = LLMConfig(
            provider=ProviderType.AI21,
            model="j2-ultra",
            api_key="test-key"
        )
        provider = AI21Provider(config)
        assert "j2-ultra" in provider.supported_models
        assert "j2-core" in provider.supported_models

    def test_base_url(self):
        """测试 base URL"""
        config = LLMConfig(
            provider=ProviderType.AI21,
            model="j2-ultra",
            api_key="test-key"
        )
        provider = AI21Provider(config)
        assert "api.ai21.com" in provider.base_url

    @pytest.mark.asyncio
    async def test_initialize_without_api_key(self):
        """测试缺少 API key 时初始化失败"""
        config = LLMConfig(
            provider=ProviderType.AI21,
            model="j2-ultra"
        )
        provider = AI21Provider(config)
        with pytest.raises(ValueError, match="API key is required"):
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_parse_response(self):
        """测试响应解析"""
        config = LLMConfig(
            provider=ProviderType.AI21,
            model="j2-ultra",
            api_key="test-key"
        )
        provider = AI21Provider(config)

        mock_response = {
            "model": "j2-ultra",
            "choices": [{
                "message": {
                    "content": "Hello, I am AI21!"
                },
                "finishReason": "stop"
            }],
            "usage": {
                "promptTokens": 10,
                "completionTokens": 20
            }
        }

        result = provider._parse_response(mock_response)
        assert result.content == "Hello, I am AI21!"
        assert result.model == "j2-ultra"
        assert result.finish_reason == "stop"


class TestCerebrasProvider:
    """测试 Cerebras Provider"""

    def test_provider_name(self):
        """测试 provider 名称"""
        config = LLMConfig(
            provider=ProviderType.CEREBRAS,
            model="llama-3.1-8b",
            api_key="test-key"
        )
        provider = CerebrasProvider(config)
        assert provider.provider_name == "cerebras"

    def test_provider_type(self):
        """测试 provider 类型"""
        config = LLMConfig(
            provider=ProviderType.CEREBRAS,
            model="llama-3.1-8b",
            api_key="test-key"
        )
        provider = CerebrasProvider(config)
        assert provider.provider_type == ProviderType.CEREBRAS

    def test_supported_models(self):
        """测试支持的模型列表"""
        config = LLMConfig(
            provider=ProviderType.CEREBRAS,
            model="llama-3.1-8b",
            api_key="test-key"
        )
        provider = CerebrasProvider(config)
        assert "llama-3.1-8b" in provider.supported_models
        assert "llama-3.1-70b" in provider.supported_models

    def test_base_url(self):
        """测试 base URL"""
        config = LLMConfig(
            provider=ProviderType.CEREBRAS,
            model="llama-3.1-8b",
            api_key="test-key"
        )
        provider = CerebrasProvider(config)
        assert "api.cerebras.ai" in provider.base_url

    @pytest.mark.asyncio
    async def test_initialize_without_api_key(self):
        """测试缺少 API key 时初始化失败"""
        config = LLMConfig(
            provider=ProviderType.CEREBRAS,
            model="llama-3.1-8b"
        )
        provider = CerebrasProvider(config)
        with pytest.raises(ValueError, match="API key is required"):
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_parse_response(self):
        """测试响应解析"""
        config = LLMConfig(
            provider=ProviderType.CEREBRAS,
            model="llama-3.1-8b",
            api_key="test-key"
        )
        provider = CerebrasProvider(config)

        mock_response = {
            "model": "llama-3.1-8b",
            "choices": [{
                "message": {
                    "content": "Hello from Cerebras!"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20
            }
        }

        result = provider._parse_response(mock_response)
        assert result.content == "Hello from Cerebras!"
        assert result.model == "llama-3.1-8b"

    @pytest.mark.asyncio
    async def test_count_tokens(self):
        """测试 token 计数"""
        config = LLMConfig(
            provider=ProviderType.CEREBRAS,
            model="llama-3.1-8b",
            api_key="test-key"
        )
        provider = CerebrasProvider(config)

        text = "Hello world, this is a test"
        tokens = await provider.count_tokens(text)
        # 约 3 字符 = 1 token
        assert tokens > 0


class TestCloudflareProvider:
    """测试 Cloudflare Provider"""

    def test_provider_name(self):
        """测试 provider 名称"""
        config = LLMConfig(
            provider=ProviderType.CLOUDFLARE,
            model="@cf/meta/llama-3-8b-instruct",
            api_key="test-key"
        )
        provider = CloudflareProvider(config)
        assert provider.provider_name == "cloudflare"

    def test_provider_type(self):
        """测试 provider 类型"""
        config = LLMConfig(
            provider=ProviderType.CLOUDFLARE,
            model="@cf/meta/llama-3-8b-instruct",
            api_key="test-key"
        )
        provider = CloudflareProvider(config)
        assert provider.provider_type == ProviderType.CLOUDFLARE

    def test_supported_models(self):
        """测试支持的模型列表"""
        config = LLMConfig(
            provider=ProviderType.CLOUDFLARE,
            model="@cf/meta/llama-3-8b-instruct",
            api_key="test-key"
        )
        provider = CloudflareProvider(config)
        assert "@cf/meta/llama-3-8b-instruct" in provider.supported_models
        assert "@cf/mistral/mistral-7b-instruct-v0.1" in provider.supported_models

    @pytest.mark.asyncio
    async def test_initialize_without_api_key(self):
        """测试缺少 API key 时初始化失败"""
        config = LLMConfig(
            provider=ProviderType.CLOUDFLARE,
            model="@cf/meta/llama-3-8b-instruct"
        )
        provider = CloudflareProvider(config)
        with pytest.raises(ValueError, match="API token is required"):
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_parse_response(self):
        """测试响应解析"""
        config = LLMConfig(
            provider=ProviderType.CLOUDFLARE,
            model="@cf/meta/llama-3-8b-instruct",
            api_key="test-key"
        )
        provider = CloudflareProvider(config)

        mock_response = {
            "model": "@cf/meta/llama-3-8b-instruct",
            "response": "Hello from Cloudflare!"
        }

        result = provider._parse_response(mock_response)
        assert result.content == "Hello from Cloudflare!"
        assert result.model == "@cf/meta/llama-3-8b-instruct"

    @pytest.mark.asyncio
    async def test_list_models_by_type(self):
        """测试按类型列出模型"""
        config = LLMConfig(
            provider=ProviderType.CLOUDFLARE,
            model="@cf/meta/llama-3-8b-instruct",
            api_key="test-key"
        )
        provider = CloudflareProvider(config)

        chat_models = await provider.list_models_by_type("chat")
        assert len(chat_models) > 0
        assert any("llama" in m["id"].lower() for m in chat_models)

        embedding_models = await provider.list_models_by_type("embedding")
        assert len(embedding_models) > 0


class TestProviderRegistration:
    """测试 Provider 注册"""

    def test_ai21_registration(self):
        """测试 AI21 注册"""
        from agent_os_kernel.llm.provider import get_provider, ProviderType
        provider_class = get_provider(ProviderType.AI21)
        assert provider_class is not None
        assert provider_class == AI21Provider

    def test_cerebras_registration(self):
        """测试 Cerebras 注册"""
        from agent_os_kernel.llm.provider import get_provider, ProviderType
        provider_class = get_provider(ProviderType.CEREBRAS)
        assert provider_class is not None
        assert provider_class == CerebrasProvider

    def test_cloudflare_registration(self):
        """测试 Cloudflare 注册"""
        from agent_os_kernel.llm.provider import get_provider, ProviderType
        provider_class = get_provider(ProviderType.CLOUDFLARE)
        assert provider_class is not None
        assert provider_class == CloudflareProvider


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
