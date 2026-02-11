# -*- coding: utf-8 -*-
"""
Performance Optimization Tools - Agent-OS-Kernel 性能优化工具

提供连接池优化、缓存优化、并发优化和内存优化功能。
"""

import time
import threading
import queue
import hashlib
import json
from typing import (
    Dict, Any, Optional, Callable, TypeVar, Generic,
    List, Tuple
)
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager
import weakref


T = TypeVar('T')


@dataclass
class PoolConfig:
    """连接池配置"""
    min_size: int = 2
    max_size: int = 10
    max_idle_seconds: float = 300.0
    checkout_timeout: float = 30.0
    health_check_interval: float = 60.0


@dataclass
class CacheConfig:
    """缓存配置"""
    max_size: int = 1000
    ttl_seconds: float = 3600.0
    cleanup_interval: float = 300.0
    eviction_policy: str = "lru"  # lru, fifo, lfu


@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_workers: int = 4
    queue_size: int = 100
    task_timeout: float = 60.0


class ConnectionPool(Generic[T]):
    """
    连接池管理器
    
    管理和复用数据库/网络连接，提高性能。
    """
    
    def __init__(
        self,
        factory: Callable[[], T],
        config: Optional[PoolConfig] = None
    ):
        self.factory = factory
        self.config = config or PoolConfig()
        self._pool: queue.Queue[T] = queue.Queue(maxsize=self.config.max_size)
        self._active: List[T] = []
        self._lock = threading.Lock()
        self._closed = False
        self._health_check_thread: Optional[threading.Thread] = None
        
        # 初始化最小连接数
        for _ in range(self.config.min_size):
            self._pool.put(self.factory())
    
    def get(self) -> T:
        """从池中获取连接"""
        if self._closed:
            raise RuntimeError("连接池已关闭")
        
        try:
            # 尝试从池中获取连接，超时检查
            return self._pool.get(
                block=True,
                timeout=self.config.checkout_timeout
            )
        except queue.Empty:
            # 池满了，创建新连接
            if len(self._active) < self.config.max_size:
                return self.factory()
            raise RuntimeError(
                f"获取连接超时，已达到最大连接数 {self.config.max_size}"
            )
    
    def release(self, connection: T):
        """将连接释放回池中"""
        if self._closed:
            return
        
        with self._lock:
            if connection in self._active:
                self._active.remove(connection)
            
            try:
                self._pool.put(connection, block=False)
            except queue.Full:
                pass  # 池满了，丢弃连接
    
    def acquire(self) -> T:
        """显式获取连接（手动管理）"""
        conn = self.get()
        with self._lock:
            self._active.append(conn)
        return conn
    
    def close(self):
        """关闭连接池"""
        self._closed = True
        
        # 清空池中的连接
        while True:
            try:
                conn = self._pool.get_nowait()
                self._close_connection(conn)
            except queue.Empty:
                break
        
        # 关闭活跃连接
        with self._lock:
            for conn in list(self._active):
                self._close_connection(conn)
            self._active.clear()
    
    def _close_connection(self, conn: T):
        """关闭单个连接"""
        if hasattr(conn, 'close'):
            try:
                conn.close()
            except Exception:
                pass
    
    def status(self) -> Dict[str, int]:
        """获取池状态"""
        return {
            "pool_size": self._pool.qsize(),
            "active_count": len(self._active),
            "total_capacity": self.config.max_size,
        }


class LRUCache(Generic[T]):
    """
    LRU (Least Recently Used) 缓存
    
    最近最少使用缓存策略，自动淘汰旧数据。
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: Dict[str, Tuple[float, T]] = {}  # {key: (timestamp, value)}
        self._order: List[str] = []  # 维护访问顺序
        self._lock = threading.Lock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """启动缓存清理任务"""
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop)
        self._cleanup_thread.daemon = True
        self._cleanup_thread.start()
    
    def stop(self):
        """停止缓存清理任务"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1.0)
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None
            
            timestamp, value = self._cache[key]
            
            # 检查TTL
            if time.time() - timestamp > self.config.ttl_seconds:
                del self._cache[key]
                self._order.remove(key)
                return None
            
            # LRU: 移动到末尾
            if self.config.eviction_policy == "lru":
                self._order.remove(key)
                self._order.append(key)
                self._cache[key] = (time.time(), value)
            
            return value
    
    def set(self, key: str, value: T):
        """设置缓存值"""
        with self._lock:
            current_time = time.time()
            
            if key in self._cache:
                # 更新现有值
                self._cache[key] = (current_time, value)
                if self.config.eviction_policy == "lru":
                    self._order.remove(key)
                    self._order.append(key)
            else:
                # 新增值
                self._cache[key] = (current_time, value)
                self._order.append(key)
            
            # 检查是否需要淘汰
            self._evict_if_needed()
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._order:
                    self._order.remove(key)
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._order.clear()
    
    def _evict_if_needed(self):
        """淘汰过期或多余的缓存项"""
        current_time = time.time()
        keys_to_remove = []
        
        for key in self._order:
            timestamp, _ = self._cache.get(key, (0, None))
            
            # 检查TTL
            if current_time - timestamp > self.config.ttl_seconds:
                keys_to_remove.append(key)
            elif len(self._cache) > self.config.max_size:
                # 超出容量，淘汰最老的
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self._cache:
                del self._cache[key]
            if key in self._order:
                self._order.remove(key)
    
    def _cleanup_loop(self):
        """定期清理过期缓存"""
        while self._running:
            time.sleep(self.config.cleanup_interval)
            
            with self._lock:
                self._evict_if_needed()
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.config.max_size,
                "ttl_seconds": self.config.ttl_seconds,
            }


class ThreadPoolOptimizer:
    """
    线程池优化器
    
    优化并发任务执行，支持任务队列和超时控制。
    """
    
    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        self.config = config or ConcurrencyConfig()
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        self._task_queue: queue.Queue = queue.Queue(maxsize=self.config.queue_size)
        self._results: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._running = True
        self._worker_thread: Optional[threading.Thread] = None
        
        self._start_worker()
    
    def _start_worker(self):
        """启动工作线程"""
        self._worker_thread = threading.Thread(target=self._process_queue)
        self._worker_thread.daemon = True
        self._worker_thread.start()
    
    def _process_queue(self):
        """处理任务队列"""
        while self._running:
            try:
                task_id, func, args, kwargs = self._task_queue.get(
                    block=True,
                    timeout=1.0
                )
                
                future = self._executor.submit(func, *args, **kwargs)
                
                # 添加超时处理
                try:
                    result = future.result(timeout=self.config.task_timeout)
                    with self._lock:
                        self._results[task_id] = {"status": "success", "result": result}
                except Exception as e:
                    with self._lock:
                        self._results[task_id] = {"status": "error", "error": str(e)}
                
                self._task_queue.task_done()
                
            except queue.Empty:
                continue
    
    def submit(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ) -> bool:
        """
        提交任务
        
        Args:
            task_id: 任务ID
            func: 可执行函数
            *args, **kwargs: 函数参数
        
        Returns:
            bool: 是否成功提交
        """
        try:
            self._task_queue.put_nowait((task_id, func, args, kwargs))
            return True
        except queue.Full:
            return False
    
    def submit_and_wait(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """提交任务并等待结果"""
        task_id = f"sync_{int(time.time() * 1000)}"
        
        future = self._executor.submit(func, *args, **kwargs)
        return future.result(timeout=self.config.task_timeout)
    
    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        start_time = time.time()
        
        while True:
            with self._lock:
                if task_id in self._results:
                    return self._results.pop(task_id)
            
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            time.sleep(0.01)
    
    def wait_for_all(self, timeout: Optional[float] = None) -> bool:
        """等待所有任务完成"""
        try:
            self._task_queue.join()
            return True
        except Exception:
            return False
    
    def shutdown(self, timeout: float = 5.0):
        """关闭线程池"""
        self._running = False
        
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
        
        self._executor.shutdown(wait=True)
    
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "queue_size": self._task_queue.qsize(),
            "max_workers": self.config.max_workers,
            "queue_capacity": self.config.queue_size,
        }


class MemoryOptimizer:
    """
    内存优化工具
    
    提供对象池化、内存泄漏检测和自动清理功能。
    """
    
    def __init__(self, max_pool_size: int = 100):
        self.max_pool_size = max_pool_size
        self._object_pool: Dict[str, List[Any]] = {}
        self._pool_lock = threading.Lock()
        self._usage_stats: Dict[str, int] = {}
        self._usage_lock = threading.Lock()
    
    def get_or_create(
        self,
        key: str,
        factory: Callable[[], T]
    ) -> T:
        """从池中获取或创建新对象"""
        with self._pool_lock:
            if key not in self._object_pool:
                self._object_pool[key] = []
            
            pool = self._object_pool[key]
            
            if pool:
                obj = pool.pop()
                self._track_usage(key, "reuse")
                return obj
            
            self._track_usage(key, "create")
            return factory()
    
    def release(self, key: str, obj: Any):
        """将对象释放回池中"""
        with self._pool_lock:
            if key not in self._object_pool:
                self._object_pool[key] = []
            
            if len(self._object_pool[key]) < self.max_pool_size:
                self._object_pool[key].append(obj)
    
    def _track_usage(self, key: str, action: str):
        """跟踪对象使用情况"""
        with self._usage_lock:
            if key not in self._usage_stats:
                self._usage_stats[key] = 0
            self._usage_stats[key] += 1
    
    def clear_pool(self, key: str):
        """清空指定类型的对象池"""
        with self._pool_lock:
            if key in self._object_pool:
                self._object_pool[key].clear()
    
    def clear_all_pools(self):
        """清空所有对象池"""
        with self._pool_lock:
            for key in list(self._object_pool.keys()):
                self._object_pool[key].clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取优化统计"""
        with self._pool_lock:
            pool_sizes = {
                key: len(pool) 
                for key, pool in self._object_pool.items()
            }
        
        with self._usage_lock:
            usage = self._usage_stats.copy()
        
        return {
            "pool_sizes": pool_sizes,
            "usage_counts": usage,
            "total_pooled": sum(pool_sizes.values()),
        }


class ConcurrencyLimiter:
    """
    并发限制器
    
    限制同时执行的任务数量，保护系统资源。
    """
    
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active_count = 0
        self._lock = threading.Lock()
    
    @contextmanager
    def limit(self):
        """上下文管理器，限制并发"""
        acquired = self._semaphore.acquire(timeout=30.0)
        
        if not acquired:
            raise RuntimeError(
                f"无法获取并发锁，当前活跃数: {self._active_count}, "
                f"最大并发: {self.max_concurrent}"
            )
        
        with self._lock:
            self._active_count += 1
        
        try:
            yield
        finally:
            with self._lock:
                self._active_count -= 1
            self._semaphore.release()
    
    def stats(self) -> Dict[str, int]:
        """获取状态"""
        with self._lock:
            return {
                "active": self._active_count,
                "max_concurrent": self.max_concurrent,
                "available": self.max_concurrent - self._active_count,
            }


class BatchProcessor:
    """
    批处理器
    
    将多个小任务合并为大批次处理，提高吞吐量。
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        flush_interval: float = 1.0,
        processor: Optional[Callable[[List[Any]], Any]] = None
    ):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._processor = processor
        
        self._queue: List[Any] = []
        self._lock = threading.Lock()
        self._flush_event = threading.Event()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
    
    def start(self):
        """启动批处理器"""
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_loop)
        self._worker_thread.daemon = True
        self._worker_thread.start()
    
    def stop(self, timeout: float = 5.0):
        """停止批处理器"""
        self._running = False
        self._flush_event.set()
        
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
        
        # 处理剩余任务
        self._flush()
    
    def add(self, item: Any) -> bool:
        """添加项目到批次"""
        with self._lock:
            if len(self._queue) >= self.batch_size:
                return False
            
            self._queue.append(item)
            
            if len(self._queue) >= self.batch_size:
                self._flush_event.set()
            
            return True
    
    def _process_loop(self):
        """处理循环"""
        while self._running:
            self._flush_event.wait(timeout=self.flush_interval)
            
            if not self._running:
                break
            
            self._flush()
            self._flush_event.clear()
    
    def _flush(self):
        """刷新批次"""
        with self._lock:
            if not self._queue:
                return
            
            batch = self._queue.copy()
            self._queue.clear()
        
        if self._processor:
            try:
                self._processor(batch)
            except Exception:
                pass  # 处理失败，丢弃批次
    
    def stats(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "queue_size": len(self._queue),
                "batch_size": self.batch_size,
                "flush_interval": self.flush_interval,
            }


# 便捷函数和工厂方法
def create_connection_pool(
    factory: Callable[[], T],
    min_size: int = 2,
    max_size: int = 10
) -> ConnectionPool[T]:
    """创建连接池"""
    config = PoolConfig(min_size=min_size, max_size=max_size)
    return ConnectionPool(factory, config)


def create_lru_cache(
    max_size: int = 1000,
    ttl_seconds: float = 3600
) -> LRUCache:
    """创建LRU缓存"""
    config = CacheConfig(max_size=max_size, ttl_seconds=ttl_seconds)
    cache = LRUCache(config)
    cache.start()
    return cache


def create_thread_pool(
    max_workers: int = 4,
    queue_size: int = 100
) -> ThreadPoolOptimizer:
    """创建线程池"""
    config = ConcurrencyConfig(
        max_workers=max_workers,
        queue_size=queue_size
    )
    return ThreadPoolOptimizer(config)


def create_memory_pool(max_pool_size: int = 100) -> MemoryOptimizer:
    """创建内存对象池"""
    return MemoryOptimizer(max_pool_size=max_pool_size)


def create_concurrency_limiter(max_concurrent: int) -> ConcurrencyLimiter:
    """创建并发限制器"""
    return ConcurrencyLimiter(max_concurrent)


def create_batch_processor(
    batch_size: int = 100,
    flush_interval: float = 1.0
) -> BatchProcessor:
    """创建批处理器"""
    return BatchProcessor(batch_size=batch_size, flush_interval=flush_interval)
