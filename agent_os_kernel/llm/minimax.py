# -*- coding: utf-8 -*-
"""MiniMax Provider - MiniMax API 支持

支持: MiniMax Chat 模型
"""

import os
import json
import logging
from typing import List, Dict, Optional
import httpx
from .provider import LLMProvider, LLMConfig, LLMResponse, Message, ProviderType

logger = logging.getLogger(__name__)


class MiniMaxProvider(LLMProvider):
    """MiniMax Provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType("minimax")
    
    @property
    def base_url(self) -> str:
        return self.config.base_url or "https://api.minimax.chat/v1"
    
    async def initialize(self):
        """初始化 MiniMax 客户端"""
        if not self.config.api_key:
            raise ValueError("MiniMax API key is required. Set MINIMAX_API_KEY env variable.")
        
        self._client = self._create_client()
        self._client.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        })
        logger.info(f"MiniMax provider initialized with model: {self.config.model}")
    
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
            raise RuntimeError("MiniMax provider not initialized")
        
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
        
        endpoint = f"{self.base_url}/chat/completions"
        
        async def make_request():
            response = await self._client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        
        data = await self._aretry_request(make_request)
        
        return self._parse_response(data)
    
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
        """估算 token 数"""
        return len(text) // 4


# 注册 Provider
from .provider import register_provider
from .provider import ProviderType, register_provider
register_provider(ProviderType.MINIMAX, MiniMaxProvider)
