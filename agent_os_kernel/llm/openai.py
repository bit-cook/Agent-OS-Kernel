# -*- coding: utf-8 -*-
"""OpenAI Provider - OpenAI API 支持

支持: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, 等
"""

import os
import json
import logging
from typing import List, Dict, Optional, AsyncIterator
import httpx
from .provider import LLMProvider, LLMConfig, LLMResponse, Message, ProviderType

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI Provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    @property
    def base_url(self) -> str:
        return self.config.base_url or "https://api.openai.com/v1"
    
    async def initialize(self):
        """初始化 OpenAI 客户端"""
        if not self.config.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY env variable.")
        
        self._client = self._create_client()
        self._client.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        })
        logger.info(f"OpenAI provider initialized with model: {self.config.model}")
    
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
            raise RuntimeError("OpenAI provider not initialized")
        
        payload = {
            "model": self.config.model,
            "messages": self._format_messages(messages),
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "stream": stream
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        # 添加额外参数
        for key, value in self.config.extra_params.items():
            if key not in payload:
                payload[key] = value
        
        async def make_request():
            endpoint = f"{self.base_url}/chat/completions"
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
            raise RuntimeError("OpenAI provider not initialized")
        
        payload = {
            "model": self.config.model,
            "messages": self._format_messages(messages),
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "stream": True
        }
        
        if tools:
            payload["tools"] = tools
        
        endpoint = f"{self.base_url}/chat/completions"
        
        async with self._client.stream("POST", endpoint, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        pass
    
    def _parse_response(self, data: Dict) -> LLMResponse:
        """解析响应"""
        choice = data["choices"][0]
        message = choice["message"]
        
        return LLMResponse(
            content=message.get("content", ""),
            model=data.get("model", self.config.model),
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            tool_calls=message.get("tool_calls")
        )
    
    async def count_tokens(self, text: str) -> int:
        """估算 token 数 (简单估算)"""
        return len(text) // 4


# 注册 Provider
from .provider import register_provider
register_provider(ProviderType.OPENAI, OpenAIProvider)
