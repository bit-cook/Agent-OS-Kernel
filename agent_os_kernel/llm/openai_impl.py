# -*- coding: utf-8 -*-
"""
OpenAI Provider Implementation

完整的 OpenAI API 实现
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from .provider import (
    LLMProvider,
    LLMConfig,
    Message,
    ChatMessage,
    StreamEvent,
    StreamEventType
)

logger = logging.getLogger(__name__)


@dataclass
class OpenAIConfig:
    """OpenAI 配置"""
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    organization: Optional[str] = None
    max_retries: int = 3
    timeout: float = 60.0
    model: str = "gpt-4o"


class OpenAIProvider(LLMProvider):
    """
    OpenAI Provider
    
    支持:
    - gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo
    - 流式输出
    - 函数调用
    - Token 使用统计
    """
    
    PROVIDER_NAME = "openai"
    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k"
    ]
    
    def __init__(self, config: OpenAIConfig):
        """
        初始化 OpenAI Provider
        
        Args:
            config: OpenAI 配置
        """
        self.config = config
        self._client = None
        self._metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "failed_requests": 0
        }
    
    async def initialize(self):
        """初始化客户端"""
        try:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                organization=self.config.organization,
                max_retries=self.config.max_retries,
                timeout=self.config.timeout
            )
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.warning("openai package not installed")
            self._client = None
    
    async def shutdown(self):
        """关闭客户端"""
        if self._client:
            await self._client.close()
            logger.info("OpenAI client closed")
    
    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME
    
    @property
    def supported_models(self) -> List[str]:
        return self.SUPPORTED_MODELS
    
    def get_config(self) -> LLMConfig:
        """获取配置"""
        return LLMConfig(
            provider=self.PROVIDER_NAME,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            max_tokens=4096,
            temperature=0.7
        )
    
    async def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大输出 token
            temperature: 温度
            stream: 是否流式输出
            **kwargs: 其他参数
        
        Returns:
            响应结果
        """
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
        
        model = model or "gpt-4o"
        
        # 转换消息格式
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # 构建请求参数
        params = {
            "model": model,
            "messages": openai_messages,
            "stream": stream
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        if temperature is not None:
            params["temperature"] = temperature
        
        self._metrics["total_requests"] += 1
        
        try:
            if stream:
                return await self._stream_chat(**params)
            else:
                return await self._sync_chat(**params)
        
        except Exception as e:
            self._metrics["failed_requests"] += 1
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _sync_chat(self, **params) -> Dict[str, Any]:
        """同步聊天请求"""
        response = await self._client.chat.completions.create(**params)
        
        # 提取响应
        choice = response.choices[0]
        message = choice.message
        
        # 更新指标
        if hasattr(response, 'usage'):
            self._metrics["prompt_tokens"] += response.usage.prompt_tokens
            self._metrics["completion_tokens"] += response.usage.completion_tokens
            self._metrics["total_tokens"] += response.usage.total_tokens
        
        return {
            "content": message.content,
            "role": message.role,
            "model": response.model,
            "object": response.object,
            "created": response.created,
            "id": response.id,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if hasattr(response, 'usage') else None,
            "stop_reason": choice.finish_reason
        }
    
    async def _stream_chat(self, **params) -> AsyncIterator[StreamEvent]:
        """流式聊天请求"""
        # openai SDK: create() 返回协程，await 后得到可异步迭代的 stream
        # （不是 async context manager）
        stream = await self._client.chat.completions.create(**params)
        async for chunk in stream:
                choice = chunk.choices[0]
                
                if choice.delta.content:
                    yield StreamEvent(
                        event_type=StreamEventType.CONTENT,
                        data={"content": choice.delta.content}
                    )
                
                if choice.finish_reason:
                    yield StreamEvent(
                        event_type=StreamEventType.DONE,
                        data={"finish_reason": choice.finish_reason}
                    )
    
    async def embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """
        获取文本嵌入
        
        Args:
            texts: 文本列表
            model: 嵌入模型
        
        Returns:
            嵌入向量列表
        """
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
        
        response = await self._client.embeddings.create(
            model=model,
            input=texts
        )
        
        return [data.embedding for data in response.data]
    
    async def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """
        计算 token 数量
        
        Args:
            text: 文本
            model: 模型名称
        
        Returns:
            Token 数量
        """
        # 使用 tiktoken 计算
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except ImportError:
            # 粗略估计
            return len(text) // 4
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "provider": self.PROVIDER_NAME,
            **self._metrics
        }
    
    def reset_metrics(self):
        """重置指标"""
        self._metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "failed_requests": 0
        }


# 便捷函数
def create_openai_provider(
    api_key: str,
    model: str = "gpt-4o",
    base_url: str = "https://api.openai.com/v1"
) -> OpenAIProvider:
    """创建 OpenAI Provider"""
    config = OpenAIConfig(
        api_key=api_key,
        base_url=base_url,
        model=model
    )
    return OpenAIProvider(config)
