# -*- coding: utf-8 -*-
"""Enhanced Memory - 增强的记忆系统

参考 CrewAI 和 AutoGPT 的记忆设计
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import logging
from threading import Lock
import hashlib

logger = logging.getLogger(__name__)


class MemoryType:
    """记忆类型"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    ENTITY = "entity"
    WORKING = "working"


@dataclass
class MemoryItem:
    """记忆条目"""
    
    id: str
    content: str
    memory_type: str
    
    # 元数据
    importance: float = 0.5  # 0-1 重要性
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 来源
    source: str = "agent"
    agent_id: Optional[str] = None
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    # 嵌入 (可选)
    embedding: Optional[List[float]] = None
    
    # 访问计数
    access_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata,
            "source": self.source,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "embedding": self.embedding,
            "access_count": self.access_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryItem':
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=data["memory_type"],
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            source=data.get("source", "agent"),
            agent_id=data.get("agent_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if isinstance(data["last_accessed"], str) else data["last_accessed"],
            embedding=data.get("embedding"),
            access_count=data.get("access_count", 0),
        )


class ShortTermMemory:
    """短期记忆 - 对话历史
    
    参考 LangChain ConversationBufferMemory
    """
    
    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self._memories: List[MemoryItem] = []
        self._lock = Lock()
        
        logger.info(f"ShortTermMemory initialized (max={max_entries})")
    
    def add(
        self,
        content: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """添加记忆"""
        with self._lock:
            item = MemoryItem(
                id=str(uuid4())[:8],
                content=content,
                memory_type=MemoryType.SHORT_TERM,
                importance=importance,
                tags=tags or [],
                **kwargs
            )
            
            self._memories.append(item)
            
            # 清理旧记忆
            if len(self._memories) > self.max_entries:
                self._memories = self._memories[-self.max_entries:]
            
            logger.debug(f"Short-term memory added: {item.id}")
            return item.id
    
    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """获取最近的记忆"""
        with self._lock:
            return list(self._memories[-limit:])
    
    def get_all(self) -> List[MemoryItem]:
        """获取所有记忆"""
        with self._lock:
            return list(self._memories)
    
    def clear(self):
        """清除所有记忆"""
        with self._lock:
            self._memories.clear()
            logger.info("Short-term memory cleared")
    
    def get_stats(self) -> Dict:
        return {
            "type": "short_term",
            "count": len(self._memories),
            "max_entries": self.max_entries,
        }


class LongTermMemory:
    """长期记忆 - 向量存储
    
    参考 CrewAI 和 AutoGPT 的记忆系统
    """
    
    def __init__(
        self,
        embedding_func: Optional[callable] = None,
        similarity_threshold: float = 0.7,
        max_entries: int = 10000
    ):
        self.embedding_func = embedding_func
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        
        self._memories: Dict[str, MemoryItem] = {}
        self._index: Dict[str, List[str]] = {}  # tag -> memory_ids
        self._lock = Lock()
        
        logger.info(
            f"LongTermMemory initialized "
            f"(threshold={similarity_threshold}, max={max_entries})"
        )
    
    def add(
        self,
        content: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        embedding: Optional[List[float]] = None,
        **kwargs
    ) -> str:
        """添加记忆"""
        with self._lock:
            # 生成或使用 embedding
            if embedding is None and self.embedding_func:
                embedding = self.embedding_func(content)
            
            item = MemoryItem(
                id=str(uuid4())[:8],
                content=content,
                memory_type=MemoryType.LONG_TERM,
                importance=importance,
                tags=tags or [],
                embedding=embedding,
                **kwargs
            )
            
            self._memories[item.id] = item
            
            # 更新索引
            for tag in item.tags:
                if tag not in self._index:
                    self._index[tag] = []
                self._index[tag].append(item.id)
            
            # 检查是否需要总结
            if len(self._memories) > self.max_entries:
                self._summarize_oldest()
            
            logger.debug(f"Long-term memory added: {item.id}")
            return item.id
    
    def search(
        self,
        query: str,
        limit: int = 5,
        tags: Optional[List[str]] = None
    ) -> List[MemoryItem]:
        """搜索记忆"""
        with self._lock:
            results = []
            
            # 如果有 embedding，使用向量搜索
            if self.embedding_func:
                query_embedding = self.embedding_func(query)
                
                for item in self._memories.values():
                    if item.embedding is not None:
                        similarity = self._cosine_similarity(
                            query_embedding,
                            item.embedding
                        )
                        if similarity >= self.similarity_threshold:
                            item.access_count += 1
                            item.last_accessed = datetime.now(timezone.utc)
                            results.append((item, similarity))
                
                # 按相似度排序
                results.sort(key=lambda x: x[1], reverse=True)
                items = [r[0] for r in results[:limit]]
            
            # 否则使用关键词搜索
            else:
                query_words = query.lower().split()
                
                for item in self._memories.values():
                    if any(word in item.content.lower() for word in query_words):
                        item.access_count += 1
                        item.last_accessed = datetime.now(timezone.utc)
                        results.append(item)
                
                items = results[:limit]
            
            # 按标签过滤
            if tags:
                items = [i for i in items if any(t in i.tags for t in tags)]
            
            return items
    
    def get_by_tag(self, tag: str) -> List[MemoryItem]:
        """按标签获取"""
        with self._lock:
            ids = self._index.get(tag, [])
            return [self._memories[i] for i in ids if i in self._memories]
    
    def _cosine_similarity(
        self, 
        a: List[float], 
        b: List[float]
    ) -> float:
        """计算余弦相似度"""
        import math
        
        if not a or not b:
            return 0.0
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    def _summarize_oldest(self):
        """总结最旧的记忆"""
        # 按创建时间排序
        sorted_items = sorted(
            self._memories.values(),
            key=lambda x: x.created_at
        )
        
        # 删除最旧的 10%
        to_remove = sorted_items[:len(sorted_items) // 10]
        
        for item in to_remove:
            del self._memories[item.id]
            for tag in item.tags:
                if tag in self._index and item.id in self._index[tag]:
                    self._index[tag].remove(item.id)
        
        logger.debug(f"Summarized {len(to_remove)} old memories")
    
    def clear(self):
        """清除所有记忆"""
        with self._lock:
            self._memories.clear()
            self._index.clear()
            logger.info("Long-term memory cleared")
    
    def get_stats(self) -> Dict:
        return {
            "type": "long_term",
            "count": len(self._memories),
            "max_entries": self.max_entries,
            "tags": len(self._index),
        }


class EntityMemory:
    """实体记忆 - 追踪实体信息
    
    参考 LangChain EntityMemory
    """
    
    def __init__(self, embedding_func: Optional[callable] = None):
        self.embedding_func = embedding_func
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        
        logger.info("EntityMemory initialized")
    
    def extract_entities(self, text: str) -> List[str]:
        """从文本中提取实体 (简化版)"""
        # 简单实现：提取大写开头的词
        import re
        words = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text)
        return list(set(words))
    
    def update_entity(
        self,
        entity_name: str,
        description: str,
        observations: List[str]
    ):
        """更新实体信息"""
        with self._lock:
            if entity_name not in self._entities:
                self._entities[entity_name] = {
                    "description": description,
                    "observations": [],
                    "updated_at": datetime.now(timezone.utc),
                }
            
            self._entities[entity_name]["observations"].extend(observations)
            self._entities[entity_name]["updated_at"] = datetime.now(timezone.utc)
            
            logger.debug(f"Entity updated: {entity_name}")
    
    def get_entity(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """获取实体信息"""
        with self._lock:
            return self._entities.get(entity_name)
    
    def search_entities(self, query: str) -> List[str]:
        """搜索实体"""
        with self._lock:
            query_lower = query.lower()
            return [
                name for name, info in self._entities.items()
                if query_lower in info["description"].lower()
                or any(query_lower in obs.lower() for obs in info["observations"])
            ]
    
    def clear(self):
        """清除所有实体"""
        with self._lock:
            self._entities.clear()
            logger.info("Entity memory cleared")
    
    def get_stats(self) -> Dict:
        return {
            "type": "entity",
            "count": len(self._entities),
        }


class EnhancedMemory:
    """增强的记忆管理器
    
    整合所有类型的记忆
    """
    
    def __init__(
        self,
        embedding_func: Optional[callable] = None,
        short_term_max: int = 100,
        long_term_max: int = 10000
    ):
        """初始化增强记忆系统"""
        self.short_term = ShortTermMemory(max_entries=short_term_max)
        self.long_term = LongTermMemory(
            embedding_func=embedding_func,
            max_entries=long_term_max
        )
        self.entity = EntityMemory(embedding_func=embedding_func)
        
        logger.info("EnhancedMemory initialized")
    
    def add(
        self,
        content: str,
        memory_type: str = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """添加记忆"""
        if memory_type == MemoryType.SHORT_TERM:
            return self.short_term.add(
                content, importance, tags, **kwargs
            )
        elif memory_type == MemoryType.LONG_TERM:
            return self.long_term.add(
                content, importance, tags, **kwargs
            )
        elif memory_type == MemoryType.ENTITY:
            entities = self.entity.extract_entities(content)
            for entity in entities:
                self.entity.update_entity(
                    entity_name=entity,
                    description=content[:200],
                    observations=[content]
                )
            return ",".join(entities)
        else:
            return self.short_term.add(content, importance, tags, **kwargs)
    
    def search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> List[MemoryItem]:
        """搜索记忆"""
        if memory_type:
            if memory_type == MemoryType.LONG_TERM:
                return self.long_term.search(query, limit=limit)
            else:
                return self.short_term.get_recent(limit)
        
        # 搜索所有类型
        results = self.long_term.search(query, limit=limit)
        
        # 添加短期记忆
        results.extend(self.short_term.get_recent(limit - len(results)))
        
        return results[:limit]
    
    def clear(self, memory_type: Optional[str] = None):
        """清除记忆"""
        if memory_type == MemoryType.SHORT_TERM:
            self.short_term.clear()
        elif memory_type == MemoryType.LONG_TERM:
            self.long_term.clear()
        elif memory_type == MemoryType.ENTITY:
            self.entity.clear()
        else:
            self.short_term.clear()
            self.long_term.clear()
            self.entity.clear()
    
    def get_stats(self) -> Dict:
        return {
            "short_term": self.short_term.get_stats(),
            "long_term": self.long_term.get_stats(),
            "entity": self.entity.get_stats(),
        }
