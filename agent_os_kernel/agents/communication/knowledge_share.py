# -*- coding: utf-8 -*-
"""Knowledge Sharing - 跨 Agent 知识共享

支持：
1. 知识提取
2. 知识压缩
3. 知识存储
4. 知识检索
5. 知识验证
6. 知识融合
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import re

logger = logging.getLogger(__name__)


class KnowledgeType(Enum):
    """知识类型"""

    FACT = "fact"  # 事实
    PROCEDURE = "procedure"  # 步骤/流程
    INSIGHT = "insight"  # 洞察
    PATTERN = "pattern"  # 模式
    PRINCIPLE = "principle"  # 原则
    EXPERIENCE = "experience"  # 经验
    LESSON = "lesson"  # 教训
    TECHNIQUE = "technique"  # 技巧


@dataclass
class KnowledgePacket:
    """知识包"""

    packet_id: str
    knowledge_type: KnowledgeType
    title: str
    content: str
    source_agent: str
    source_task: str
    confidence: float  # 0-1, 置信度
    usefulness: float  # 0-1, 有用性
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    verified: bool = False
    verification_count: int = 0
    usage_count: int = 0
    last_used: Optional[datetime] = None
    related_packets: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        knowledge_type: KnowledgeType,
        title: str,
        content: str,
        source_agent: str,
        source_task: str,
        confidence: float = 0.8,
        tags: List[str] = None,
    ) -> "KnowledgePacket":
        """创建知识包"""
        packet_id = hashlib.md5(f"{title}:{content}:{source_agent}".encode()).hexdigest()[:16]

        return cls(
            packet_id=packet_id,
            knowledge_type=knowledge_type,
            title=title,
            content=content,
            source_agent=source_agent,
            source_task=source_task,
            confidence=confidence,
            usefulness=0.5,  # 初始有用性
            tags=tags or [],
        )

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "packet_id": self.packet_id,
            "knowledge_type": self.knowledge_type.value,
            "title": self.title,
            "content": self.content,
            "source_agent": self.source_agent,
            "source_task": self.source_task,
            "confidence": self.confidence,
            "usefulness": self.usefulness,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "verified": self.verified,
            "verification_count": self.verification_count,
            "usage_count": self.usage_count,
            "related_packets": self.related_packets,
        }


class KnowledgeExtractor:
    """知识提取器"""

    @staticmethod
    async def extract_from_text(text: str, agent_name: str, task: str) -> List[KnowledgePacket]:
        """从文本提取知识"""
        knowledge_list = []

        # 提取事实
        facts = KnowledgeExtractor._extract_facts(text)
        for fact in facts:
            knowledge_list.append(
                KnowledgePacket.create(
                    knowledge_type=KnowledgeType.FACT,
                    title=f"Fact from {agent_name}",
                    content=fact,
                    source_agent=agent_name,
                    source_task=task,
                    confidence=0.8,
                )
            )

        # 提取步骤
        procedures = KnowledgeExtractor._extract_procedures(text)
        for proc in procedures:
            knowledge_list.append(
                KnowledgePacket.create(
                    knowledge_type=KnowledgeType.PROCEDURE,
                    title=f"Procedure from {agent_name}",
                    content=proc,
                    source_agent=agent_name,
                    source_task=task,
                    confidence=0.7,
                    tags=["procedure"],
                )
            )

        # 提取教训
        lessons = KnowledgeExtractor._extract_lessons(text)
        for lesson in lessons:
            knowledge_list.append(
                KnowledgePacket.create(
                    knowledge_type=KnowledgeType.LESSON,
                    title=f"Lesson from {agent_name}",
                    content=lesson,
                    source_agent=agent_name,
                    source_task=task,
                    confidence=0.9,
                    tags=["lesson"],
                )
            )

        return knowledge_list

    @staticmethod
    def _extract_facts(text: str) -> List[str]:
        """提取事实"""
        facts = []

        # 识别 "X 是 Y" 模式
        patterns = [
            r"([^。！？]+)是([^。！？]+)",
            r"([^。！？]+)包含([^。！？]+)",
            r"需要([^。！？]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) >= 2:
                    facts.append(f"{match[0]} 是 {match[1]}")

        return facts[:10]  # 限制数量

    @staticmethod
    def _extract_procedures(text: str) -> List[str]:
        """提取步骤"""
        procedures = []

        # 识别步骤模式
        patterns = [
            r"第一步[：:]([^。！？]+)",
            r"第二步[：:]([^。！？]+)",
            r"第三步[：:]([^。！？]+)",
            r"首先[，,]([^。！？]+)",
            r"然后[，,]([^。！？]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            procedures.extend(matches)

        return procedures[:5]

    @staticmethod
    def _extract_lessons(text: str) -> List[str]:
        """提取教训"""
        lessons = []

        # 识别教训模式
        patterns = [
            r"([^。！？]+)错误",
            r"([^。！？]+)失败",
            r"([^。！？]+)避免",
            r"注意([^。！？]+)",
            r"应该([^。！？]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            lessons.extend(matches)

        return lessons[:5]


class KnowledgeSharing:
    """
    知识共享系统

    功能：
    1. 知识存储
    2. 知识检索
    3. 知识验证
    4. 知识融合
    5. 知识进化
    """

    def __init__(self, storage_dir: str = "./knowledge"):
        self.storage_dir = storage_dir
        self._knowledge_base: Dict[str, KnowledgePacket] = {}
        self._tag_index: Dict[str, set] = {}
        self._type_index: Dict[KnowledgeType, set] = {}
        self._agent_index: Dict[str, set] = {}
        self._lock = asyncio.Lock()

        import os

        os.makedirs(storage_dir, exist_ok=True)

    async def share(self, packet: KnowledgePacket, verify: bool = True) -> str:
        """共享知识"""
        async with self._lock:
            # 检查是否已存在
            if packet.packet_id in self._knowledge_base:
                # 更新
                existing = self._knowledge_base[packet.packet_id]
                existing.verification_count += 1
                if packet.confidence > existing.confidence:
                    existing.confidence = packet.confidence
                logger.info(f"Knowledge updated: {packet.packet_id}")
            else:
                # 添加
                self._knowledge_base[packet.packet_id] = packet

                # 更新索引
                self._update_indexes(packet)

                logger.info(f"Knowledge shared: {packet.packet_id}")

            return packet.packet_id

    async def share_batch(self, packets: List[KnowledgePacket], verify: bool = True) -> List[str]:
        """批量共享"""
        ids = []
        for packet in packets:
            packet_id = await self.share(packet, verify)
            ids.append(packet_id)
        return ids

    def _update_indexes(self, packet: KnowledgePacket):
        """更新索引"""
        # 标签索引
        for tag in packet.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(packet.packet_id)

        # 类型索引
        if packet.knowledge_type not in self._type_index:
            self._type_index[packet.knowledge_type] = set()
        self._type_index[packet.knowledge_type].add(packet.packet_id)

        # Agent 索引
        if packet.source_agent not in self._agent_index:
            self._agent_index[packet.source_agent] = set()
        self._agent_index[packet.source_agent].add(packet.packet_id)

    async def retrieve(
        self,
        query: str,
        knowledge_type: KnowledgeType = None,
        tags: List[str] = None,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[Tuple[KnowledgePacket, float]]:
        """检索知识"""
        results = []

        async with self._lock:
            candidates = list(self._knowledge_base.values())

        # 简单关键词匹配
        query_words = set(query.lower().split())

        for packet in candidates:
            # 过滤
            if knowledge_type and packet.knowledge_type != knowledge_type:
                continue

            if packet.confidence < min_confidence:
                continue

            # 计算相关性分数
            score = self._calculate_relevance(packet, query_words)

            if score > 0:
                results.append((packet, score))

        # 排序
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def _calculate_relevance(self, packet: KnowledgePacket, query_words: set) -> float:
        """计算相关性分数"""
        score = 0.0

        # 标题匹配
        title_words = set(packet.title.lower().split())
        score += len(query_words & title_words) * 0.3

        # 内容匹配
        content_words = set(packet.content.lower().split())
        score += len(query_words & content_words) * 0.2

        # 标签匹配
        tag_words = set(t.lower() for t in packet.tags)
        score += len(query_words & tag_words) * 0.5

        # 置信度权重
        score *= packet.confidence

        return score

    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        async with self._lock:
            return {
                "total_knowledge": len(self._knowledge_base),
                "by_type": {kt.value: len(s) for kt, s in self._type_index.items()},
                "by_tags": len(self._tag_index),
                "by_agents": len(self._agent_index),
                "avg_confidence": self._get_avg_confidence(),
                "verified_count": sum(1 for p in self._knowledge_base.values() if p.verified),
            }

    def _get_avg_confidence(self) -> float:
        """获取平均置信度"""
        if not self._knowledge_base:
            return 0.0
        return sum(p.confidence for p in self._knowledge_base.values()) / len(self._knowledge_base)

    async def verify(self, packet_id: str) -> bool:
        """验证知识"""
        async with self._lock:
            if packet_id in self._knowledge_base:
                packet = self._knowledge_base[packet_id]
                packet.verified = True
                packet.verification_count += 1
                return True
            return False

    async def merge(self, packet_ids: List[str]) -> Optional[KnowledgePacket]:
        """融合知识"""
        packets = []
        async with self._lock:
            for pid in packet_ids:
                if pid in self._knowledge_base:
                    packets.append(self._knowledge_base[pid])

        if len(packets) < 2:
            return None

        # 合并内容
        combined_content = "\n".join(p.content for p in packets)
        combined_tags = list(set(t for p in packets for t in p.tags))

        avg_confidence = sum(p.confidence for p in packets) / len(packets)

        merged = KnowledgePacket.create(
            knowledge_type=KnowledgeType.INSIGHT,
            title=f"Merged from {len(packets)} sources",
            content=combined_content[:500],
            source_agent="system",
            source_task="merge",
            confidence=avg_confidence,
            tags=combined_tags[:5],
        )

        await self.share(merged)

        return merged

    async def get_agent_knowledge(self, agent_id: str) -> List[KnowledgePacket]:
        """获取 Agent 的知识"""
        async with self._lock:
            if agent_id not in self._agent_index:
                return []
            packet_ids = list(self._agent_index[agent_id])

        return [self._knowledge_base[pid] for pid in packet_ids if pid in self._knowledge_base]

    async def clear(self, agent_id: str = None):
        """清空知识"""
        async with self._lock:
            if agent_id:
                if agent_id in self._agent_index:
                    for pid in self._agent_index[agent_id]:
                        if pid in self._knowledge_base:
                            del self._knowledge_base[pid]
                    del self._agent_index[agent_id]
            else:
                self._knowledge_base.clear()
                self._tag_index.clear()
                self._type_index.clear()
                self._agent_index.clear()

        logger.info(f"Knowledge cleared for: {agent_id or 'all'}")


# 便捷函数
def create_knowledge_sharing(storage_dir: str = "./knowledge") -> KnowledgeSharing:
    """创建知识共享系统"""
    return KnowledgeSharing(storage_dir)
