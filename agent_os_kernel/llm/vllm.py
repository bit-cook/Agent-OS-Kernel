# -*- coding: utf-8 -*-
"""VLLM Provider - 高性能推理引擎支持

支持: Llama, Qwen, Mistral, 等主流模型
"""

import os
import json
import logging
from typing import List, Dict, Optional, AsyncIterator
import httpx
from .provider import LLMProvider, LLMConfig, LLMResponse, Message, ProviderType

logger = logging.getLogger(__name__)


class VLLMProvider(LLMProvider):
    """VLLM Provider - 高性能本地推理"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.VLLM
    
    @property
    def base_url(self) -> str:
        return self.config.base_url or "http://localhost:8000/v1"
    
    async def initialize(self):
        """初始化 VLLM 客户端"""
        self._client = self._create_client()
        logger.info(f"VLLM provider initialized: {self.base_url}")
    
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
            raise RuntimeError("VLLM provider not initialized")
        
        # OpenAI 兼容格式
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
    
    async def stream_complete(
        self,
        messages: List[Message],
        tools: List[Dict] = None
    ) -> AsyncIterator[str]:
        """流式完成"""
        if not self._client:
            raise RuntimeError("VLLM provider not initialized")
        
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
        """估算 token 数"""
        return len(text) // 4
    
    async def health_check(self) -> bool:
        """VLLM 健康检查"""
        try:
            if not self._client:
                await self.initialize()
            
            response = await self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"VLLM health check failed: {e}")
            return False


# 注册 Provider
from .provider import register_provider
register_provider(ProviderType.VLLM, VLLMProvider)
