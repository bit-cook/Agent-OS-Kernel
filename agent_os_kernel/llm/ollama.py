# -*- coding: utf-8 -*-
"""Ollama Provider - 本地 LLM 支持

支持: Qwen, Llama, Mistral, Gemma, 等
"""

import os
import json
import logging
from typing import List, Dict, Optional, AsyncIterator
import httpx
from .provider import LLMProvider, LLMConfig, LLMResponse, Message, ProviderType

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama Provider - 本地 LLM"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA
    
    @property
    def base_url(self) -> str:
        return self.config.base_url or "http://localhost:11434"
    
    async def initialize(self):
        """初始化 Ollama 客户端"""
        self._client = self._create_client()
        logger.info(f"Ollama provider initialized: {self.base_url}")
    
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
            raise RuntimeError("Ollama provider not initialized")
        
        # 转换为 Ollama 格式
        prompt = self._format_prompt(messages)
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "num_predict": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p
            }
        }
        
        # 添加额外参数
        for key, value in self.config.extra_params.items():
            if key not in payload:
                payload[key] = value
        
        if stream:
            return await self._stream_request(payload)
        else:
            return await self._sync_request(payload)
    
    async def _sync_request(self, payload: Dict) -> LLMResponse:
        """同步请求"""
        endpoint = f"{self.base_url}/api/generate"
        
        async def make_request():
            response = await self._client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        
        data = await self._aretry_request(make_request)
        
        return LLMResponse(
            content=data.get("response", ""),
            model=self.config.model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0)
            }
        )
    
    async def _stream_request(self, payload: Dict) -> AsyncIterator[str]:
        """流式请求"""
        endpoint = f"{self.base_url}/api/generate"
        
        async with self._client.stream("POST", endpoint, json=payload) as response:
            async for line in response.aiter_lines():
                try:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        yield chunk["response"]
                except json.JSONDecodeError:
                    pass
    
    async def stream_complete(
        self,
        messages: List[Message],
        tools: List[Dict] = None
    ) -> AsyncIterator[str]:
        """流式完成"""
        return await self.complete(messages, tools, stream=True)
    
    def _format_prompt(self, messages: List[Message]) -> str:
        """格式化为 Ollama prompt"""
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content}")
            else:
                parts.append(f"{msg.role}: {msg.content}")
        return "\n\n".join(parts) + "\n\nAssistant:"
    
    async def count_tokens(self, text: str) -> int:
        """估算 token 数"""
        # Ollama 使用 tiktoken 类似分词
        # 简单估算: 英文 4 字符/token, 中文 2 字符/token
        chinese_chars = sum(1 for c in text if ord(c) > 127)
        english_chars = len(text) - chinese_chars
        return (english_chars // 4) + (chinese_chars // 2)
    
    async def list_models(self) -> List[Dict]:
        """列出可用模型"""
        if not self._client:
            raise RuntimeError("Ollama provider not initialized")
        
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def pull_model(self, model: str) -> AsyncIterator[Dict]:
        """拉取模型"""
        endpoint = f"{self.base_url}/api/pull"
        payload = {"name": model, "stream": True}
        
        async with self._client.stream("POST", endpoint, json=payload) as response:
            async for line in response.aiter_lines():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass
    
    async def delete_model(self, model: str) -> bool:
        """删除模型"""
        try:
            response = await self._client.delete(
                f"{self.base_url}/api/delete",
                params={"name": model}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False


# 注册 Provider
from .provider import register_provider
register_provider(ProviderType.OLLAMA, OllamaProvider)
