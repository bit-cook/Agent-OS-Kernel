# -*- coding: utf-8 -*-
"""AI21 Labs Provider - Jurassic 系列模型支持

支持: Jurassic-2 (J2), J2-Core, J2-Ultra
"""

import os
import json
import logging
from typing import List, Dict, Optional, AsyncIterator, Any
import httpx
from .provider import LLMProvider, LLMConfig, LLMResponse, Message, ProviderType

logger = logging.getLogger(__name__)


class AI21Provider(LLMProvider):
    """AI21 Labs Provider - Jurassic 系列"""

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "j2-ultra",
        "j2-core",
        "j2-7b-instruct",
        "j2-7b-base",
        "j2-1b-instruct",
    ]

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_name(self) -> str:
        return "ai21"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.AI21

    @property
    def supported_models(self) -> List[str]:
        return self.SUPPORTED_MODELS

    @property
    def base_url(self) -> str:
        return self.config.base_url or "https://api.ai21.com/studio/v1"

    async def initialize(self):
        """初始化 AI21 客户端"""
        if not self.config.api_key:
            raise ValueError("AI21 API key is required. Set AI21_API_KEY env variable.")

        self._client = self._create_client()
        self._client.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        })
        logger.info(f"AI21 provider initialized with model: {self.config.model}")

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
            raise RuntimeError("AI21 provider not initialized")

        # AI21 格式
        formatted_messages = []
        system_message = ""

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        payload = {
            "model": self.config.model,
            "messages": formatted_messages,
            "maxTokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        if system_message:
            payload["system"] = system_message

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
            raise RuntimeError("AI21 provider not initialized")

        formatted_messages = []
        system_message = ""

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        payload = {
            "model": self.config.model,
            "messages": formatted_messages,
            "maxTokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True
        }

        if system_message:
            payload["system"] = system_message

        endpoint = f"{self.base_url}/chat/completions"

        async with self._client.stream("POST", endpoint, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        pass

    def _parse_response(self, data: Dict) -> LLMResponse:
        """解析响应"""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        # 解析 usage
        usage = data.get("usage", {})
        prompt_tokens = usage.get("promptTokens", 0)
        completion_tokens = usage.get("completionTokens", 0)

        return LLMResponse(
            content=message.get("content", ""),
            model=data.get("model", self.config.model),
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            finish_reason=choice.get("finishReason", "stop"),
            tool_calls=message.get("tool_calls")
        )

    async def count_tokens(self, text: str, model: str = "j2-ultra") -> int:
        """估算 token 数"""
        # AI21 使用类似的分词器，约 4 个字符 = 1 个 token
        return len(text) // 4

    async def list_models(self) -> List[str]:
        """列出可用模型"""
        return self.SUPPORTED_MODELS

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
register_provider(ProviderType.AI21, AI21Provider)
