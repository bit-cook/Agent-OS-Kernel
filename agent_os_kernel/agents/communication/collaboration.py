# -*- coding: utf-8 -*-
"""Agent Collaboration - 多 Agent 协作系统

整合消息传递、知识共享、群聊等功能，支持复杂的多 Agent 协作。

参考 AutoGen 群聊模式，提供：
1. 任务分解
2. 角色分配
3. 协作执行
4. 结果聚合
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型"""

    PARALLEL = "parallel"  # 并行任务
    SEQUENTIAL = "sequential"  # 顺序任务
    HIERARCHICAL = "hierarchical"  # 层级任务
    CONSENSUS = "consensus"  # 共识任务


@dataclass
class Task:
    """任务"""

    task_id: str
    task_type: TaskType
    description: str
    assigned_agent: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: int = 0


@dataclass
class CollaborationSession:
    """协作会话"""

    session_id: str
    name: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    agents: Dict[str, Dict] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "active"


class AgentCollaboration:
    """
    多 Agent 协作系统

    功能：
    1. 任务分解
    2. 角色分配
    3. 协作执行
    4. 结果聚合
    """

    def __init__(self, messenger=None, knowledge_sharing=None, group_chat=None):
        self.messenger = messenger
        self.knowledge = knowledge_sharing
        self.group_chat = group_chat

        self._sessions: Dict[str, CollaborationSession] = {}
        self._task_queue: asyncio.Queue = None
        self._running = False

    async def start(self):
        """启动协作系统"""
        self._running = True
        self._task_queue = asyncio.Queue()

        # 启动任务处理
        asyncio.create_task(self._task_processor())

        logger.info("Agent Collaboration started")

    async def stop(self):
        """停止协作系统"""
        self._running = False
        logger.info("Agent Collaboration stopped")

    async def create_session(self, session_id: str, name: str, agents: List[Dict]) -> str:
        """创建协作会话"""
        session = CollaborationSession(
            session_id=session_id, name=name, agents={a["id"]: a for a in agents}
        )

        self._sessions[session_id] = session

        # 注册 Agent 到消息系统
        if self.messenger:
            for agent in agents:
                await self.messenger.register_agent(agent["id"], agent["name"])

        logger.info(f"Session created: {name} ({len(agents)} agents)")
        return session_id

    async def add_task(
        self,
        session_id: str,
        task_id: str,
        task_type: TaskType,
        description: str,
        assigned_agent: str,
        dependencies: List[str] = None,
        priority: int = 0,
    ) -> str:
        """添加任务"""
        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        task = Task(
            task_id=task_id,
            task_type=task_type,
            description=description,
            assigned_agent=assigned_agent,
            dependencies=dependencies or [],
            priority=priority,
        )

        self._sessions[session_id].tasks[task_id] = task
        await self._task_queue.put((session_id, task_id))

        logger.info(f"Task added: {task_id} -> {assigned_agent}")

        return task_id

    async def _task_processor(self):
        """任务处理器"""
        while self._running:
            try:
                session_id, task_id = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)

                if session_id in self._sessions:
                    await self._execute_task(session_id, task_id)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Task processor error: {e}")

    async def _execute_task(self, session_id: str, task_id: str):
        """执行任务"""
        session = self._sessions[session_id]

        if task_id not in session.tasks:
            return

        task = session.tasks[task_id]

        # 检查依赖
        for dep_id in task.dependencies:
            if dep_id in session.tasks:
                dep_task = session.tasks[dep_id]
                if dep_task.status != "completed":
                    # 依赖未完成，重新入队
                    await self._task_queue.put((session_id, task_id))
                    return

        # 开始执行
        task.status = "running"
        task.started_at = datetime.now()

        logger.info(f"Task started: {task_id}")

        # 模拟任务执行
        await asyncio.sleep(0.5)

        # 生成结果
        task.result = {
            "status": "completed",
            "agent": task.assigned_agent,
            "output": f"Result of {task.description}",
        }
        task.status = "completed"
        task.completed_at = datetime.now()

        logger.info(f"Task completed: {task_id}")

    async def run_parallel(self, session_id: str, tasks: List[Dict]) -> List[Dict]:
        """并行执行任务"""
        results = []

        for task_def in tasks:
            task_id = await self.add_task(
                session_id=session_id,
                task_id=task_def["id"],
                task_type=TaskType.PARALLEL,
                description=task_def["description"],
                assigned_agent=task_def["agent"],
                priority=task_def.get("priority", 0),
            )
            results.append(task_id)

        # 等待所有任务完成
        session = self._sessions[session_id]

        while any(t.status != "completed" for t in session.tasks.values()):
            await asyncio.sleep(0.1)

        return results

    async def run_sequential(self, session_id: str, tasks: List[Dict]) -> List[Dict]:
        """顺序执行任务"""
        results = []

        for i, task_def in enumerate(tasks):
            # 设置依赖
            dependencies = [results[i - 1]] if i > 0 else []

            task_id = await self.add_task(
                session_id=session_id,
                task_id=task_def["id"],
                task_type=TaskType.SEQUENTIAL,
                description=task_def["description"],
                assigned_agent=task_def["agent"],
                dependencies=dependencies,
            )
            results.append(task_id)

        # 等待完成
        session = self._sessions[session_id]

        while any(t.status != "completed" for t in session.tasks.values()):
            await asyncio.sleep(0.1)

        return results

    async def delegate_task(
        self, from_agent: str, to_agent: str, task_description: str, priority: int = 0
    ):
        """委派任务"""
        if self.messenger:
            await self.messenger.send(
                message={
                    "msg_type": "task_delegation",
                    "sender_id": from_agent,
                    "sender_name": from_agent,
                    "content": f"Task delegated: {task_description}",
                    "receiver_id": to_agent,
                    "priority": priority,
                    "metadata": {"task": task_description},
                }
            )

    async def share_result(self, agent_id: str, result: Dict, task_id: str):
        """共享结果"""
        # 发送到群聊
        if self.group_chat and self._sessions:
            session = list(self._sessions.values())[0]
            await self.group_chat.send_message(
                chat_id=session.session_id,
                agent_id=agent_id,
                content=f"Task {task_id} completed: {json.dumps(result)[:200]}",
            )

        # 存储到知识共享
        if self.knowledge:
            from .knowledge_share import KnowledgePacket, KnowledgeType

            packet = KnowledgePacket.create(
                knowledge_type=KnowledgeType.EXPERIENCE,
                title=f"Result from {agent_id}",
                content=json.dumps(result),
                source_agent=agent_id,
                source_task=task_id,
                confidence=0.8,
            )
            await self.knowledge.share(packet)

    async def aggregate_results(self, session_id: str) -> Dict[str, Any]:
        """聚合结果"""
        if session_id not in self._sessions:
            return {}

        session = self._sessions[session_id]

        results = {
            task_id: task.result
            for task_id, task in session.tasks.items()
            if task.status == "completed"
        }

        # 生成聚合报告
        report = {
            "session_id": session_id,
            "total_tasks": len(session.tasks),
            "completed_tasks": len(results),
            "results": results,
            "summary": f"{len(results)}/{len(session.tasks)} tasks completed",
        }

        logger.info(f"Results aggregated: {report['summary']}")

        return report

    async def consensus_decision(
        self, session_id: str, topic: str, options: List[str]
    ) -> Dict[str, Any]:
        """共识决策"""
        # 发送到群聊投票
        if self.group_chat:
            await self.group_chat.send_message(
                chat_id=session_id,
                agent_id="system",
                content=f"Decision needed: {topic}\nOptions: {', '.join(options)}",
            )

        # 收集反馈
        # 简化：随机选择
        import random

        chosen = random.choice(options)

        return {"topic": topic, "chosen": chosen, "all_options": options, "method": "consensus"}

    def get_session_status(self, session_id: str) -> Dict:
        """获取会话状态"""
        if session_id not in self._sessions:
            return {}

        session = self._sessions[session_id]

        return {
            "session_id": session_id,
            "name": session.name,
            "status": session.status,
            "agents_count": len(session.agents),
            "tasks_count": len(session.tasks),
            "completed_tasks": sum(1 for t in session.tasks.values() if t.status == "completed"),
            "created_at": session.created_at.isoformat(),
        }

    async def end_session(self, session_id: str) -> Dict:
        """结束会话"""
        if session_id not in self._sessions:
            return {}

        session = self._sessions[session_id]

        # 聚合结果
        report = await self.aggregate_results(session_id)

        # 清理
        if self.messenger:
            for agent_id in session.agents.keys():
                await self.messenger.unregister_agent(agent_id)

        del self._sessions[session_id]

        logger.info(f"Session ended: {session_id}")

        return report


# 便捷函数
def create_collaboration(
    messenger=None, knowledge_sharing=None, group_chat=None
) -> AgentCollaboration:
    """创建协作系统"""
    return AgentCollaboration(messenger, knowledge_sharing, group_chat)
