# -*- coding: utf-8 -*-
"""
Agent Scheduler - 进程调度器

实现真正的操作系统级进程管理：
- 抢占式调度（优先级 + 时间片）
- 状态持久化（Checkpoint/恢复）
- 进程间通信（IPC）
- 优雅终止（Graceful Shutdown）

核心洞察（来自冯若航《AI Agent 的操作系统时刻》）：
- 当前 Agent 框架的核心都是 while loop，这不是真正的进程管理
- 真正的进程管理包括：并发调度、状态恢复、IPC、优雅终止
- 当 Agent 成为长期运行的服务，真正的需求才会浮现
"""

import time
import logging
from typing import Optional, Dict, Any, List, Callable, Tuple
from queue import PriorityQueue, Empty
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent 进程状态"""
    READY = "ready"           # 就绪，等待执行
    RUNNING = "running"       # 正在执行
    WAITING = "waiting"       # 等待资源（如 API 限流）
    SUSPENDED = "suspended"   # 被挂起（主动暂停）
    TERMINATED = "terminated" # 已终止
    ERROR = "error"           # 错误状态


@dataclass
class ResourceQuota:
    """资源配额配置"""
    max_tokens_per_window: int = 100000     # 每小时 token 上限
    max_api_calls_per_window: int = 1000    # 每小时 API 调用上限
    max_tokens_per_request: int = 10000     # 单次请求上限
    window_seconds: float = 3600            # 配额窗口（秒）


@dataclass
class AgentProcess:
    """
    Agent 进程控制块（PCB）
    
    类比操作系统进程控制块，记录 Agent 的完整状态。
    """
    pid: str
    name: str
    state: AgentState = AgentState.READY
    priority: int = 50                      # 优先级（0-100，越小越高）
    
    # 资源使用统计
    token_usage: int = 0
    api_calls: int = 0
    execution_time: float = 0.0
    cpu_time: float = 0.0                   # 实际 LLM 推理时间
    
    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)
    checkpoint_id: Optional[str] = None
    
    # 调度信息
    created_at: float = field(default_factory=time.time)
    last_run: float = 0.0
    started_at: Optional[float] = None
    terminated_at: Optional[float] = None
    time_slice: float = 60.0                # 时间片（秒）
    
    # 等待信息
    waiting_since: Optional[float] = None
    waiting_reason: Optional[str] = None
    
    # 错误处理
    error_count: int = 0
    last_error: Optional[str] = None
    max_errors: int = 3
    
    # 父进程（用于进程树）
    parent_pid: Optional[str] = None
    child_pids: List[str] = field(default_factory=list)
    
    def is_active(self) -> bool:
        """是否处于活动状态"""
        return self.state in (AgentState.READY, AgentState.RUNNING, AgentState.WAITING, AgentState.SUSPENDED)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'pid': self.pid,
            'name': self.name,
            'state': self.state.value,
            'priority': self.priority,
            'token_usage': self.token_usage,
            'api_calls': self.api_calls,
            'execution_time': self.execution_time,
            'cpu_time': self.cpu_time,
            'context': self.context,
            'checkpoint_id': self.checkpoint_id,
            'created_at': self.created_at,
            'last_run': self.last_run,
            'started_at': self.started_at,
            'terminated_at': self.terminated_at,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'parent_pid': self.parent_pid,
            'child_pids': self.child_pids,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentProcess':
        """从字典反序列化"""
        process = cls(
            pid=data['pid'],
            name=data['name'],
            state=AgentState(data['state']),
            priority=data.get('priority', 50),
            token_usage=data.get('token_usage', 0),
            api_calls=data.get('api_calls', 0),
            execution_time=data.get('execution_time', 0.0),
            cpu_time=data.get('cpu_time', 0.0),
            context=data.get('context', {}),
            checkpoint_id=data.get('checkpoint_id'),
            created_at=data.get('created_at', time.time()),
            last_run=data.get('last_run', 0.0),
            started_at=data.get('started_at'),
            terminated_at=data.get('terminated_at'),
            error_count=data.get('error_count', 0),
            last_error=data.get('last_error'),
            parent_pid=data.get('parent_pid'),
            child_pids=data.get('child_pids', []),
        )
        return process


@dataclass(order=True)
class SchedulableProcess:
    """可调度进程包装器（用于优先级队列）"""
    priority: int
    timestamp: float = field(compare=True)
    process: AgentProcess = field(compare=False)


class IPCChannel:
    """
    进程间通信通道
    
    实现 Agent 之间的消息传递机制。
    """
    
    def __init__(self, channel_name: str):
        self.name = channel_name
        self.messages: List[Dict] = []
        self.subscribers: List[str] = []  # 订阅者 PID 列表
    
    def send(self, from_pid: str, message: Any, message_type: str = "message"):
        """发送消息"""
        self.messages.append({
            'from': from_pid,
            'type': message_type,
            'content': message,
            'timestamp': time.time(),
        })
    
    def receive(self, to_pid: str, block: bool = False, timeout: float = 1.0) -> Optional[Dict]:
        """接收消息"""
        for msg in self.messages:
            if msg.get('to') is None or msg.get('to') == to_pid:
                self.messages.remove(msg)
                return msg
        return None
    
    def subscribe(self, pid: str):
        """订阅通道"""
        if pid not in self.subscribers:
            self.subscribers.append(pid)
    
    def get_pending_count(self) -> int:
        """获取待处理消息数"""
        return len(self.messages)


class ResourceQuotaManager:
    """
    资源配额管理器
    
    管理 API 调用、Token 使用等资源配额，防止单一 Agent 耗尽预算。
    """
    
    def __init__(self, quota: ResourceQuota):
        self.quota = quota
        self.current_usage = {'tokens': 0, 'api_calls': 0}
        self.per_agent_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'tokens': 0, 'api_calls': 0
        })
        self.window_start = time.time()
    
    def reset_if_needed(self):
        """检查并重置配额窗口"""
        current_time = time.time()
        if current_time - self.window_start >= self.quota.window_seconds:
            logger.info(f"Resetting quota window")
            self.current_usage = {'tokens': 0, 'api_calls': 0}
            self.per_agent_usage.clear()
            self.window_start = current_time
    
    def request_quota(self, agent_pid: str, tokens: int,
                     api_calls: int = 1) -> Tuple[bool, str]:
        """
        请求资源配额
        
        Returns:
            (是否批准, 原因)
        """
        self.reset_if_needed()
        
        # 检查全局配额
        if self.current_usage['tokens'] + tokens > self.quota.max_tokens_per_window:
            return False, "Global token quota exceeded"
        
        if self.current_usage['api_calls'] + api_calls > self.quota.max_api_calls_per_window:
            return False, "Global API call quota exceeded"
        
        # 检查单个请求限制
        if tokens > self.quota.max_tokens_per_request:
            return False, f"Request exceeds max tokens per request"
        
        # 检查单个 Agent 配额（最多 30%）
        agent_usage = self.per_agent_usage[agent_pid]
        max_per_agent_tokens = self.quota.max_tokens_per_window * 0.3
        max_per_agent_calls = self.quota.max_api_calls_per_window * 0.3
        
        if agent_usage['tokens'] + tokens > max_per_agent_tokens:
            return False, "Agent token quota exceeded (30% of global)"
        
        if agent_usage['api_calls'] + api_calls > max_per_agent_calls:
            return False, "Agent API call quota exceeded (30% of global)"
        
        # 批准并记录
        self.current_usage['tokens'] += tokens
        self.current_usage['api_calls'] += api_calls
        agent_usage['tokens'] += tokens
        agent_usage['api_calls'] += api_calls
        
        return True, "Approved"
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            'window_start': self.window_start,
            'window_elapsed': time.time() - self.window_start,
            'global_usage': self.current_usage.copy(),
            'global_limits': {
                'tokens': self.quota.max_tokens_per_window,
                'api_calls': self.quota.max_api_calls_per_window,
            },
            'usage_percent': {
                'tokens': (self.current_usage['tokens'] / self.quota.max_tokens_per_window) * 100,
                'api_calls': (self.current_usage['api_calls'] / self.quota.max_api_calls_per_window) * 100,
            },
            'per_agent_count': len(self.per_agent_usage),
        }


class AgentScheduler:
    """
    Agent 调度器 - 真正的操作系统级进程管理
    
    实现功能：
    1. 抢占式调度（优先级 + 时间片）
    2. 状态持久化（Checkpoint/恢复）
    3. 进程间通信（IPC 通道）
    4. 优雅终止（Graceful Shutdown）
    5. 资源配额管理
    
    使用示例：
        scheduler = AgentScheduler(time_slice=60.0)
        
        # 添加进程
        scheduler.add_process(process)
        
        # 调度循环
        while True:
            process = scheduler.schedule()
            if process:
                # 执行进程
                result = execute(process)
                
                # 创建检查点
                checkpoint_id = scheduler.suspend_process(process.pid)
                
                # 从检查点恢复
                scheduler.resume_process(process.pid, checkpoint_id)
    """
    
    def __init__(self, time_slice: float = 60.0,
                 quota: Optional[ResourceQuota] = None,
                 storage: Optional[Any] = None):
        """
        初始化调度器
        
        Args:
            time_slice: 默认时间片（秒）
            quota: 资源配额配置
            storage: 存储后端（用于检查点）
        """
        self.time_slice = time_slice
        self.storage = storage
        
        # 队列
        self.ready_queue: PriorityQueue[SchedulableProcess] = PriorityQueue()
        self.waiting_queue: Dict[str, AgentProcess] = {}
        
        # 进程表
        self.processes: Dict[str, AgentProcess] = {}
        self.running: Optional[AgentProcess] = None
        
        # IPC 通道
        self.ipc_channels: Dict[str, IPCChannel] = {}
        
        # 资源配额
        self.quota_manager = ResourceQuotaManager(quota or ResourceQuota())
        
        # 统计
        self.stats = {
            'total_scheduled': 0,
            'total_preempted': 0,
            'total_completed': 0,
            'total_errors': 0,
            'total_checkpoints': 0,
            'total_restores': 0,
        }
        
        # 优雅终止标志
        self._shutdown_requested = False
        self._shutdown_callbacks: List[Callable] = []
        
        logger.info(f"AgentScheduler initialized (time_slice={time_slice}s)")
    
    def add_process(self, process: AgentProcess):
        """
        添加新进程到调度队列
        
        Args:
            process: Agent 进程
        """
        self.processes[process.pid] = process
        self._enqueue(process)
        logger.info(f"Added process {process.name} (PID: {process.pid[:8]}...)")
    
    def _enqueue(self, process: AgentProcess):
        """将进程加入就绪队列"""
        process.state = AgentState.READY
        schedulable = SchedulableProcess(
            priority=process.priority,
            timestamp=time.time(),
            process=process
        )
        self.ready_queue.put(schedulable)
    
    def schedule(self) -> Optional[AgentProcess]:
        """
        调度下一个要执行的进程（抢占式调度）
        
        Returns:
            被调度的进程，如果没有则返回 None
        """
        if self._shutdown_requested:
            return None
        
        # 检查并重置配额
        self.quota_manager.reset_if_needed()
        
        # 检查当前进程是否需要抢占
        if self.running:
            if self._should_preempt(self.running):
                logger.debug(f"Preempting {self.running.name}")
                self._enqueue(self.running)
                self.running = None
                self.stats['total_preempted'] += 1
        
        # 检查等待队列中是否有进程可以唤醒
        self._check_waiting_queue()
        
        # 如果没有运行中的进程，从队列取一个
        if not self.running:
            try:
                schedulable = self.ready_queue.get(block=False)
                process = schedulable.process
                
                # 检查进程是否仍然有效
                if process.state == AgentState.TERMINATED:
                    return self.schedule()  # 递归获取下一个
                
                process.state = AgentState.RUNNING
                process.last_run = time.time()
                if process.started_at is None:
                    process.started_at = time.time()
                
                self.running = process
                self.stats['total_scheduled'] += 1
                
                logger.debug(f"Scheduled {process.name} (priority={process.priority})")
                
            except Empty:
                pass
        
        return self.running
    
    def _should_preempt(self, process: AgentProcess) -> bool:
        """
        判断是否应该抢占当前进程
        
        抢占条件：
        1. 时间片用完
        2. 有更高优先级的进程在等待
        3. 资源使用过多
        4. 进程执行时间过长
        """
        # 1. 时间片用完
        if time.time() - process.last_run > process.time_slice:
            logger.debug(f"Time slice expired for {process.name}")
            return True
        
        # 2. 有更高优先级的进程在等待
        if not self.ready_queue.empty():
            next_schedulable = self.ready_queue.queue[0]
            if next_schedulable.priority < process.priority - 10:
                logger.debug(f"Higher priority process waiting")
                return True
        
        # 3. 资源使用过多
        quota_stats = self.quota_manager.get_usage_stats()
        agent_usage = self.quota_manager.per_agent_usage.get(process.pid, {})
        if agent_usage.get('tokens', 0) > quota_stats['global_limits']['tokens'] * 0.3:
            logger.debug(f"Resource usage exceeded for {process.name}")
            return True
        
        return False
    
    def _check_waiting_queue(self):
        """检查等待队列，尝试唤醒进程"""
        to_wakeup = []
        
        for pid, process in self.waiting_queue.items():
            # 检查资源是否可用
            if process.waiting_reason and process.waiting_reason.startswith("quota"):
                approved, _ = self.quota_manager.request_quota(pid, 100, 0)
                if approved:
                    to_wakeup.append(pid)
            
            # 超时唤醒
            elif process.waiting_since and time.time() - process.waiting_since > 30:
                to_wakeup.append(pid)
        
        for pid in to_wakeup:
            self.wakeup_process(pid)
    
    def suspend_process(self, pid: str, create_checkpoint: bool = True) -> Optional[str]:
        """
        挂起进程（保存检查点）
        
        这是实现状态持久化的关键方法。
        
        Args:
            pid: 进程 ID
            create_checkpoint: 是否创建检查点
        
        Returns:
            检查点 ID（如果创建）
        """
        process = self.processes.get(pid)
        if not process:
            return None
        
        if self.running and self.running.pid == pid:
            self.running = None
        
        process.state = AgentState.SUSPENDED
        
        checkpoint_id = None
        if create_checkpoint and self.storage:
            try:
                checkpoint_id = self.storage.save_checkpoint(
                    agent_pid=pid,
                    process_state=process.to_dict(),
                    context_pages=[],  # 应该从 ContextManager 获取
                    description=f"Suspended at {time.time()}"
                )
                process.checkpoint_id = checkpoint_id
                self.stats['total_checkpoints'] += 1
                logger.info(f"Created checkpoint {checkpoint_id[:8]} for {process.name}")
            except Exception as e:
                logger.error(f"Failed to create checkpoint: {e}")
        
        return checkpoint_id
    
    def resume_process(self, pid: str, checkpoint_id: Optional[str] = None) -> bool:
        """
        恢复挂起的进程
        
        Args:
            pid: 进程 ID
            checkpoint_id: 检查点 ID（如果为 None，则从内存恢复）
        
        Returns:
            是否成功恢复
        """
        process = self.processes.get(pid)
        
        # 从检查点恢复
        if checkpoint_id and self.storage:
            checkpoint = self.storage.load_checkpoint(checkpoint_id)
            if checkpoint:
                process = AgentProcess.from_dict(checkpoint['process_state'])
                process.state = AgentState.READY
                self.processes[pid] = process
                self.stats['total_restores'] += 1
                logger.info(f"Restored process {process.name} from checkpoint {checkpoint_id[:8]}")
        
        if not process:
            return False
        
        if process.state == AgentState.SUSPENDED:
            self._enqueue(process)
            logger.info(f"Resumed process {process.name}")
            return True
        
        return False
    
    def terminate_process(self, pid: str, reason: str = "completed"):
        """
        终止进程
        
        实现优雅终止：给进程机会清理资源。
        """
        process = self.processes.get(pid)
        if not process:
            return
        
        # 调用终止回调
        for callback in self._shutdown_callbacks:
            try:
                callback(process)
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")
        
        process.state = AgentState.TERMINATED
        process.terminated_at = time.time()
        
        if self.running and self.running.pid == pid:
            self.running = None
        
        if pid in self.waiting_queue:
            del self.waiting_queue[pid]
        
        if reason == "error":
            self.stats['total_errors'] += 1
        else:
            self.stats['total_completed'] += 1
        
        logger.info(f"Terminated {process.name} (reason: {reason})")
    
    def request_resources(self, agent_pid: str, tokens: int,
                         api_calls: int = 1) -> bool:
        """请求资源配额"""
        approved, reason = self.quota_manager.request_quota(agent_pid, tokens, api_calls)
        
        if not approved:
            logger.warning(f"Resource request denied for {agent_pid[:8]}: {reason}")
            self.wait_process(agent_pid, reason)
        else:
            process = self.processes.get(agent_pid)
            if process:
                process.token_usage += tokens
                process.api_calls += api_calls
        
        return approved
    
    def wait_process(self, pid: str, reason: str = "waiting"):
        """将进程置为等待状态"""
        process = self.processes.get(pid)
        if not process:
            return
        
        if self.running and self.running.pid == pid:
            self.running = None
        
        process.state = AgentState.WAITING
        process.waiting_since = time.time()
        process.waiting_reason = reason
        self.waiting_queue[pid] = process
        
        logger.debug(f"Process {process.name} is now waiting ({reason})")
    
    def wakeup_process(self, pid: str):
        """唤醒等待中的进程"""
        if pid in self.waiting_queue:
            process = self.waiting_queue.pop(pid)
            process.waiting_since = None
            process.waiting_reason = None
            self._enqueue(process)
            logger.debug(f"Woke up process {process.name}")
    
    # ========== IPC 方法 ==========
    
    def create_ipc_channel(self, channel_name: str) -> IPCChannel:
        """创建 IPC 通道"""
        channel = IPCChannel(channel_name)
        self.ipc_channels[channel_name] = channel
        return channel
    
    def send_message(self, from_pid: str, to_pid: Optional[str],
                    channel_name: str, message: Any, msg_type: str = "message"):
        """发送 IPC 消息"""
        channel = self.ipc_channels.get(channel_name)
        if channel:
            channel.send(from_pid, message, msg_type)
            # 如果目标进程在等待，唤醒它
            if to_pid and to_pid in self.waiting_queue:
                self.wakeup_process(to_pid)
    
    def receive_message(self, pid: str, channel_name: str,
                       block: bool = False, timeout: float = 1.0) -> Optional[Dict]:
        """接收 IPC 消息"""
        channel = self.ipc_channels.get(channel_name)
        if channel:
            return channel.receive(pid, block, timeout)
        return None
    
    # ========== 优雅终止 ==========
    
    def request_shutdown(self, timeout: float = 30.0):
        """请求优雅终止"""
        logger.info("Shutdown requested, stopping scheduler...")
        self._shutdown_requested = True
        
        # 为所有运行中的进程创建检查点
        if self.running:
            self.suspend_process(self.running.pid)
        
        for pid, process in self.processes.items():
            if process.is_active():
                self.suspend_process(pid)
    
    def register_shutdown_callback(self, callback: Callable):
        """注册终止回调"""
        self._shutdown_callbacks.append(callback)
    
    # ========== 统计 ==========
    
    def get_process_stats(self) -> Dict[str, Any]:
        """获取进程统计"""
        states = defaultdict(int)
        for p in self.processes.values():
            states[p.state.value] += 1
        
        return {
            **self.stats,
            'total_processes': len(self.processes),
            'active_processes': len([p for p in self.processes.values() if p.is_active()]),
            'running': self.running.name if self.running else None,
            'ready_queue_size': self.ready_queue.qsize(),
            'waiting_queue_size': len(self.waiting_queue),
            'state_distribution': dict(states),
            'quota_usage': self.quota_manager.get_usage_stats(),
        }
