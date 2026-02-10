# -*- coding: utf-8 -*-
"""Anthropic Provider - Claude API 支持

支持: Claude 3.5, Claude 3, Claude 2
"""

import os
import json
import logging
from typing import List, Dict, Optional, AsyncIterator
import httpx
from .provider import LLMProvider, LLMConfig, LLMResponse, Message, ProviderType

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Provider"""
    
    ANTHROPIC_VERSION = "2023-06-01"
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    @property
    def base_url(self) -> str:
        return self.config.base_url or "https://api.anthropic.com"
    
    async def initialize(self):
        """初始化 Anthropic 客户端"""
        if not self.config.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY env variable.")
        
        self._client = self._create_client()
        self._client.headers.update({
            "x-api-key": self.config.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json"
        })
        logger.info(f"Anthropic provider initialized with model: {self.config.model}")
    
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
            raise RuntimeError("Anthropic provider not initialized")
        
        # Anthropic 格式转换
        formatted_messages = []
        for msg in messages:
            if msg.role == "system":
                # System message
                formatted_messages.append({
                    "role": "user",
                    "content": f"\n\nHuman: {msg.content}\n\nAssistant: I understand."
                })
            else:
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        payload = {
            "model": self.config.model,
            "messages": formatted_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": stream
        }
        
        if tools:
            payload["tools"] = tools
        
        # Anthropic 使用不同的 endpoint
        endpoint = f"{self.base_url}/v1/messages"
        
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
            raise RuntimeError("Anthropic provider not initialized")
        
        formatted_messages = []
        for msg in messages:
            if msg.role == "system":
                formatted_messages.append({
                    "role": "user",
                    "content": f"\n\nHuman: {msg.content}\n\nAssistant:"
                })
            else:
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        payload = {
            "model": self.config.model,
            "messages": formatted_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True
        }
        
        if tools:
            payload["tools"] = tools
        
        endpoint = f"{self.base_url}/v1/messages"
        
        async with self._client.stream("POST", endpoint, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if chunk.get("type") == "content_block_delta":
                            delta = chunk.get("delta", {})
                            if "text" in delta:
                                yield delta["text"]
                    except json.JSONDecodeError:
                        pass
    
    def _parse_response(self, data: Dict) -> LLMResponse:
        """解析响应"""
        content_blocks = data.get("content", [])
        content = ""
        for block in content_blocks:
            if block.get("type") == "text":
                content += block.get("text", "")
        
        return LLMResponse(
            content=content,
            model=data.get("model", self.config.model),
            usage=data.get("usage", {}),
            finish_reason=data.get("stop_reason", "stop")
        )
    
    async def count_tokens(self, text: str) -> int:
        """估算 token 数"""
        return len(text) // 4


# 注册 Provider
from .provider import register_provider
register_provider(ProviderType.ANTHROPIC, AnthropicProvider)
