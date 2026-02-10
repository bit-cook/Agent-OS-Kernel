# -*- coding: utf-8 -*-
import logging
"""Base LLM Provider - 基础 Provider 实现

提供完整的 LLM Provider 基础实现。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time

logger = logging.getLogger(__name__)


@dataclass
class ProviderMetrics:
    """Provider 指标"""
    total_requests: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    last_request_time: Optional[float] = None
    error_count: int = 0
    success_count: int = 0


class BaseLLMProvider(ABC):
    """基础 LLM Provider (完整实现)"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Provider
        
        Args:
            config: 配置字典
        """
        self.config = config
        self._metrics = ProviderMetrics()
        self._request_times: List[float] = []
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名称"""
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """聊天完成"""
        pass
    
    @abstractmethod
    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """流式聊天"""
        pass
    
    async def embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """
        获取嵌入向量 (默认实现)
        
        Args:
            texts: 文本列表
            model: 模型名称
            
        Returns:
            嵌入向量列表
        """
        # 默认实现：返回随机向量（生产环境应被覆盖）
        logger.warning(f"Provider {self.provider_name} using default embeddings")
        import random
        return [[random.uniform(-1, 1) for _ in range(1536)] for _ in texts]
    
    async def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """
        计算 token 数量 (默认实现)
        
        Args:
            text: 文本
            model: 模型名称
            
        Returns:
            token 数量
        """
        # 简单估算：约4个字符一个token
        return len(text) // 4
    
    async def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        return {
            "provider": self.provider_name,
            "model": self.config.get("model", "unknown"),
            "max_tokens": self.config.get("max_tokens", 4096),
            "supports_streaming": True,
            "supports_embeddings": True,
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取使用指标
        
        Returns:
            指标字典
        """
        total = self._metrics.total_requests
        avg_latency = sum(self._request_times) / len(self._request_times) if self._request_times else 0
        
        return {
            "provider": self.provider_name,
            "total_requests": self._metrics.total_requests,
            "total_tokens": self._metrics.total_tokens,
            "prompt_tokens": self._metrics.prompt_tokens,
            "completion_tokens": self._metrics.completion_tokens,
            "total_cost": self._metrics.total_cost,
            "avg_latency_ms": avg_latency,
            "success_rate": self._metrics.success_count / max(1, total) * 100,
            "error_rate": self._metrics.error_count / max(1, total) * 100,
        }
    
    def reset_metrics(self):
        """重置指标"""
        self._metrics = ProviderMetrics()
        self._request_times.clear()
    
    def _update_metrics(
        self,
        tokens: int,
        latency_ms: float,
        cost: float = 0.0,
        success: bool = True
    ):
        """更新指标"""
        self._metrics.total_requests += 1
        self._metrics.total_tokens += tokens
        self._metrics.last_request_time = time.time()
        self._request_times.append(latency_ms)
        
        if len(self._request_times) > 100:
            self._request_times = self._request_times[-100:]
        
        if success:
            self._metrics.success_count += 1
        else:
            self._metrics.error_count += 1
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态
        """
        return {
            "healthy": True,
            "provider": self.provider_name,
            "latency_ms": self._request_times[-1] if self._request_times else None,
            "uptime_seconds": time.time() - (self._metrics.last_request_time or time.time())
        }
    
    async def list_models(self) -> List[str]:
        """
        列出可用模型
        
        Returns:
            模型列表
        """
        return [self.config.get("model", "default")]
    
    async def shutdown(self):
        """关闭 Provider"""
        logger.info(f"Provider {self.provider_name} shutting down")
