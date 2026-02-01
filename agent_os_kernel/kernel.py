# -*- coding: utf-8 -*-
"""
Agent OS Kernel - 主内核

真正填补"缺失的内核"，将五大子系统整合为统一的 Agent 运行时环境：
1. 内存管理（Context Manager）- 虚拟内存式上下文管理
2. 外存管理（Storage）- PostgreSQL 五重角色
3. 进程管理（Scheduler）- 真正的进程调度
4. I/O 管理（Tools）- Agent-Native CLI
5. 安全与可观测性（Security & Observability）- 三层信任基础设施

核心洞察（来自冯若航《AI Agent 的操作系统时刻》）：
- 我们正站在 1991 年的时刻——所有工具都已就位，唯独缺少一个内核
- 这个内核将把一切粘合起来：统一的上下文调度、可恢复的进程状态、
  标准化的 I/O 接口、完整的信任基础设施与可观测性
- 谁是 Agent 时代的 Linus Torvalds？
"""

import uuid
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

from .core.types import AgentState
from .core.context_manager import ContextManager, ContextPage
from .core.scheduler import AgentScheduler, AgentProcess, ResourceQuota
from .core.storage import StorageManager, StorageBackend
from .core.security import SecurityPolicy, PermissionLevel
from .tools.registry import ToolRegistry
from .tools.builtin import (
    CalculatorTool,
    FileReadTool,
    FileWriteTool,
    PythonExecuteTool,
    SearchTool,
)


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class KernelStats:
    """内核统计信息"""
    version: str = "0.2.0"
    start_time: float = 0.0
    total_agents: int = 0
    active_agents: int = 0
    total_iterations: int = 0
    total_tokens: int = 0
    total_api_calls: int = 0
    avg_cache_hit_rate: float = 0.0


class AgentOSKernel:
    """
    Agent OS Kernel - 主内核
    
    这是 Agent 生态中"缺失的内核"，提供操作系统级的 Agent 运行时环境。
    
    示例：
        # 初始化内核
        kernel = AgentOSKernel(
            max_context_tokens=128000,
            storage=StorageManager.from_postgresql("postgresql://...")
        )
        
        # 创建 Agent
        agent_pid = kernel.spawn_agent(
            name="CodeAssistant",
            task="帮我写一个 Python 爬虫",
            priority=30
        )
        
        # 运行内核（调度循环）
        kernel.run(max_iterations=100)
        
        # 创建检查点（状态持久化）
        checkpoint_id = kernel.create_checkpoint(agent_pid)
        
        # 从检查点恢复
        new_pid = kernel.restore_checkpoint(checkpoint_id)
    
    Attributes:
        version: 内核版本
        context_manager: 上下文管理器（虚拟内存）
        scheduler: 进程调度器
        storage: 存储管理器（PostgreSQL 五重角色）
        tool_registry: 工具注册表（Agent-Native CLI）
    """
    
    VERSION = "0.2.0"
    
    def __init__(self,
                 max_context_tokens: int = 128000,
                 time_slice: float = 60.0,
                 storage_backend: Optional[StorageBackend] = None,
                 quota: Optional[ResourceQuota] = None,
                 enable_sandbox: bool = False):
        """
        初始化 Agent OS Kernel
        
        Args:
            max_context_tokens: 最大上下文 token 数（默认 128K）
            time_slice: 调度时间片（秒）
            storage_backend: 存储后端（默认内存存储）
            quota: 资源配额配置
            enable_sandbox: 是否启用沙箱（需要 Docker）
        """
        logger.info("=" * 70)
        logger.info("Agent OS Kernel v%s - The Missing Kernel for AI Agents", self.VERSION)
        logger.info("=" * 70)
        logger.info("Initializing five subsystems...")
        
        # 1. 存储层（必须先初始化，供其他子系统使用）
        self.storage = StorageManager(storage_backend)
        logger.info("[1/5] Storage Layer ready (PostgreSQL Five Roles)")
        
        # 2. 上下文管理器（虚拟内存）
        self.context_manager = ContextManager(
            max_context_tokens=max_context_tokens,
            storage_backend=self.storage.backend
        )
        logger.info("[2/5] Context Manager ready (Virtual Memory)")
        
        # 3. 进程调度器
        self.scheduler = AgentScheduler(
            time_slice=time_slice,
            quota=quota or ResourceQuota(),
            storage=self.storage
        )
        logger.info("[3/5] Process Scheduler ready (True Process Management)")
        
        # 4. 工具注册表（Agent-Native CLI）
        self.tool_registry = ToolRegistry()
        self._register_builtin_tools()
        logger.info("[4/5] I/O Manager ready (Agent-Native CLI)")
        
        # 5. 安全子系统
        self.security = None
        if enable_sandbox:
            from .core.security import SandboxManager
            self.security = SandboxManager()
            logger.info("[5/5] Security Subsystem ready (Sandbox + Observability)")
        else:
            logger.info("[5/5] Security Subsystem ready (Observability only)")
        
        # 统计
        self.stats = KernelStats(start_time=time.time())
        
        # 钩子
        self.pre_step_hooks: List[Callable] = []
        self.post_step_hooks: List[Callable] = []
        
        # 运行标志
        self._running = False
        self._shutdown_requested = False
        
        logger.info("")
        logger.info("All systems ready. Agent OS Kernel initialized.")
        logger.info("")
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        tools = [
            CalculatorTool(),
            FileReadTool(),
            FileWriteTool(),
            PythonExecuteTool(),
            SearchTool(),
        ]
        
        for tool in tools:
            self.tool_registry.register(tool, category="builtin")
        
        logger.info("  Registered %d built-in tools", len(tools))
    
    def spawn_agent(self,
                   name: str,
                   task: str,
                   priority: int = 50,
                   policy: Optional[SecurityPolicy] = None,
                   context: Optional[Dict] = None) -> str:
        """
        创建并启动一个新 Agent（类比操作系统 fork）
        
        Args:
            name: Agent 名称
            task: 任务描述
            priority: 优先级（0-100，越小越优先）
            policy: 安全策略
            context: 额外上下文
        
        Returns:
            Agent PID
        """
        # 1. 创建进程
        process = AgentProcess(
            pid=str(uuid.uuid4()),
            name=name,
            priority=priority
        )
        
        # 2. 初始化上下文（L1 Cache：System Prompt）
        system_prompt = f"You are {name}. Your task: {task}"
        system_page = self.context_manager.allocate_page(
            agent_pid=process.pid,
            content=system_prompt,
            importance=1.0,  # 最高重要性
            page_type="system"
        )
        
        # 3. 初始化任务上下文（L2 Cache：Working Memory）
        task_page = self.context_manager.allocate_page(
            agent_pid=process.pid,
            content=f"Current task: {task}",
            importance=0.9,
            page_type="task"
        )
        
        # 4. 注册工具定义（L2 Cache：Tools）
        tool_schema = self.tool_registry.get_tool_schemas()
        tools_page = self.context_manager.allocate_page(
            agent_pid=process.pid,
            content=f"Available tools: {tool_schema}",
            importance=0.8,
            page_type="tools"
        )
        
        process.context = {
            'system_page': system_page,
            'task_page': task_page,
            'tools_page': tools_page,
            'task': task,
            'custom': context or {}
        }
        
        # 5. 应用安全策略
        if policy:
            process.context['security_policy'] = policy.to_dict() if hasattr(policy, 'to_dict') else policy
        
        # 6. 创建沙箱
        if self.security and policy:
            self.security.create_sandbox(process.pid, policy)
        
        # 7. 保存到存储（长期记忆）
        self.storage.save_process(process)
        
        # 8. 加入调度队列
        self.scheduler.add_process(process)
        
        self.stats.total_agents += 1
        
        logger.info("✓ Spawned agent: %s (PID: %s...)", name, process.pid[:8])
        logger.info("  Task: %s", task)
        logger.info("  Priority: %d", priority)
        logger.info("  Context pages: 3 (System + Task + Tools)")
        logger.info("")
        
        return process.pid
    
    def create_checkpoint(self, agent_pid: str, 
                         description: str = "") -> Optional[str]:
        """
        创建检查点（状态持久化）
        
        这是实现可靠 Agent 的关键：即使系统崩溃，也能从检查点恢复。
        
        Args:
            agent_pid: Agent PID
            description: 检查点描述
        
        Returns:
            检查点 ID
        """
        process = self.scheduler.processes.get(agent_pid)
        if not process:
            logger.error("Agent %s... not found", agent_pid[:8])
            return None
        
        # 1. 挂起进程
        checkpoint_id = self.scheduler.suspend_process(agent_pid, create_checkpoint=True)
        
        if checkpoint_id:
            # 2. 保存上下文页面到存储
            page_ids = self.context_manager.agent_pages.get(agent_pid, [])
            context_pages = []
            
            for page_id in page_ids:
                page = self.context_manager.pages_in_memory.get(page_id) or \
                       self.context_manager.swapped_pages.get(page_id)
                if page:
                    context_pages.append(page.to_dict())
                    # 将页面写回存储
                    self.storage.save_context_page(page)
            
            logger.info("✓ Created checkpoint %s... for agent %s... (%d pages)",
                       checkpoint_id[:8], agent_pid[:8], len(context_pages))
            
            return checkpoint_id
        
        return None
    
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[str]:
        """
        从检查点恢复 Agent
        
        Args:
            checkpoint_id: 检查点 ID
        
        Returns:
            新的 Agent PID
        """
        # 1. 加载检查点
        checkpoint = self.storage.load_checkpoint(checkpoint_id)
        if not checkpoint:
            logger.error("Checkpoint %s... not found", checkpoint_id[:8])
            return None
        
        # 2. 恢复进程状态
        old_pid = checkpoint['agent_pid']
        process = AgentProcess.from_dict(checkpoint['process_state'])
        process.pid = str(uuid.uuid4())  # 分配新 PID
        process.state = AgentState.READY
        process.checkpoint_id = checkpoint_id
        
        # 3. 恢复上下文页面
        for page_data in checkpoint.get('context_pages', []):
            page = ContextPage.from_dict(page_data)
            # 标记为 swapped，需要时自动换入
            page.status = PageStatus.SWAPPED
            self.context_manager.swapped_pages[page.page_id] = page
            self.context_manager.agent_pages[process.pid].append(page.page_id)
        
        # 4. 加入调度队列
        self.scheduler.add_process(process)
        
        logger.info("✓ Restored agent %s... from checkpoint %s... (new PID: %s...)",
                   old_pid[:8], checkpoint_id[:8], process.pid[:8])
        
        return process.pid
    
    def execute_agent_step(self, process: AgentProcess) -> Dict[str, Any]:
        """
        执行 Agent 的一步推理
        
        子类应该重写这个方法来实现具体的 LLM 调用。
        
        Args:
            process: Agent 进程
        
        Returns:
            执行结果
        """
        # 1. 执行前置钩子
        for hook in self.pre_step_hooks:
            hook(process)
        
        # 2. 获取上下文（触发虚拟内存换入）
        context = self.context_manager.get_agent_context(
            process.pid,
            optimize_for_cache=True
        )
        
        # 3. 检查资源配额
        tokens_needed = len(context.split()) * 2  # 粗略估计
        if not self.scheduler.request_resources(process.pid, tokens_needed):
            return {'success': False, 'error': 'Resource quota exceeded', 'done': False}
        
        # 4. 模拟 LLM 推理（子类应该重写）
        logger.info("[%s] Thinking...", process.name)
        time.sleep(0.1)
        
        # 5. 模拟决策
        reasoning = f"Processing task: {process.context.get('task', 'unknown')}"
        
        # 6. 记录审计日志（可观测性）
        self.storage.log_action(
            agent_pid=process.pid,
            action_type="reasoning",
            input_data={'context_length': len(context)},
            output_data={'reasoning': reasoning},
            reasoning=reasoning
        )
        
        # 7. 执行后置钩子
        for hook in self.post_step_hooks:
            hook(process)
        
        return {
            'success': True,
            'reasoning': reasoning,
            'done': False  # 由具体实现决定
        }
    
    def run(self, max_iterations: Optional[int] = None):
        """
        运行内核主循环（类比操作系统启动）
        
        Args:
            max_iterations: 最大迭代次数（None 表示无限）
        """
        logger.info("Starting Agent OS Kernel main loop...")
        logger.info("")
        
        self._running = True
        iteration = 0
        
        try:
            while self._running and not self._shutdown_requested:
                # 检查最大迭代次数
                if max_iterations and iteration >= max_iterations:
                    logger.info("Max iterations reached, stopping...")
                    break
                
                # 调度下一个 Agent
                process = self.scheduler.schedule()
                
                if process:
                    try:
                        # 执行 Agent 步骤
                        result = self.execute_agent_step(process)
                        
                        # 更新统计
                        self.stats.total_iterations += 1
                        self.stats.total_tokens += len(result.get('reasoning', '').split())
                        
                        # 检查是否完成
                        if result.get('done'):
                            self.scheduler.terminate_process(process.pid, "completed")
                        
                        # 检查错误
                        elif not result.get('success'):
                            process.error_count += 1
                            process.last_error = result.get('error')
                            
                            if process.error_count >= process.max_errors:
                                self.scheduler.terminate_process(process.pid, "error")
                            else:
                                # 短暂等待后重试
                                self.scheduler.wait_process(process.pid, "error_recovery")
                    
                    except Exception as e:
                        logger.exception("Error executing agent step")
                        process.error_count += 1
                        process.last_error = str(e)
                        
                        if process.error_count >= process.max_errors:
                            self.scheduler.terminate_process(process.pid, "error")
                
                else:
                    # 没有可调度进程，短暂休眠
                    time.sleep(0.1)
                
                iteration += 1
        
        except KeyboardInterrupt:
            logger.info("Interrupted, shutting down...")
            self.shutdown()
        
        finally:
            self._running = False
            logger.info("Kernel main loop stopped.")
    
    def shutdown(self, timeout: float = 30.0):
        """
        优雅关闭内核
        
        为所有运行中的 Agent 创建检查点，确保状态不丢失。
        """
        logger.info("Shutting down Agent OS Kernel...")
        self._shutdown_requested = True
        
        # 为所有活动进程创建检查点
        for pid, process in self.scheduler.processes.items():
            if process.is_active():
                self.create_checkpoint(pid, description="Graceful shutdown")
        
        # 关闭存储连接
        self.storage.close()
        
        logger.info("Kernel shutdown complete.")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取内核统计信息"""
        return {
            'version': self.VERSION,
            'uptime': time.time() - self.stats.start_time,
            'total_agents': self.stats.total_agents,
            'active_agents': len([p for p in self.scheduler.processes.values() if p.is_active()]),
            'total_iterations': self.stats.total_iterations,
            'context_stats': self.context_manager.get_stats(),
            'scheduler_stats': self.scheduler.get_process_stats(),
        }
    
    def print_status(self):
        """打印系统状态"""
        stats = self.get_stats()
        
        print("\n" + "=" * 70)
        print("Agent OS Kernel Status")
        print("=" * 70)
        print(f"Version:        {stats['version']}")
        print(f"Uptime:         {stats['uptime']:.1f}s")
        print(f"Total Agents:   {stats['total_agents']}")
        print(f"Active Agents:  {stats['active_agents']}")
        print(f"Iterations:     {stats['total_iterations']}")
        print("")
        print("Context Manager:")
        ctx_stats = stats['context_stats']
        print(f"  Usage:        {ctx_stats['current_usage']}/{ctx_stats['max_tokens']} tokens ({ctx_stats['usage_percent']:.1f}%)")
        print(f"  Pages:        {ctx_stats['pages_in_memory']} in memory, {ctx_stats['pages_swapped']} swapped")
        print(f"  Cache Hit:    {ctx_stats.get('cache_hit_rate', 0):.1%}")
        print("")
        print("Scheduler:")
        sched_stats = stats['scheduler_stats']
        print(f"  Running:      {sched_stats['running'] or 'None'}")
        print(f"  Ready Queue:  {sched_stats['ready_queue_size']}")
        print(f"  Waiting:      {sched_stats['waiting_queue_size']}")
        print("=" * 70 + "\n")


# 导入 PageStatus
from .core.context_manager import PageStatus
