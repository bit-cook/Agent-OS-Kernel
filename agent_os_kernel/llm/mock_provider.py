# -*- coding: utf-8 -*-
"""
Mock Provider - 用于测试的模拟 Provider

无需 API key 即可测试
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass

from .provider import (
    LLMProvider,
    LLMConfig,
    ChatMessage,
    StreamEvent,
    StreamEventType
)

logger = logging.getLogger(__name__)


class MockProvider(LLMProvider):
    """
    Mock Provider - 用于测试
    
    特点:
    - 无需 API key
    - 快速响应
    - 可配置的响应
    - 模拟各种场景
    """
    
    PROVIDER_NAME = "mock"
    
    def __init__(self, config: LLMConfig = None):
        """
        初始化 Mock Provider
        """
        self.config = config or LLMConfig(
            provider="mock",
            model="mock-model",
            api_key="mock-key"
        )
        
        self._call_count = 0
        self._delay = 0.1
        
        # 预设响应
        self._responses = {
            "hello": "Hello! I'm a mock AI assistant.",
            "help": "I'm a mock assistant. How can I help you?",
            "code": "Here's a Python example:\n\n```python\nprint('Hello, World!')\n```",
            "default": "This is a mock response."
        }
    
    async def initialize(self):
        """初始化"""
        logger.info("MockProvider initialized")
    
    async def shutdown(self):
        """关闭"""
        logger.info("MockProvider shutdown")
    
    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME
    
    @property
    def supported_models(self) -> List[str]:
        return ["mock-model", "mock-fast", "mock-smart"]
    
    def get_config(self) -> LLMConfig:
        return self.config
    
    def set_response(self, trigger: str, response: str):
        """设置预设响应"""
        self._responses[trigger.lower()] = response
    
    def set_delay(self, delay: float):
        """设置响应延迟"""
        self._delay = delay
    
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
        模拟聊天请求
        """
        self._call_count += 1
        
        # 模拟延迟
        await asyncio.sleep(self._delay)
        
        # 获取最后一条用户消息
        last_message = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_message = msg.content.lower()
                break
        
        # 选择响应
        content = self._responses.get("default")
        
        for trigger, response in self._responses.items():
            if trigger in last_message:
                content = response
                break
        
        # 模拟 token 计算
        prompt_tokens = sum(len(m.content.split()) for m in messages) // 4
        completion_tokens = len(content.split()) // 4
        
        result = {
            "content": content,
            "role": "assistant",
            "model": model or "mock-model",
            "object": "chat.completion",
            "created": int(__import__('time').time()),
            "id": f"mock-{self._call_count}",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "stop_reason": "stop"
        }
        
        return result
    
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamEvent]:
        """流式聊天"""
        result = await self.chat(messages, model=model, stream=False)
        
        words = result["content"].split()
        for word in words:
            yield StreamEvent(
                event_type=StreamEventType.CONTENT,
                data={"content": word + " "}
            )
            await asyncio.sleep(0.01)
        
        yield StreamEvent(
            event_type=StreamEventType.DONE,
            data={"finish_reason": "stop"}
        )
    
    async def embeddings(self, texts: List[str], model: str = "mock-embedding") -> List[List[float]]:
        """模拟嵌入"""
        import random
        return [
            [random.uniform(-1, 1) for _ in range(384)]
            for _ in texts
        ]
    
    async def count_tokens(self, text: str, model: str = "mock-model") -> int:
        """模拟 token 计算"""
        return len(text.split()) // 4
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "provider": self.PROVIDER_NAME,
            "total_requests": self._call_count,
            "delay_ms": self._delay * 1000
        }
    
    def reset_metrics(self):
        """重置指标"""
        self._call_count = 0


class MockErrorProvider(MockProvider):
    """模拟错误 Provider"""
    
    def __init__(self, config: LLMConfig = None):
        super().__init__(config)
        self._error_rate = 0.5
        self._error_message = "Mock API Error"
    
    def set_error_rate(self, rate: float):
        """设置错误率"""
        self._error_rate = rate
    
    def set_error_message(self, message: str):
        """设置错误消息"""
        self._error_message = message
    
    async def chat(self, **kwargs) -> Dict[str, Any]:
        """模拟错误"""
        import random
        if random.random() < self._error_rate:
            raise Exception(self._error_message)
        return await super().chat(**kwargs)


# 便捷函数
def create_mock_provider(model: str = "mock-model") -> MockProvider:
    """创建 Mock Provider"""
    return MockProvider()


def create_error_mock_provider(
    model: str = "mock-error",
    error_rate: float = 0.5
) -> MockErrorProvider:
    """创建模拟错误的 Provider"""
    provider = MockErrorProvider()
    provider.set_error_rate(error_rate)
    return provider
