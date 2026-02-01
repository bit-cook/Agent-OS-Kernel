# -*- coding: utf-8 -*-
"""
Context Manager - 上下文管理器

实现操作系统级的虚拟内存机制：
- 将 LLM 上下文窗口视为 RAM（有限、快速、昂贵）
- 将数据库存储视为 Disk（无限、慢速、便宜）
- 自动页面置换（LRU + 重要性 + 语义相似度）
- 透明的 swap in/out
- KV-Cache 优化（静态内容前置）

核心洞察（来自冯若航《AI Agent 的操作系统时刻》）：
1. 上下文窗口是 LLM 最稀缺的资源（类比 640KB 内存限制）
2. KV-Cache 命中率是最重要的性能指标（Manus 经验）
3. 需要内存层次结构（L1/L2/RAM/Disk - DeepSeek Engram 论文）
"""

import uuid
import time
import heapq
import logging
from typing import Optional, Dict, Any, List, Set, Tuple, Callable
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class PageStatus(Enum):
    """页面状态"""
    IN_MEMORY = "in_memory"      # 在内存中（Context Window 内）
    SWAPPED = "swapped"          # 已换出到磁盘（数据库）
    DIRTY = "dirty"              # 已修改但未写回


@dataclass
class ContextPage:
    """
    上下文页面 - 类比虚拟内存的页
    
    Attributes:
        page_id: 页面唯一标识
        agent_pid: 所属 Agent
        content: 页面内容
        tokens: Token 数（估算）
        importance_score: 重要性评分 0-1
        page_type: 页面类型（system/tools/user/task/memory）
        status: 当前状态
        access_count: 访问次数
        last_accessed: 最后访问时间
        created_at: 创建时间
        embedding: 语义嵌入向量（可选）
        metadata: 额外元数据
    """
    agent_pid: str
    content: str
    tokens: int = 0
    importance_score: float = 0.5
    page_type: str = "general"  # system, tools, user, task, memory, working
    status: PageStatus = PageStatus.IN_MEMORY
    
    # 内部字段
    page_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 脏页追踪
    _dirty: bool = False
    
    def touch(self):
        """访问页面（更新访问统计）"""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def mark_dirty(self):
        """标记为脏页"""
        self._dirty = True
        self.status = PageStatus.DIRTY
    
    def mark_clean(self):
        """标记为干净"""
        self._dirty = False
        if self.status == PageStatus.DIRTY:
            self.status = PageStatus.IN_MEMORY
    
    def is_dirty(self) -> bool:
        """是否脏页"""
        return self._dirty
    
    def get_lru_score(self, current_time: Optional[float] = None) -> float:
        """
        获取 LRU 分数（越高表示越不常用）
        
        使用指数衰减模型：长时间未访问的页面分数更高（更可能被换出）
        """
        if current_time is None:
            current_time = time.time()
        
        time_delta = current_time - self.last_accessed
        # 指数衰减：10 分钟前的页面分数约为 1.0
        return 1 - 2 ** (-time_delta / 600)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'page_id': self.page_id,
            'agent_pid': self.agent_pid,
            'content': self.content,
            'tokens': self.tokens,
            'importance_score': self.importance_score,
            'page_type': self.page_type,
            'status': self.status.value,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed,
            'created_at': self.created_at,
            'embedding': self.embedding,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextPage':
        """从字典反序列化"""
        page = cls(
            agent_pid=data['agent_pid'],
            content=data['content'],
            tokens=data['tokens'],
            importance_score=data['importance_score'],
            page_type=data['page_type'],
            status=PageStatus(data['status']),
            page_id=data['page_id'],
            access_count=data['access_count'],
            last_accessed=data['last_accessed'],
            created_at=data['created_at'],
            embedding=data.get('embedding'),
            metadata=data.get('metadata', {}),
        )
        return page


class MemoryHierarchy:
    """
    内存层次结构 - 参考 DeepSeek Engram 论文
    
    模拟计算机存储层次，实现智能分层管理：
    
    L1 Cache (寄存器级)  ->  System Prompt (< 1K tokens, 始终在 context)
    L2 Cache (高速缓存)  ->  Working Memory (10-20K tokens, 当前任务)
    RAM (内存)           ->  Session Context (50-100K tokens, 本次会话)
    Disk (磁盘)          ->  Long-term Memory (数据库, 无限容量)
    
    关键洞察：越往上越快、越贵、越小；需要自动管理换入换出
    """
    
    # 层次容量限制（tokens）
    L1_SIZE = 1000          # System Prompt
    L2_SIZE = 20000         # Working Memory
    RAM_SIZE = 100000       # Session Context
    
    def __init__(self):
        self.l1_system: List[ContextPage] = []      # 系统提示（最热）
        self.l2_working: List[ContextPage] = []     # 工作记忆（热）
        self.ram_session: List[ContextPage] = []    # 会话上下文（温）
        self.access_patterns: Dict[str, int] = {}   # 访问模式统计
    
    def classify_page(self, page: ContextPage) -> str:
        """
        分类页面到对应的层次
        
        Returns:
            'l1', 'l2', 'ram', or 'disk'
        """
        if page.page_type == 'system':
            return 'l1'
        elif page.page_type in ('task', 'working'):
            return 'l2'
        elif page.page_type in ('user', 'recent'):
            return 'ram'
        else:
            return 'disk'
    
    def promote_page(self, page: ContextPage) -> bool:
        """
        尝试提升页面层次（换入更高速缓存）
        
        Returns:
            是否成功提升
        """
        current_level = self.classify_page(page)
        
        # L2 -> L1
        if current_level == 'l2' and page.importance_score > 0.9:
            if sum(p.tokens for p in self.l1_system) + page.tokens <= self.L1_SIZE:
                return True
        
        # RAM -> L2
        if current_level == 'ram' and page.access_count > 5:
            if sum(p.tokens for p in self.l2_working) + page.tokens <= self.L2_SIZE:
                return True
        
        return False
    
    def get_temperature(self, page: ContextPage) -> float:
        """
        获取页面的"温度"（访问热度）
        
        Returns:
            温度值 0-1，越高越热
        """
        # 基于访问频率和最近访问时间计算
        recency = 1 / (1 + time.time() - page.last_accessed)  # 最近访问越热
        frequency = min(page.access_count / 10, 1.0)          # 访问次数越多越热
        importance = page.importance_score                     # 重要性越高越热
        
        # 加权平均
        return recency * 0.3 + frequency * 0.3 + importance * 0.4


class KVCacheOptimizer:
    """
    KV-Cache 优化器
    
    核心洞察（来自 Manus 团队）：KV-Cache 命中率是最重要的性能指标。
    在 Claude 上，缓存命中的 token 成本是未命中的 1/10。
    
    优化策略：
    1. 静态内容前置：系统提示、工具定义放在最前面（最可能命中缓存）
    2. 动态内容排序：按变化频率排序，变化少的放前面
    3. 缓存命中率预估：预估命中率，指导上下文重组
    """
    
    def __init__(self):
        self.cache_segments: List[Dict[str, Any]] = []
        self.hit_rate_history: List[float] = []
        self.previous_tokens: Set[str] = set()  # 上一次请求的 token 集合
        self.static_signatures: Set[str] = set()  # 静态内容签名
    
    def register_static_content(self, content: str):
        """注册静态内容（这些部分在多次调用中保持不变，可以缓存）"""
        # 使用内容哈希作为签名
        import hashlib
        signature = hashlib.md5(content.encode()).hexdigest()
        self.static_signatures.add(signature)
    
    def optimize_layout(self, pages: List[ContextPage]) -> List[ContextPage]:
        """
        优化上下文布局以最大化缓存命中率
        
        策略：
        1. 将固定不变的部分（system、tools）放在最前面
        2. 将可能变化的部分（user、task）放在后面
        3. 在动态部分内部，按变化频率排序（变化少的放前面）
        
        Returns:
            优化后的页面列表
        """
        # 分类页面
        l1_pages = []    # System - 最热
        l2_pages = []    # Tools, Task - 热
        ram_pages = []   # User, Recent - 温
        
        for page in pages:
            if page.page_type == 'system':
                l1_pages.append(page)
            elif page.page_type in ('tools', 'task'):
                l2_pages.append(page)
            else:
                ram_pages.append(page)
        
        # L2 页面按访问频率排序（访问多的放前面，更可能命中缓存）
        l2_pages.sort(key=lambda p: (p.access_count, p.importance_score), reverse=True)
        
        # RAM 页面按"温度"排序
        ram_pages.sort(key=lambda p: p.access_count * p.importance_score, reverse=True)
        
        # 组装：L1 -> L2 -> RAM
        return l1_pages + l2_pages + ram_pages
    
    def estimate_cache_hit_rate(self, current_pages: List[ContextPage]) -> float:
        """
        预估缓存命中率
        
        计算当前上下文与上一次请求的 token 重叠度。
        
        Returns:
            预估的缓存命中率 0-1
        """
        if not self.previous_tokens:
            return 0.0
        
        # 提取当前页面的 token（简化处理：按空格分词）
        current_tokens: Set[str] = set()
        for page in current_pages:
            current_tokens.update(page.content.split())
        
        if not current_tokens:
            return 0.0
        
        # 计算重叠
        common_tokens = current_tokens & self.previous_tokens
        hit_rate = len(common_tokens) / len(current_tokens)
        
        self.hit_rate_history.append(hit_rate)
        
        # 保持历史记录在合理大小
        if len(self.hit_rate_history) > 100:
            self.hit_rate_history = self.hit_rate_history[-100:]
        
        return hit_rate
    
    def update_previous_tokens(self, pages: List[ContextPage]):
        """更新上一次请求的 token 集合"""
        self.previous_tokens = set()
        for page in pages:
            self.previous_tokens.update(page.content.split())
    
    def suggest_context_reorganization(self, pages: List[ContextPage]) -> List[Tuple[int, str]]:
        """
        建议上下文重组以优化缓存命中
        
        Returns:
            建议列表，每个建议包含 (优先级, 描述)
            优先级：1=高，2=中，3=低
        """
        suggestions = []
        
        # 检查静态内容是否在前
        non_static_in_front = False
        for i, page in enumerate(pages[:3]):  # 检查前3页
            if page.page_type not in ('system', 'tools'):
                non_static_in_front = True
                break
        
        if non_static_in_front:
            suggestions.append((1, "将静态内容（系统提示、工具定义）移到最前面，可提高 KV-Cache 命中率"))
        
        # 检查是否有低访问频率页面在高访问频率页面之前
        for i in range(len(pages) - 1):
            if pages[i].access_count < pages[i+1].access_count and \
               pages[i].page_type == pages[i+1].page_type:
                suggestions.append((2, f"交换位置 {i} 和 {i+1} 的页面，将高访问频率页面前置"))
                break  # 只报告第一个
        
        # 预估命中率检查
        hit_rate = self.estimate_cache_hit_rate(pages)
        if hit_rate < 0.5:
            suggestions.append((1, f"预估缓存命中率过低 ({hit_rate:.1%})，建议重组上下文"))
        elif hit_rate < 0.7:
            suggestions.append((2, f"预估缓存命中率有优化空间 ({hit_rate:.1%})"))
        
        return suggestions
    
    def get_hit_rate_stats(self) -> Dict[str, Any]:
        """获取命中率统计"""
        if not self.hit_rate_history:
            return {'average': 0, 'min': 0, 'max': 0, 'count': 0}
        
        return {
            'average': sum(self.hit_rate_history) / len(self.hit_rate_history),
            'min': min(self.hit_rate_history),
            'max': max(self.hit_rate_history),
            'count': len(self.hit_rate_history),
            'recent': self.hit_rate_history[-10:] if len(self.hit_rate_history) >= 10 else self.hit_rate_history,
        }


class SemanticImportanceCalculator:
    """
    语义重要性计算器
    
    使用向量相似度计算页面相对于当前任务的语义重要性。
    这是页面置换算法的重要组成部分：与当前任务语义相关的页面更不应该被换出。
    """
    
    def __init__(self, embedding_model: Optional[Any] = None):
        self.embedding_model = embedding_model
        self.cache: Dict[str, List[float]] = {}  # 嵌入缓存
    
    def calculate_importance(self, page: ContextPage, task_embedding: List[float]) -> float:
        """
        计算页面的语义重要性
        
        Args:
            page: 上下文页面
            task_embedding: 当前任务的嵌入向量
        
        Returns:
            重要性分数 0-1
        """
        if not self.embedding_model and not page.embedding:
            # 没有嵌入模型时，使用启发式方法
            return self._heuristic_importance(page)
        
        # 获取页面的嵌入
        if page.embedding:
            page_embedding = page.embedding
        else:
            page_embedding = self._get_embedding(page.content)
            page.embedding = page_embedding
        
        # 计算余弦相似度
        similarity = self._cosine_similarity(task_embedding, page_embedding)
        
        # 归一化到 0-1
        importance = (similarity + 1) / 2
        
        return importance
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的嵌入向量（带缓存）"""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.cache:
            return self.cache[text_hash]
        
        # 这里应该调用真实的嵌入模型
        # 简化处理：返回随机向量（实际应用中使用 OpenAI/text-embedding-3 等）
        import random
        embedding = [random.random() for _ in range(1536)]
        self.cache[text_hash] = embedding
        return embedding
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        import math
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _heuristic_importance(self, page: ContextPage) -> float:
        """启发式重要性计算（无嵌入模型时使用）"""
        # 系统提示最重要
        if page.page_type == 'system':
            return 1.0
        
        # 任务描述次之
        if page.page_type == 'task':
            return 0.9
        
        # 工具定义再次
        if page.page_type == 'tools':
            return 0.8
        
        # 基于访问频率调整
        base_score = 0.5
        if page.access_count > 10:
            base_score += 0.2
        elif page.access_count > 5:
            base_score += 0.1
        
        return min(base_score, 1.0)


class ContextManager:
    """
    上下文管理器 - 操作系统级的虚拟内存管理
    
    这是 Agent OS Kernel 最核心的组件之一。它将 LLM 有限的上下文窗口
    抽象为虚拟内存，通过自动的页面置换机制，让 Agent 可以"透明地"
    使用超过物理上下文限制的记忆。
    
    核心功能：
    1. 上下文页面管理（虚拟地址空间）
    2. 缺页中断处理（Page Fault）
    3. 页面置换算法（LRU + 重要性 + 语义相似度）
    4. 内存层次结构（L1/L2/RAM/Disk）
    5. KV-Cache 优化
    
    使用示例：
        # 初始化（设置上下文限制）
        cm = ContextManager(max_context_tokens=128000)
        
        # 分配页面（自动处理溢出）
        page_id = cm.allocate_page(agent_pid="agent-1", content="...", importance=0.8)
        
        # 访问页面（自动 swap in）
        page = cm.access_page(page_id)  # 如果不在内存，自动从数据库加载
        
        # 获取优化后的上下文
        context = cm.get_agent_context(agent_pid="agent-1", optimize_for_cache=True)
    
    Attributes:
        max_context_tokens: 最大上下文 token 数（模拟物理内存大小）
        current_usage: 当前使用的 token 数
        pages_in_memory: 当前在内存中的页面（pid -> page）
        swapped_pages: 已换出到磁盘的页面（pid -> page）
        storage_backend: 存储后端（用于 swap out/in）
    """
    
    def __init__(self, 
                 max_context_tokens: int = 128000,
                 enable_semantic_importance: bool = False,
                 storage_backend: Optional[Any] = None):
        """
        初始化上下文管理器
        
        Args:
            max_context_tokens: 最大上下文 token 数（默认 128K）
            enable_semantic_importance: 是否启用语义重要性计算
            storage_backend: 存储后端（用于页面换入换出）
        """
        self.max_context_tokens = max_context_tokens
        self.current_usage = 0
        
        # 页面存储
        self.pages_in_memory: Dict[str, ContextPage] = {}
        self.swapped_pages: Dict[str, ContextPage] = {}
        
        # 每个 Agent 的页面列表
        self.agent_pages: Dict[str, List[str]] = defaultdict(list)
        
        # 存储后端（用于 swap）
        self.storage = storage_backend
        
        # 优化器
        self.kv_cache_optimizer = KVCacheOptimizer()
        self.memory_hierarchy = MemoryHierarchy()
        self.importance_calculator = SemanticImportanceCalculator()
        self.enable_semantic_importance = enable_semantic_importance
        
        # 统计
        self.stats = {
            'page_faults': 0,          # 缺页次数
            'swaps_in': 0,             # 换入次数
            'swaps_out': 0,            # 换出次数
            'total_accesses': 0,       # 总访问次数
            'cache_hits': 0,           # 缓存命中
        }
        
        logger.info(f"ContextManager initialized with {max_context_tokens} tokens limit")
    
    def allocate_page(self, 
                     agent_pid: str, 
                     content: str, 
                     importance: float = 0.5,
                     page_type: str = "general",
                     embedding: Optional[List[float]] = None) -> str:
        """
        分配新的上下文页面
        
        如果当前使用超过限制，会自动触发页面置换（swap out）。
        
        Args:
            agent_pid: Agent 进程 ID
            content: 页面内容
            importance: 重要性评分 0-1（影响置换决策）
            page_type: 页面类型（system/tools/user/task/memory/working）
            embedding: 语义嵌入向量（可选）
        
        Returns:
            页面 ID
        
        Raises:
            MemoryError: 如果无法分配（所有页面都不可换出）
        """
        tokens = self._estimate_tokens(content)
        
        # 检查是否需要换出页面
        while self.current_usage + tokens > self.max_context_tokens:
            if not self._swap_out_page():
                raise MemoryError(
                    f"Cannot allocate page with {tokens} tokens. "
                    f"Current usage: {self.current_usage}/{self.max_context_tokens}. "
                    "All pages are critical and cannot be swapped out."
                )
        
        # 创建新页面
        page = ContextPage(
            agent_pid=agent_pid,
            content=content,
            tokens=tokens,
            importance_score=importance,
            page_type=page_type,
            status=PageStatus.IN_MEMORY,
            embedding=embedding
        )
        
        # 注册静态内容（用于 KV-Cache 优化）
        if page_type in ('system', 'tools'):
            self.kv_cache_optimizer.register_static_content(content)
        
        self.pages_in_memory[page.page_id] = page
        self.agent_pages[agent_pid].append(page.page_id)
        self.current_usage += tokens
        
        logger.debug(f"Allocated page {page.page_id[:8]} for agent {agent_pid[:8]} "
                    f"({tokens} tokens, type={page_type})")
        
        return page.page_id
    
    def access_page(self, 
                   page_id: str, 
                   agent_pid: Optional[str] = None,
                   auto_swap: bool = True) -> Optional[ContextPage]:
        """
        访问页面（可能触发缺页中断）
        
        如果页面不在内存中（已被 swap out），且 auto_swap=True，
        会自动从存储后端加载（swap in）。
        
        Args:
            page_id: 页面 ID
            agent_pid: Agent PID（用于权限检查）
            auto_swap: 是否自动换入
        
        Returns:
            页面对象，如果不存在则返回 None
        """
        self.stats['total_accesses'] += 1
        
        # 检查是否在内存中
        if page_id in self.pages_in_memory:
            page = self.pages_in_memory[page_id]
            
            # 权限检查
            if agent_pid and page.agent_pid != agent_pid:
                logger.warning(f"Access denied: page {page_id[:8]} belongs to different agent")
                return None
            
            page.touch()
            self.stats['cache_hits'] += 1
            return page
        
        # 页面在磁盘上，需要换入（缺页中断）
        if auto_swap and page_id in self.swapped_pages:
            self.stats['page_faults'] += 1
            logger.debug(f"Page fault for {page_id[:8]}, swapping in...")
            return self._swap_in_page(page_id)
        
        # 尝试从存储后端加载
        if auto_swap and self.storage:
            self.stats['page_faults'] += 1
            return self._load_from_storage(page_id)
        
        return None
    
    def get_agent_context(self, 
                         agent_pid: str, 
                         max_pages: Optional[int] = None,
                         optimize_for_cache: bool = True,
                         include_swapped: bool = False) -> str:
        """
        获取 Agent 的完整上下文
        
        Args:
            agent_pid: Agent 进程 ID
            max_pages: 最大返回页面数（None 表示不限制）
            optimize_for_cache: 是否优化布局以提高 KV-Cache 命中率
            include_swapped: 是否包含已换出的页面（会自动换入）
        
        Returns:
            合并后的上下文字符串
        """
        page_ids = self.agent_pages.get(agent_pid, [])
        pages = []
        
        for pid in page_ids:
            if include_swapped:
                page = self.access_page(pid, agent_pid, auto_swap=True)
            else:
                page = self.pages_in_memory.get(pid)
            
            if page:
                pages.append(page)
        
        if not pages:
            return ""
        
        # 优化布局以最大化 KV-Cache 命中率
        if optimize_for_cache:
            pages = self.kv_cache_optimizer.optimize_layout(pages)
            # 更新优化后的 token 集合（用于下次命中率预估）
            self.kv_cache_optimizer.update_previous_tokens(pages)
        
        # 限制页面数
        if max_pages:
            pages = pages[:max_pages]
        
        return "\n\n".join(p.content for p in pages)
    
    def update_page_content(self, page_id: str, new_content: str):
        """
        更新页面内容
        
        这会触发重新计算 token 数，并标记页面为 dirty。
        """
        page = self.pages_in_memory.get(page_id)
        if not page:
            logger.warning(f"Cannot update page {page_id[:8]}: not in memory")
            return
        
        # 更新 token 计数
        old_tokens = page.tokens
        page.content = new_content
        page.tokens = self._estimate_tokens(new_content)
        page.mark_dirty()
        page.touch()
        
        # 更新总使用量
        self.current_usage += (page.tokens - old_tokens)
        
        logger.debug(f"Updated page {page_id[:8]} content ({old_tokens} -> {page.tokens} tokens)")
    
    def update_page_importance(self, page_id: str, importance: float):
        """更新页面的重要性评分"""
        page = self.pages_in_memory.get(page_id) or self.swapped_pages.get(page_id)
        if page:
            page.importance_score = importance
            logger.debug(f"Updated importance for page {page_id[:8]}: {importance}")
    
    def release_agent_pages(self, agent_pid: str) -> int:
        """
        释放 Agent 的所有页面
        
        Returns:
            释放的页面数
        """
        page_ids = self.agent_pages.get(agent_pid, [])
        released = 0
        
        for page_id in page_ids:
            if page_id in self.pages_in_memory:
                page = self.pages_in_memory[page_id]
                self.current_usage -= page.tokens
                del self.pages_in_memory[page_id]
                released += 1
            elif page_id in self.swapped_pages:
                del self.swapped_pages[page_id]
                released += 1
        
        del self.agent_pages[agent_pid]
        
        logger.info(f"Released {released} pages for agent {agent_pid[:8]}")
        return released
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        hit_rate = 0
        if self.stats['total_accesses'] > 0:
            hit_rate = self.stats['cache_hits'] / self.stats['total_accesses']
        
        return {
            **self.stats,
            'current_usage': self.current_usage,
            'max_tokens': self.max_context_tokens,
            'usage_percent': (self.current_usage / self.max_context_tokens) * 100,
            'pages_in_memory': len(self.pages_in_memory),
            'pages_swapped': len(self.swapped_pages),
            'total_agents': len(self.agent_pages),
            'cache_hit_rate': hit_rate,
            'kv_cache_stats': self.kv_cache_optimizer.get_hit_rate_stats(),
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数
        
        简化实现：按空格分词后乘以经验系数 1.3
        实际生产环境应该使用 tiktoken 或类似工具
        """
        words = len(text.split())
        return int(words * 1.3)
    
    def _swap_out_page(self) -> bool:
        """
        换出一个页面（页面置换算法）
        
        策略：LRU + 重要性评分 + 语义相似度
        
        Returns:
            是否成功换出
        """
        if not self.pages_in_memory:
            return False
        
        # 计算每个页面的"受害者分数"（越高越应该被换出）
        candidates = []
        current_time = time.time()
        
        for page_id, page in self.pages_in_memory.items():
            # 跳过重要性极高的页面
            if page.importance_score >= 0.95:
                continue
            
            # 计算 LRU 分数
            lru_score = page.get_lru_score(current_time)
            
            # 综合考虑重要性：重要性越低，越容易被换出
            victim_score = lru_score * (1 - page.importance_score * 0.5)
            
            candidates.append((page_id, victim_score, page))
        
        if not candidates:
            logger.warning("No swappable pages found (all pages are critical)")
            return False
        
        # 选择得分最高的（最应该被换出的）
        victim_id, score, victim_page = max(candidates, key=lambda x: x[1])
        
        # 执行换出
        victim_page.status = PageStatus.SWAPPED
        del self.pages_in_memory[victim_id]
        self.swapped_pages[victim_id] = victim_page
        self.current_usage -= victim_page.tokens
        
        # 如果 dirty，写回存储
        if victim_page.is_dirty() and self.storage:
            self._write_to_storage(victim_page)
            victim_page.mark_clean()
        
        self.stats['swaps_out'] += 1
        
        logger.debug(f"Swapped out page {victim_id[:8]} "
                    f"({victim_page.tokens} tokens, score={score:.3f})")
        
        return True
    
    def _swap_in_page(self, page_id: str) -> Optional[ContextPage]:
        """
        换入一个页面（处理缺页中断）
        
        Args:
            page_id: 页面 ID
        
        Returns:
            页面对象
        """
        if page_id not in self.swapped_pages:
            return None
        
        page = self.swapped_pages[page_id]
        
        # 确保有足够空间
        while self.current_usage + page.tokens > self.max_context_tokens:
            if not self._swap_out_page():
                logger.error(f"Cannot swap in page {page_id[:8]}: no space available")
                return None
        
        # 执行换入
        page.status = PageStatus.IN_MEMORY
        page.touch()
        self.pages_in_memory[page_id] = page
        del self.swapped_pages[page_id]
        self.current_usage += page.tokens
        
        self.stats['swaps_in'] += 1
        
        logger.debug(f"Swapped in page {page_id[:8]} ({page.tokens} tokens)")
        
        return page
    
    def _write_to_storage(self, page: ContextPage):
        """将页面写回存储后端"""
        if self.storage and hasattr(self.storage, 'save_context_page'):
            self.storage.save_context_page(page)
            logger.debug(f"Wrote page {page.page_id[:8]} to storage")
    
    def _load_from_storage(self, page_id: str) -> Optional[ContextPage]:
        """从存储后端加载页面"""
        if not self.storage or not hasattr(self.storage, 'load_context_page'):
            return None
        
        page = self.storage.load_context_page(page_id)
        if page:
            # 确保有足够空间
            while self.current_usage + page.tokens > self.max_context_tokens:
                if not self._swap_out_page():
                    return None
            
            self.pages_in_memory[page_id] = page
            self.current_usage += page.tokens
            self.stats['swaps_in'] += 1
            logger.debug(f"Loaded page {page_id[:8]} from storage")
        
        return page
