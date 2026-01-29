"""
Agent OS Kernel - 核心实现
基于操作系统设计原理的 AI Agent 运行时内核
"""

import uuid
import time
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Callable
from queue import PriorityQueue
from collections import defaultdict
from abc import ABC, abstractmethod


# ============================================================================
# 1. 基础数据结构
# ============================================================================

class AgentState(Enum):
    """Agent 进程状态"""
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


@dataclass
class AgentProcess:
    """Agent 进程控制块 (PCB)"""
    pid: str
    name: str
    state: AgentState = AgentState.READY
    priority: int = 50  # 0-100, 数字越小优先级越高
    
    # 资源使用统计
    token_usage: int = 0
    api_calls: int = 0
    execution_time: float = 0
    
    # 上下文和状态
    context: Dict[str, Any] = field(default_factory=dict)
    checkpoint_id: Optional[str] = None
    
    # 时间戳
    created_at: float = field(default_factory=time.time)
    last_run: float = field(default_factory=time.time)
    cpu_time: float = 0  # 实际推理时间
    
    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        data = asdict(self)
        data['state'] = self.state.value
        return data


@dataclass
class ContextPage:
    """上下文页面（内存页）"""
    page_id: str
    agent_pid: str
    content: str
    tokens: int
    importance_score: float = 0.5
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)


# ============================================================================
# 2. Context Manager (上下文管理器)
# ============================================================================

class ContextManager:
    """
    上下文管理器 - 类似操作系统的虚拟内存管理
    
    实现功能：
    1. 上下文窗口管理（RAM）
    2. 页面置换算法（LRU + 重要性）
    3. 上下文换入换出（swap）
    """
    
    def __init__(self, max_context_tokens: int = 100000):
        self.max_context_tokens = max_context_tokens
        self.current_usage = 0
        
        # 当前在"内存"中的页面
        self.pages_in_memory: Dict[str, ContextPage] = {}
        
        # 换出到"磁盘"的页面（简化版，实际应存数据库）
        self.swapped_pages: Dict[str, ContextPage] = {}
        
        # 每个 Agent 的页面列表
        self.agent_pages: Dict[str, List[str]] = defaultdict(list)
    
    def allocate_page(self, agent_pid: str, content: str, 
                     importance: float = 0.5) -> str:
        """
        分配新的上下文页面
        """
        page_id = str(uuid.uuid4())
        tokens = len(content.split())  # 简化的 token 计数
        
        # 检查是否需要换出页面
        while self.current_usage + tokens > self.max_context_tokens:
            if not self._swap_out_page():
                raise MemoryError("Cannot allocate more context - all pages are critical")
        
        # 创建新页面
        page = ContextPage(
            page_id=page_id,
            agent_pid=agent_pid,
            content=content,
            tokens=tokens,
            importance_score=importance
        )
        
        self.pages_in_memory[page_id] = page
        self.agent_pages[agent_pid].append(page_id)
        self.current_usage += tokens
        
        return page_id
    
    def access_page(self, page_id: str) -> Optional[ContextPage]:
        """
        访问页面（可能触发页面换入）
        """
        # 检查是否在内存中
        if page_id in self.pages_in_memory:
            page = self.pages_in_memory[page_id]
            page.access_count += 1
            page.last_accessed = time.time()
            return page
        
        # 页面在磁盘上，需要换入
        if page_id in self.swapped_pages:
            self._swap_in_page(page_id)
            return self.pages_in_memory[page_id]
        
        return None
    
    def _swap_out_page(self) -> bool:
        """
        换出一个页面（LRU + 重要性评分）
        """
        if not self.pages_in_memory:
            return False
        
        # 计算每个页面的"受害者分数"（越高越应该被换出）
        victim_scores = []
        current_time = time.time()
        
        for page_id, page in self.pages_in_memory.items():
            # 综合考虑：
            # 1. 最后访问时间（越久越应该换出）
            # 2. 访问频率（越低越应该换出）
            # 3. 重要性评分（越低越应该换出）
            
            time_score = (current_time - page.last_accessed) / 3600  # 归一化到小时
            freq_score = 1.0 / (page.access_count + 1)  # 访问越少分数越高
            importance_penalty = 1.0 - page.importance_score  # 重要性越低分数越高
            
            total_score = (
                time_score * 0.4 +
                freq_score * 0.3 +
                importance_penalty * 0.3
            )
            
            victim_scores.append((page_id, total_score))
        
        # 选择得分最高的（最应该被换出的）
        victim_id, _ = max(victim_scores, key=lambda x: x[1])
        victim_page = self.pages_in_memory[victim_id]
        
        # 执行换出
        del self.pages_in_memory[victim_id]
        self.swapped_pages[victim_id] = victim_page
        self.current_usage -= victim_page.tokens
        
        print(f"[Context] Swapped out page {victim_id[:8]}... ({victim_page.tokens} tokens)")
        return True
    
    def _swap_in_page(self, page_id: str):
        """
        换入一个页面
        """
        page = self.swapped_pages[page_id]
        
        # 确保有足够空间
        while self.current_usage + page.tokens > self.max_context_tokens:
            self._swap_out_page()
        
        # 执行换入
        self.pages_in_memory[page_id] = page
        del self.swapped_pages[page_id]
        self.current_usage += page.tokens
        
        print(f"[Context] Swapped in page {page_id[:8]}... ({page.tokens} tokens)")
    
    def get_agent_context(self, agent_pid: str) -> str:
        """
        获取 Agent 的完整上下文
        """
        page_ids = self.agent_pages.get(agent_pid, [])
        pages = [self.access_page(pid) for pid in page_ids if pid]
        pages = [p for p in pages if p is not None]
        
        # 按重要性和访问时间排序
        pages.sort(key=lambda p: (p.importance_score, -p.last_accessed), reverse=True)
        
        return "\n\n".join(p.content for p in pages)


# ============================================================================
# 3. Agent Scheduler (进程调度器)
# ============================================================================

class AgentScheduler:
    """
    Agent 调度器
    
    实现功能：
    1. 优先级调度
    2. 时间片轮转
    3. 抢占式调度
    4. 资源配额管理
    """
    
    def __init__(self, time_slice: float = 60.0):
        self.time_slice = time_slice  # 时间片（秒）
        
        # 就绪队列（优先级队列）
        self.ready_queue = PriorityQueue()
        
        # 所有进程
        self.processes: Dict[str, AgentProcess] = {}
        
        # 当前运行的进程
        self.running: Optional[AgentProcess] = None
        
        # 资源配额
        self.hourly_token_quota = 100000
        self.hourly_api_quota = 1000
        self.current_token_usage = 0
        self.current_api_usage = 0
        self.quota_reset_time = time.time() + 3600
    
    def add_process(self, process: AgentProcess):
        """添加新进程到调度队列"""
        self.processes[process.pid] = process
        self._enqueue(process)
        print(f"[Scheduler] Added process {process.name} (PID: {process.pid[:8]}...)")
    
    def _enqueue(self, process: AgentProcess):
        """将进程加入就绪队列"""
        process.state = AgentState.READY
        # 优先级队列：(优先级, 时间戳, 进程)
        # 优先级数字越小越优先
        self.ready_queue.put((process.priority, time.time(), process))
    
    def schedule(self) -> Optional[AgentProcess]:
        """
        调度下一个要执行的进程
        """
        # 重置配额（如果需要）
        self._check_quota_reset()
        
        # 检查当前进程是否需要抢占
        if self.running:
            if self._should_preempt(self.running):
                print(f"[Scheduler] Preempting {self.running.name}")
                self._enqueue(self.running)
                self.running = None
        
        # 如果没有运行中的进程，从队列取一个
        if not self.running and not self.ready_queue.empty():
            _, _, process = self.ready_queue.get()
            process.state = AgentState.RUNNING
            process.last_run = time.time()
            self.running = process
            print(f"[Scheduler] Scheduled {process.name}")
        
        return self.running
    
    def _should_preempt(self, process: AgentProcess) -> bool:
        """
        判断是否应该抢占当前进程
        """
        # 1. 时间片用完
        if time.time() - process.last_run > self.time_slice:
            return True
        
        # 2. 有更高优先级的进程在等待
        if not self.ready_queue.empty():
            next_priority, _, _ = self.ready_queue.queue[0]
            if next_priority < process.priority - 10:  # 优先级差距超过 10
                return True
        
        # 3. 资源使用过多
        if process.token_usage > self.hourly_token_quota * 0.3:
            return True
        
        return False
    
    def _check_quota_reset(self):
        """检查并重置配额"""
        if time.time() >= self.quota_reset_time:
            self.current_token_usage = 0
            self.current_api_usage = 0
            self.quota_reset_time = time.time() + 3600
            print("[Scheduler] Quota reset")
    
    def request_resources(self, agent_pid: str, tokens: int, api_calls: int = 1) -> bool:
        """
        请求资源配额
        """
        if (self.current_token_usage + tokens > self.hourly_token_quota or
            self.current_api_usage + api_calls > self.hourly_api_quota):
            return False
        
        self.current_token_usage += tokens
        self.current_api_usage += api_calls
        
        process = self.processes.get(agent_pid)
        if process:
            process.token_usage += tokens
            process.api_calls += api_calls
        
        return True
    
    def terminate_process(self, pid: str):
        """终止进程"""
        process = self.processes.get(pid)
        if process:
            process.state = AgentState.TERMINATED
            if self.running and self.running.pid == pid:
                self.running = None
            print(f"[Scheduler] Terminated {process.name}")


# ============================================================================
# 4. Tool System (工具调用系统)
# ============================================================================

class Tool(ABC):
    """工具抽象基类"""
    
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def description(self) -> str:
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        pass


class SimpleTool(Tool):
    """简单工具包装器"""
    
    def __init__(self, name: str, description: str, func: Callable):
        self._name = name
        self._description = description
        self._func = func
    
    def name(self) -> str:
        return self._name
    
    def description(self) -> str:
        return self._description
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            result = self._func(**kwargs)
            return {
                "success": True,
                "data": result,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        self.tools[tool.name()] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {
                "name": tool.name(),
                "description": tool.description()
            }
            for tool in self.tools.values()
        ]


# ============================================================================
# 5. Storage Layer (存储层 - 简化版)
# ============================================================================

class StorageManager:
    """
    存储管理器（简化版，使用内存模拟数据库）
    生产环境应使用 PostgreSQL
    """
    
    def __init__(self):
        self.processes_db: Dict[str, dict] = {}
        self.checkpoints_db: Dict[str, dict] = {}
        self.audit_logs: List[dict] = []
    
    def save_process(self, process: AgentProcess):
        """保存进程状态"""
        self.processes_db[process.pid] = process.to_dict()
    
    def load_process(self, pid: str) -> Optional[AgentProcess]:
        """加载进程状态"""
        data = self.processes_db.get(pid)
        if data:
            # 重建进程对象（简化版）
            process = AgentProcess(
                pid=data['pid'],
                name=data['name'],
                priority=data['priority']
            )
            process.state = AgentState(data['state'])
            process.token_usage = data['token_usage']
            process.context = data['context']
            return process
        return None
    
    def save_checkpoint(self, process: AgentProcess) -> str:
        """保存检查点"""
        checkpoint_id = str(uuid.uuid4())
        self.checkpoints_db[checkpoint_id] = {
            'checkpoint_id': checkpoint_id,
            'process': process.to_dict(),
            'timestamp': time.time()
        }
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[dict]:
        """加载检查点"""
        return self.checkpoints_db.get(checkpoint_id)
    
    def log_action(self, agent_pid: str, action_type: str, 
                   input_data: dict, output_data: dict, reasoning: str):
        """记录审计日志"""
        self.audit_logs.append({
            'agent_pid': agent_pid,
            'action_type': action_type,
            'input': input_data,
            'output': output_data,
            'reasoning': reasoning,
            'timestamp': time.time()
        })
    
    def get_audit_trail(self, agent_pid: str) -> List[dict]:
        """获取审计追踪"""
        return [
            log for log in self.audit_logs
            if log['agent_pid'] == agent_pid
        ]


# ============================================================================
# 6. Agent OS Kernel (核心系统)
# ============================================================================

class AgentOSKernel:
    """
    Agent OS Kernel - 主内核
    
    整合所有子系统，提供统一的 Agent 运行时环境
    """
    
    def __init__(self):
        print("=" * 60)
        print("Agent OS Kernel v0.1")
        print("=" * 60)
        
        # 初始化子系统
        self.context_manager = ContextManager(max_context_tokens=100000)
        self.scheduler = AgentScheduler(time_slice=60.0)
        self.tool_registry = ToolRegistry()
        self.storage = StorageManager()
        
        # 注册一些示例工具
        self._register_builtin_tools()
        
        print("[Kernel] Initialized successfully")
        print()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        
        # 计算器工具
        def calculator(expression: str) -> str:
            try:
                result = eval(expression)  # 注意：生产环境不应直接 eval
                return f"Result: {result}"
            except Exception as e:
                return f"Error: {e}"
        
        self.tool_registry.register(SimpleTool(
            name="calculator",
            description="Evaluate mathematical expressions",
            func=calculator
        ))
        
        # 搜索工具（模拟）
        def search(query: str) -> str:
            return f"Search results for '{query}': [Mock result 1, Mock result 2]"
        
        self.tool_registry.register(SimpleTool(
            name="search",
            description="Search for information",
            func=search
        ))
    
    def spawn_agent(self, name: str, task: str, priority: int = 50) -> str:
        """
        创建并启动一个新 Agent
        """
        # 1. 创建进程
        process = AgentProcess(
            pid=str(uuid.uuid4()),
            name=name,
            priority=priority
        )
        
        # 2. 初始化上下文
        system_prompt = f"You are {name}. Your task: {task}"
        page_id = self.context_manager.allocate_page(
            agent_pid=process.pid,
            content=system_prompt,
            importance=1.0  # 系统提示最重要
        )
        
        process.context['system_page'] = page_id
        process.context['task'] = task
        
        # 3. 保存到存储
        self.storage.save_process(process)
        
        # 4. 加入调度队列
        self.scheduler.add_process(process)
        
        print(f"✓ Spawned agent: {name} (PID: {process.pid[:8]}...)")
        print(f"  Task: {task}")
        print(f"  Priority: {priority}")
        print()
        
        return process.pid
    
    def execute_agent_step(self, process: AgentProcess) -> dict:
        """
        执行 Agent 的一步推理
        （这里用简化的模拟，实际应调用 LLM API）
        """
        # 1. 获取上下文
        context = self.context_manager.get_agent_context(process.pid)
        
        # 2. 模拟 LLM 推理
        print(f"[Agent {process.name}] Thinking...")
        time.sleep(0.5)  # 模拟推理延迟
        
        # 3. 模拟决策（实际应该是 LLM 的输出）
        reasoning = f"I need to work on: {process.context.get('task', 'unknown task')}"
        action = {
            "tool": "calculator",
            "parameters": {"expression": "2 + 2"}
        }
        
        # 4. 请求资源配额
        tokens_needed = 1000
        if not self.scheduler.request_resources(process.pid, tokens_needed):
            print(f"[Agent {process.name}] Quota exceeded, waiting...")
            return {"done": False, "waiting": True}
        
        # 5. 执行工具调用
        tool = self.tool_registry.get(action['tool'])
        if tool:
            result = tool.execute(**action['parameters'])
        else:
            result = {"success": False, "error": "Tool not found"}
        
        # 6. 记录审计日志
        self.storage.log_action(
            agent_pid=process.pid,
            action_type="tool_call",
            input_data={"context": context, "action": action},
            output_data=result,
            reasoning=reasoning
        )
        
        # 7. 更新上下文
        result_text = f"Action: {action}\nResult: {result}"
        self.context_manager.allocate_page(
            agent_pid=process.pid,
            content=result_text,
            importance=0.7
        )
        
        print(f"[Agent {process.name}] Executed: {action['tool']}")
        print(f"  Reasoning: {reasoning}")
        print(f"  Result: {result}")
        print()
        
        return {
            "done": True,  # 模拟：一步就完成
            "reasoning": reasoning,
            "action": action,
            "result": result
        }
    
    def run(self, max_iterations: int = 10):
        """
        主事件循环
        """
        print("=" * 60)
        print("Starting Agent OS Kernel main loop...")
        print("=" * 60)
        print()
        
        for i in range(max_iterations):
            print(f"--- Iteration {i + 1}/{max_iterations} ---")
            
            # 调度下一个 Agent
            process = self.scheduler.schedule()
            
            if not process:
                print("No processes to schedule")
                time.sleep(1)
                continue
            
            # 执行一步
            try:
                result = self.execute_agent_step(process)
                
                # 检查是否完成
                if result.get('done'):
                    self.scheduler.terminate_process(process.pid)
                    print(f"✓ Agent {process.name} completed")
                
            except Exception as e:
                print(f"✗ Error in agent {process.name}: {e}")
                self.scheduler.terminate_process(process.pid)
            
            print()
            time.sleep(0.5)
        
        print("=" * 60)
        print("Agent OS Kernel shutdown")
        print("=" * 60)
    
    def print_status(self):
        """打印系统状态"""
        print("\n" + "=" * 60)
        print("System Status")
        print("=" * 60)
        
        print(f"\n[Context Manager]")
        print(f"  Memory usage: {self.context_manager.current_usage} / {self.context_manager.max_context_tokens} tokens")
        print(f"  Pages in memory: {len(self.context_manager.pages_in_memory)}")
        print(f"  Pages swapped out: {len(self.context_manager.swapped_pages)}")
        
        print(f"\n[Scheduler]")
        print(f"  Active processes: {len(self.scheduler.processes)}")
        print(f"  Token quota: {self.scheduler.current_token_usage} / {self.scheduler.hourly_token_quota}")
        print(f"  API quota: {self.scheduler.current_api_usage} / {self.scheduler.hourly_api_quota}")
        
        print(f"\n[Storage]")
        print(f"  Processes stored: {len(self.storage.processes_db)}")
        print(f"  Checkpoints: {len(self.storage.checkpoints_db)}")
        print(f"  Audit logs: {len(self.storage.audit_logs)}")
        
        print("=" * 60 + "\n")


# ============================================================================
# 7. 使用示例
# ============================================================================

if __name__ == "__main__":
    # 初始化内核
    kernel = AgentOSKernel()
    
    # 创建几个 Agent
    kernel.spawn_agent(
        name="CodeAssistant",
        task="Help write Python code",
        priority=30
    )
    
    kernel.spawn_agent(
        name="ResearchAssistant",
        task="Research AI papers",
        priority=50
    )
    
    kernel.spawn_agent(
        name="DataAnalyst",
        task="Analyze sales data",
        priority=40
    )
    
    # 运行主循环
    kernel.run(max_iterations=5)
    
    # 打印最终状态
    kernel.print_status()
    
    # 查看审计日志
    print("\n" + "=" * 60)
    print("Audit Trail (First Agent)")
    print("=" * 60)
    
    first_agent_pid = list(kernel.scheduler.processes.keys())[0]
    audit_trail = kernel.storage.get_audit_trail(first_agent_pid)
    
    for log in audit_trail:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log['timestamp']))}]")
        print(f"Action: {log['action_type']}")
        print(f"Reasoning: {log['reasoning']}")
        print(f"Result: {log['output']}")
