# -*- coding: utf-8 -*-
"""Context Compressor - 上下文压缩优化

参考 AutoGen 和 Manus 的上下文管理最佳实践。

功能：
1. 基于重要性的压缩
2. 语义摘要生成
3. Token 预算管理
4. 信息密度优化
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """压缩策略"""
    NONE = "none"                    # 不压缩
    TRUNCATE = "truncate"            # 截断
    SUMMARIZE = "summarize"          # 摘要
    IMPORTANCE_FILTER = "importance"  # 重要性过滤
    HYBRID = "hybrid"                # 混合 (推荐)


@dataclass
class CompressedChunk:
    """压缩后的块"""
    original_text: str
    compressed_text: str
    compression_ratio: float
    importance_score: float
    chunk_id: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class CompressionConfig:
    """压缩配置"""
    max_tokens: int = 8192           # 最大 token 数
    min_compression_ratio: float = 0.3  # 最小压缩率
    preserve_system_prompt: bool = True  # 保留系统提示
    preserve_recent: int = 3         # 保留最近 N 条消息
    importance_threshold: float = 0.4  # 重要性阈值
    summary_model: Optional[str] = None  # 摘要模型
    token_per_message: int = 4       # 每个消息的 token 开销


class ContextCompressor:
    """
    上下文压缩器
    
    参考 AutoGen 的上下文管理实现，提供多种压缩策略。
    """
    
    def __init__(self, config: CompressionConfig = None):
        self.config = config or CompressionConfig()
        self._importance_cache: Dict[str, float] = {}
    
    def compress_messages(
        self,
        messages: List[Dict[str, Any]],
        strategy: CompressionStrategy = CompressionStrategy.HYBRID
    ) -> List[Dict[str, Any]]:
        """
        压缩消息列表
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            strategy: 压缩策略
            
        Returns:
            压缩后的消息列表
        """
        if not messages:
            return messages
        
        # 计算当前 token 数
        current_tokens = self._count_tokens(messages)
        
        if current_tokens <= self.config.max_tokens:
            return messages
        
        logger.info(
            f"需要压缩上下文: {current_tokens} -> {self.config.max_tokens} tokens"
        )
        
        # 根据策略选择压缩方法
        if strategy == CompressionStrategy.TRUNCATE:
            return self._truncate(messages)
        elif strategy == CompressionStrategy.SUMMARIZE:
            return self._summarize(messages)
        elif strategy == CompressionStrategy.IMPORTANCE_FILTER:
            return self._filter_by_importance(messages)
        elif strategy == CompressionStrategy.HYBRID:
            return self._hybrid_compress(messages)
        else:
            return messages
    
    def _truncate(self, messages: List[Dict]) -> List[Dict]:
        """截断策略 - 保留最近的消息"""
        max_messages = self._estimate_max_messages()
        
        # 保留系统提示
        result = []
        system_msgs = [m for m in messages if m.get("role") == "system"]
        result.extend(system_msgs)
        
        # 保留最近的消息
        non_system = [m for m in messages if m.get("role") != "system"]
        result.extend(non_system[-max_messages:])
        
        return result
    
    def _summarize(self, messages: List[Dict]) -> List[Dict]:
        """摘要策略 - 将旧消息压缩为摘要"""
        if len(messages) <= self.config.preserve_recent + 1:
            return messages
        
        result = []
        
        # 保留系统提示
        system_msgs = [m for m in messages if m.get("role") == "system"]
        result.extend(system_msgs)
        
        # 保留最近消息
        recent = [m for m in messages if m.get("role") != "system"][-self.config.preserve_recent:]
        
        # 压缩旧消息为摘要
        old_messages = [m for m in messages if m.get("role") != "system"][:-self.config.preserve_recent]
        
        if old_messages:
            summary = self._generate_summary(old_messages)
            result.append({
                "role": "system",
                "content": f"[历史对话摘要]\n{summary}",
                "_compressed": True
            })
        
        result.extend(recent)
        return result
    
    def _filter_by_importance(self, messages: List[Dict]) -> List[Dict]:
        """重要性过滤 - 只保留重要的消息"""
        result = []
        
        # 计算每条消息的重要性
        scored = []
        for i, msg in enumerate(messages):
            importance = self._calculate_importance(msg, i, messages)
            scored.append((msg, importance))
        
        # 按重要性排序并过滤
        scored.sort(key=lambda x: x[1], reverse=True)
        
        total_tokens = 0
        max_tokens = self.config.max_tokens
        
        for msg, importance in scored:
            if importance < self.config.importance_threshold:
                continue
            
            msg_tokens = self._count_tokens([msg])
            
            if total_tokens + msg_tokens > max_tokens:
                # 最后一条消息截断
                remaining = max_tokens - total_tokens
                if remaining > 50:
                    msg["content"] = msg["content"][:remaining * 4]
                    result.append(msg)
                break
            
            result.append(msg)
            total_tokens += msg_tokens
        
        # 按原始顺序排序
        original_order = {msg.get("_index", i): msg for i, msg in enumerate(messages)}
        result.sort(key=lambda x: original_order.get(x.get("_index", 0), 0))
        
        return result
    
    def _hybrid_compress(self, messages: List[Dict]) -> List[Dict]:
        """
        混合压缩策略 (推荐)
        
        结合多种方法：
        1. 保留系统提示
        2. 保留最近消息
        3. 摘要历史消息
        4. 过滤低重要性内容
        """
        result = []
        
        # 1. 保留系统提示
        system_msgs = [m for m in messages if m.get("role") == "system"]
        result.extend(system_msgs)
        
        # 2. 分析消息
        non_system = [m for m in messages if m.get("role") != "system"]
        
        if not non_system:
            return result
        
        # 3. 分类消息
        recent_count = min(self.config.preserve_recent, len(non_system))
        recent = non_system[-recent_count:]
        history = non_system[:-recent_count] if recent_count < len(non_system) else []
        
        # 4. 处理历史消息
        if history:
            # 按重要性分组
            important = []
            less_important = []
            
            for i, msg in enumerate(history):
                importance = self._calculate_importance(msg, i, history)
                if importance > self.config.importance_threshold:
                    important.append(msg)
                else:
                    less_important.append(msg)
            
            # 摘要不太重要的消息
            if less_important:
                summary = self._generate_summary(less_important)
                result.append({
                    "role": "system",
                    "content": f"[历史对话摘要]\n{summary}",
                    "_compressed": True
                })
            
            # 保留重要的原始消息
            result.extend(important[:10])  # 最多保留 10 条重要消息
        
        # 5. 添加最近消息
        result.extend(recent)
        
        return result
    
    def _calculate_importance(
        self,
        message: Dict,
        index: int,
        messages: List[Dict]
    ) -> float:
        """计算消息的重要性分数 (0-1)"""
        
        # 1. 角色权重
        role_weights = {
            "system": 1.0,
            "user": 0.9,
            "assistant": 0.8,
            "tool": 0.7,
            "function": 0.6
        }
        role = message.get("role", "user")
        score = role_weights.get(role, 0.5)
        
        # 2. 位置权重 (越近越重要)
        recency = 1.0 - (index / len(messages)) * 0.3
        score *= recency
        
        # 3. 内容特征
        content = message.get("content", "")
        
        # 包含决策或结论
        if any(kw in content for kw in ["所以", "因此", "结论", "决定", "solution", "result"]):
            score *= 1.2
        
        # 包含工具调用
        if message.get("tool_calls") or message.get("function_calls"):
            score *= 1.1
        
        # 包含错误
        if "error" in content.lower() or "failed" in content.lower():
            score *= 0.8
        
        # 长度适中最好
        length = len(content)
        if 100 < length < 2000:
            score *= 1.1
        elif length < 50:
            score *= 0.9
        
        return min(1.0, max(0.0, score))
    
    def _generate_summary(self, messages: List[Dict]) -> str:
        """生成消息摘要"""
        if not messages:
            return "无历史对话"
        
        # 统计信息
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        
        topics = self._extract_topics(messages)
        
        summary_parts = [
            f"历史对话 ({len(messages)} 条消息)",
            f"- 用户消息: {len(user_msgs)} 条",
            f"- 助手回复: {len(assistant_msgs)} 条",
            f"- 主要话题: {', '.join(topics[:5])}"
        ]
        
        # 关键点
        key_points = self._extract_key_points(messages)
        if key_points:
            summary_parts.append("- 关键决策:")
            for point in key_points[:3]:
                summary_parts.append(f"  • {point}")
        
        return "\n".join(summary_parts)
    
    def _extract_topics(self, messages: List[Dict]) -> List[str]:
        """提取话题"""
        # 简单的话题提取
        topics = []
        keywords = []
        
        for msg in messages:
            content = msg.get("content", "")
            # 提取 # 标签
            tags = re.findall(r'#(\w+)', content)
            keywords.extend(tags)
            
            # 提取关键词 (简化版)
            words = re.findall(r'\b[A-Za-z]\w+\b', content.lower())
            keywords.extend(words[:5])
        
        # 统计频率
        freq = {}
        for word in keywords:
            freq[word] = freq.get(word, 0) + 1
        
        # 排序
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        
        return [w for w, _ in sorted_words[:10]]
    
    def _extract_key_points(self, messages: List[Dict]) -> List[str]:
        """提取关键点"""
        key_points = []
        
        for msg in messages:
            content = msg.get("content", "")
            
            # 查找包含关键信息的句子
            sentences = re.split(r'[。！？\n]', content)
            for sent in sentences:
                if any(kw in sent for kw in ["决定", "选择", "使用", "创建", "result", "answer"]):
                    if len(sent) > 10 and len(sent) < 200:
                        key_points.append(sent.strip())
        
        return key_points[:10]
    
    def _count_tokens(self, messages: List[Dict]) -> int:
        """计算 token 数 (估算)"""
        total = 0
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            # 角色 overhead
            total += self.config.token_per_message
            
            # 内容
            if isinstance(content, str):
                total += len(content) // 4  # 英文约 4 字符/token
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        total += len(item.get("text", "")) // 4
                    else:
                        total += len(str(item)) // 4
        
        return total
    
    def _estimate_max_messages(self) -> int:
        """估算最大消息数"""
        return max(1, (self.config.max_tokens // self.config.token_per_message) - 2)
    
    def get_compression_report(
        self,
        original: List[Dict],
        compressed: List[Dict]
    ) -> Dict[str, Any]:
        """生成压缩报告"""
        original_tokens = self._count_tokens(original)
        compressed_tokens = self._count_tokens(compressed)
        
        return {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": compressed_tokens / max(1, original_tokens),
            "messages_reduced": len(original) - len(compressed),
            "messages_preserved": len(compressed),
            "saved_tokens": original_tokens - compressed_tokens
        }


# 便捷函数
def compress_context(
    messages: List[Dict],
    max_tokens: int = 8192,
    strategy: str = "hybrid"
) -> List[Dict]:
    """便捷的上下文压缩函数"""
    config = CompressionConfig(max_tokens=max_tokens)
    compressor = ContextCompressor(config)
    
    strategy_enum = CompressionStrategy(strategy)
    return compressor.compress_messages(messages, strategy_enum)
