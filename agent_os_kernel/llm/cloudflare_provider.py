# -*- coding: utf-8 -*-
"""Cloudflare Provider - Workers AI 支持

支持: Llama, Mistral, Whisper, Embeddings 等
通过 Cloudflare Workers AI 部署
"""

import os
import json
import logging
from typing import List, Dict, Optional, AsyncIterator, Any
import httpx
from .provider import LLMProvider, LLMConfig, LLMResponse, Message, ProviderType

logger = logging.getLogger(__name__)


class CloudflareProvider(LLMProvider):
    """Cloudflare Workers AI Provider - 边缘 AI"""

    # 支持的模型列表
    SUPPORTED_MODELS = {
        "@cf/meta/llama-3-8b-instruct": {
            "type": "chat",
            "name": "Llama 3 8B"
        },
        "@cf/meta/llama-3-70b-instruct": {
            "type": "chat",
            "name": "Llama 3 70B"
        },
        "@cf/meta/llama-3.1-8b-instruct": {
            "type": "chat",
            "name": "Llama 3.1 8B"
        },
        "@cf/meta/llama-3.2-1b-chat": {
            "type": "chat",
            "name": "Llama 3.2 1B"
        },
        "@cf/meta/llama-3.2-3b-chat": {
            "type": "chat",
            "name": "Llama 3.2 3B"
        },
        "@cf/mistral/mistral-7b-instruct-v0.1": {
            "type": "chat",
            "name": "Mistral 7B"
        },
        "@cf/mistral/mistral-7b-instruct-v0.2": {
            "type": "chat",
            "name": "Mistral 7B v2"
        },
        "@cf/deepseek-ai/deepseek-coder-6.7b-base": {
            "type": "chat",
            "name": "DeepSeek Coder"
        },
        "@cf/openai/whisper": {
            "type": "audio",
            "name": "Whisper"
        },
        "@cf/sentence-transformers/all-minilm-l6-v2": {
            "type": "embedding",
            "name": "All-MiniLM L6 v2"
        },
        "@cf/baai/bge-base-en-v1.5": {
            "type": "embedding",
            "name": "BGE Base"
        },
    }

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._account_id: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "cloudflare"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CLOUDFLARE

    @property
    def supported_models(self) -> List[str]:
        return list(self.SUPPORTED_MODELS.keys())

    @property
    def base_url(self) -> str:
        account_id = self._account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        return self.config.base_url or f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"

    async def initialize(self):
        """初始化 Cloudflare 客户端"""
        if not self.config.api_key:
            raise ValueError("Cloudflare API token is required. Set CLOUDFLARE_API_TOKEN env variable.")

        self._account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")

        self._client = self._create_client()
        self._client.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        })
        logger.info(f"Cloudflare provider initialized with model: {self.config.model}")

    async def shutdown(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def complete(
        self,
        messages: List[Message],
        tools: List[Dict] = None,
        stream: bool = False
    ) -> LLMResponse:
        """发送完成请求"""
        if not self._client:
            raise RuntimeError("Cloudflare provider not initialized")

        # Cloudflare 格式
        formatted_messages = []
        for msg in messages:
            if msg.role == "system":
                # Cloudflare 使用特殊的 system prompt 格式
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            else:
                formatted_messages.append({
                    "role": msg.role if msg.role != "assistant" else "assistant",
                    "content": msg.content
                })

        payload = {
            "messages": formatted_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        # Cloudflare 使用 /chat/completions endpoint
        endpoint = f"{self.base_url}/chat/completions"

        async def make_request():
            response = await self._client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()

        data = await self._aretry_request(make_request)

        return self._parse_response(data)

    async def stream_complete(
        self,
        messages: List[Message],
        tools: List[Dict] = None
    ) -> AsyncIterator[str]:
        """流式完成"""
        if not self._client:
            raise RuntimeError("Cloudflare provider not initialized")

        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role if msg.role != "assistant" else "assistant",
                "content": msg.content
            })

        payload = {
            "messages": formatted_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True
        }

        endpoint = f"{self.base_url}/chat/completions"

        async with self._client.stream("POST", endpoint, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "response" in chunk:
                            yield chunk["response"]
                    except json.JSONDecodeError:
                        pass

    async def embeddings(self, texts: List[str], model: str = "@cf/sentence-transformers/all-minilm-l6-v2") -> List[List[float]]:
        """获取嵌入向量"""
        if not self._client:
            raise RuntimeError("Cloudflare provider not initialized")

        embeddings = []
        for text in texts:
            payload = {
                "text": text
            }

            endpoint = f"{self.base_url}/embeddings"

            async def make_request():
                response = await self._client.post(endpoint, json=payload)
                response.raise_for_status()
                return response.json()

            data = await self._aretry_request(make_request)
            embeddings.append(data.get("data", [{}])[0].get("embedding", []))

        return embeddings

    def _parse_response(self, data: Dict) -> LLMResponse:
        """解析响应"""
        # Cloudflare 返回格式
        content = data.get("result", {}).get("response", "") if "result" in data else data.get("response", "")

        # 解析 usage (Cloudflare 不总是返回详细 usage)
        usage = data.get("usage", {})
        if not usage:
            prompt_tokens = len(content.split()) // 4
            completion_tokens = len(content.split()) // 4
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }

        return LLMResponse(
            content=content,
            model=data.get("model", self.config.model),
            usage=usage,
            finish_reason="stop",
            tool_calls=None
        )

    async def count_tokens(self, text: str, model: str = "@cf/meta/llama-3-8b-instruct") -> int:
        """估算 token 数"""
        # Llama 分词器约 3.5 字符 = 1 个 token
        return len(text) // 3

    async def list_models(self) -> List[str]:
        """列出可用模型"""
        return self.SUPPORTED_MODELS

    async def list_models_by_type(self, model_type: str) -> List[Dict[str, str]]:
        """按类型列出模型"""
        return [
            {"id": k, "name": v["name"]}
            for k, v in self.SUPPORTED_MODELS.items()
            if v["type"] == model_type
        ]

    async def chat(
        self,
        messages: List['ChatMessage'],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """发送聊天请求"""
        from .provider import ChatMessage, Message
        # 转换为 Message 格式
        msg_list = [
            Message(role=msg.role, content=msg.content)
            for msg in messages
        ]
        response = await self.complete(msg_list, stream=stream)
        return {
            "content": response.content,
            "model": response.model,
            "usage": response.usage,
            "finish_reason": response.finish_reason
        }

    def get_config(self) -> LLMConfig:
        """获取配置"""
        return self.config


# 注册 Provider
from .provider import register_provider
register_provider(ProviderType.CLOUDFLARE, CloudflareProvider)
