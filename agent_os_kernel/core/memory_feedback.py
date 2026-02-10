# -*- coding: utf-8 -*-
"""Memory Feedback - 记忆反馈系统

支持自然语言纠正、补充、替换记忆内容。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型"""
    CORRECT = "correct"       # 纠正错误
    SUPPLEMENT = "supplement"  # 补充信息
    REPLACE = "replace"        # 替换内容
    DELETE = "delete"          # 删除记忆


@dataclass
class MemoryFeedback:
    """记忆反馈"""
    feedback_id: str
    memory_id: str
    feedback_type: FeedbackType
    original_content: str
    feedback_content: str
    reason: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    applied: bool = False
    applied_at: Optional[datetime] = None


class MemoryFeedbackSystem:
    """记忆反馈系统"""
    
    def __init__(
        self,
        memory_system = None
    ):
        """
        初始化记忆反馈系统
        
        Args:
            memory_system: 关联的记忆系统
        """
        self.memory_system = memory_system
        self._feedbacks: Dict[str, MemoryFeedback] = {}
        self._lock = asyncio.Lock()
        
        logger.info("MemoryFeedbackSystem initialized")
    
    async def create_feedback(
        self,
        memory_id: str,
        feedback_type: FeedbackType,
        feedback_content: str,
        reason: str,
        original_content: str = ""
    ) -> str:
        """
        创建反馈
        
        Args:
            memory_id: 记忆 ID
            feedback_type: 反馈类型
            feedback_content: 反馈内容
            reason: 反馈原因
            original_content: 原始内容
            
        Returns:
            反馈 ID
        """
        feedback_id = str(uuid4())
        
        feedback = MemoryFeedback(
            feedback_id=feedback_id,
            memory_id=memory_id,
            feedback_type=feedback_type,
            original_content=original_content,
            feedback_content=feedback_content,
            reason=reason
        )
        
        async with self._lock:
            self._feedbacks[feedback_id] = feedback
        
        logger.info(f"Feedback created: {feedback_id}")
        
        return feedback_id
    
    async def apply_feedback(self, feedback_id: str) -> bool:
        """
        应用反馈
        
        Args:
            feedback_id: 反馈 ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            if feedback_id not in self._feedbacks:
                return False
            
            feedback = self._feedbacks[feedback_id]
            feedback.applied = True
            feedback.applied_at = datetime.utcnow()
        
        logger.info(f"Feedback applied: {feedback_id}")
        
        return True
    
    async def get_pending_feedbacks(self) -> List[MemoryFeedback]:
        """获取待处理的反馈"""
        async with self._lock:
            return [f for f in self._feedbacks.values() if not f.applied]
    
    async def get_feedback_history(self, memory_id: str) -> List[MemoryFeedback]:
        """获取记忆的反馈历史"""
        async with self._lock:
            return [
                f for f in self._feedbacks.values()
                if f.memory_id == memory_id
            ]
    
    async def delete_feedback(self, feedback_id: str) -> bool:
        """删除反馈"""
        async with self._lock:
            if feedback_id in self._feedbacks:
                del self._feedbacks[feedback_id]
                return True
        return False
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = len(self._feedbacks)
        applied = sum(1 for f in self._feedbacks.values() if f.applied)
        
        return {
            "total_feedbacks": total,
            "pending": total - applied,
            "applied": applied,
            "correct_count": sum(1 for f in self._feedbacks.values() if f.feedback_type == FeedbackType.CORRECT),
            "supplement_count": sum(1 for f in self._feedbacks.values() if f.feedback_type == FeedbackType.SUPPLEMENT),
            "replace_count": sum(1 for f in self._feedbacks.values() if f.feedback_type == FeedbackType.REPLACE)
        }
