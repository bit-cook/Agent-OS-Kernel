"""
关闭管理器模块 - Agent OS Kernel

提供系统关闭和资源清理功能:
- 优雅关闭
- 资源清理
- 关闭钩子注册
- 信号处理
- 资源状态追踪
"""

import signal
import logging
import threading
import asyncio
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import atexit


# 配置日志
logger = logging.getLogger(__name__)


class ShutdownPhase(Enum):
    """关闭阶段"""
    PRE_SHUTDOWN = "pre_shutdown"
    RESOURCE_RELEASE = "resource_release"
    CLEANUP = "cleanup"
    FINALIZE = "finalize"
    COMPLETED = "completed"


class ShutdownStatus(Enum):
    """关闭状态"""
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ShutdownHook:
    """关闭钩子数据类"""
    name: str
    callback: Callable[..., Any]
    priority: int = 0
    timeout_seconds: float = 30.0
    phase: ShutdownPhase = ShutdownPhase.CLEANUP
    enabled: bool = True
    executed: bool = False
    error: Optional[str] = None


@dataclass
class ResourceInfo:
    """资源信息数据类"""
    resource_id: str
    resource_type: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    cleanup_callback: Optional[Callable[..., Any]] = None
    state: str = "active"


class ShutdownManager:
    """关闭管理器主类"""
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        graceful_timeout: float = 60.0,
        enable_signal_handlers: bool = True
    ):
        """
        初始化关闭管理器
        
        Args:
            default_timeout: 默认超时时间（秒）
            graceful_timeout: 优雅关闭超时时间（秒）
            enable_signal_handlers: 是否启用信号处理器
        """
        self.default_timeout = default_timeout
        self.graceful_timeout = graceful_timeout
        self.enable_signal_handlers = enable_signal_handlers
        
        self._hooks: Dict[str, ShutdownHook] = {}
        self._resources: Dict[str, ResourceInfo] = {}
        self._shutdown_status: ShutdownStatus = ShutdownStatus.IDLE
        self._current_phase: ShutdownPhase = ShutdownPhase.PRE_SHUTDOWN
        self._shutdown_start_time: Optional[datetime] = None
        self._lock = threading.Lock()
        self._shutdown_requested = threading.Event()
        
        self._callbacks: List[Callable[[ShutdownPhase, str], None]] = []
        
        if self.enable_signal_handlers:
            self._setup_signal_handlers()
        
        # 注册atexithandler作为备份
        atexit.register(self._atexit_handler)
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        self._original_handlers: Dict[int, Any] = {}
        
        signals = [
            signal.SIGTERM,
            signal.SIGINT,
            signal.SIGHUP,
        ]
        
        for sig in signals:
            try:
                self._original_handlers[sig] = signal.signal(sig, self._signal_handler)
            except (OSError, ValueError) as e:
                logger.warning(f"Cannot set signal handler for {sig}: {e}")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """信号处理器"""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name}, initiating graceful shutdown")
        self._shutdown_requested.set()
        
        try:
            self.shutdown(graceful=True)
        except Exception as e:
            logger.error(f"Error during signal-triggered shutdown: {e}")
    
    def _atexit_handler(self) -> None:
        """atexit处理器"""
        if self._shutdown_status == ShutdownStatus.IDLE:
            logger.info("Process exiting, running shutdown hooks")
            try:
                self.shutdown(graceful=True)
            except Exception as e:
                logger.error(f"Error during atexit shutdown: {e}")
    
    def register_hook(
        self,
        name: str,
        callback: Callable[..., Any],
        priority: int = 0,
        timeout_seconds: Optional[float] = None,
        phase: Optional[ShutdownPhase] = None
    ) -> str:
        """
        注册关闭钩子
        
        Args:
            name: 钩子名称
            callback: 回调函数
            priority: 优先级（数字越大优先级越高）
            timeout_seconds: 超时时间
            phase: 执行阶段
            
        Returns:
            str: 钩子ID
        """
        hook_id = f"hook_{len(self._hooks)}"
        
        hook = ShutdownHook(
            name=name,
            callback=callback,
            priority=priority,
            timeout_seconds=timeout_seconds or self.default_timeout,
            phase=phase or ShutdownPhase.CLEANUP
        )
        
        with self._lock:
            self._hooks[hook_id] = hook
        
        logger.debug(f"Registered shutdown hook: {name} (priority: {priority})")
        return hook_id
    
    def unregister_hook(self, hook_id: str) -> bool:
        """
        注销关闭钩子
        
        Args:
            hook_id: 钩子ID
            
        Returns:
            bool: 是否成功注销
        """
        with self._lock:
            if hook_id in self._hooks:
                del self._hooks[hook_id]
                logger.debug(f"Unregistered shutdown hook: {hook_id}")
                return True
        return False
    
    def register_resource(
        self,
        resource_id: str,
        resource_type: str,
        name: str,
        cleanup_callback: Optional[Callable[..., Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        注册需要清理的资源
        
        Args:
            resource_id: 资源ID
            resource_type: 资源类型
            name: 资源名称
            cleanup_callback: 清理回调函数
            metadata: 元数据
        """
        resource = ResourceInfo(
            resource_id=resource_id,
            resource_type=resource_type,
            name=name,
            cleanup_callback=cleanup_callback,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._resources[resource_id] = resource
        
        logger.debug(f"Registered resource: {resource_type}/{name}")
    
    def unregister_resource(self, resource_id: str) -> bool:
        """
        注销资源
        
        Args:
            resource_id: 资源ID
            
        Returns:
            bool: 是否成功注销
        """
        with self._lock:
            if resource_id in self._resources:
                del self._resources[resource_id]
                logger.debug(f"Unregistered resource: {resource_id}")
                return True
        return False
    
    def get_registered_resources(self) -> List[ResourceInfo]:
        """获取所有已注册资源"""
        with self._lock:
            return list(self._resources.values())
    
    def register_progress_callback(
        self,
        callback: Callable[[ShutdownPhase, str], None]
    ) -> None:
        """
        注册进度回调
        
        Args:
            callback: 进度回调函数
        """
        self._callbacks.append(callback)
    
    def _notify_progress(self, phase: ShutdownPhase, message: str) -> None:
        """通知进度"""
        for callback in self._callbacks:
            try:
                callback(phase, message)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _execute_hook(self, hook: ShutdownHook) -> bool:
        """
        执行单个钩子
        
        Args:
            hook: 关闭钩子
            
        Returns:
            bool: 是否成功执行
        """
        if not hook.enabled or hook.executed:
            return True
        
        try:
            logger.debug(f"Executing shutdown hook: {hook.name}")
            
            # 如果是可调用对象，执行它
            if callable(hook.callback):
                import inspect
                if inspect.iscoroutinefunction(hook.callback):
                    # 异步函数
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(
                            asyncio.wait_for(
                                hook.callback(),
                                timeout=hook.timeout_seconds
                            )
                        )
                    finally:
                        loop.close()
                else:
                    # 同步函数
                    hook.callback()
            
            hook.executed = True
            logger.debug(f"Shutdown hook completed: {hook.name}")
            return True
            
        except asyncio.TimeoutError:
            hook.error = f"Timeout after {hook.timeout_seconds}s"
            logger.warning(f"Shutdown hook timeout: {hook.name}")
            return False
        except Exception as e:
            hook.error = str(e)
            logger.error(f"Shutdown hook error: {hook.name} - {e}")
            return False
    
    def shutdown(
        self,
        graceful: bool = True,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        执行关闭流程
        
        Args:
            graceful: 是否优雅关闭
            timeout: 超时时间
            
        Returns:
            Dict: 关闭结果
        """
        if self._shutdown_status == ShutdownStatus.IN_PROGRESS:
            logger.warning("Shutdown already in progress")
            return {"status": "already_in_progress"}
        
        result = {
            "status": None,
            "phase": None,
            "duration_seconds": None,
            "hooks_executed": 0,
            "hooks_failed": 0,
            "resources_cleaned": 0,
            "errors": []
        }
        
        self._shutdown_status = ShutdownStatus.IN_PROGRESS
        self._shutdown_start_time = datetime.utcnow()
        timeout = timeout or (self.graceful_timeout if graceful else self.default_timeout)
        
        logger.info(f"Starting shutdown (graceful={graceful}, timeout={timeout}s)")
        
        try:
            # 阶段1: 预关闭
            self._current_phase = ShutdownPhase.PRE_SHUTDOWN
            self._notify_progress(ShutdownPhase.PRE_SHUTDOWN, "Pre-shutdown phase started")
            
            # 阶段2: 资源释放
            self._current_phase = ShutdownPhase.RESOURCE_RELEASE
            self._notify_progress(ShutdownPhase.RESOURCE_RELEASE, "Releasing resources")
            
            resources = self.get_registered_resources()
            for resource in resources:
                try:
                    if resource.cleanup_callback and callable(resource.cleanup_callback):
                        resource.cleanup_callback()
                    resource.state = "released"
                    result["resources_cleaned"] += 1
                except Exception as e:
                    result["errors"].append(f"Resource {resource.name}: {e}")
            
            # 阶段3: 执行清理钩子（按优先级排序）
            self._current_phase = ShutdownPhase.CLEANUP
            self._notify_progress(ShutdownPhase.CLEANUP, "Executing cleanup hooks")
            
            with self._lock:
                sorted_hooks = sorted(
                    self._hooks.values(),
                    key=lambda h: (-h.priority, h.phase.value)
                )
            
            for hook in sorted_hooks:
                success = self._execute_hook(hook)
                if success:
                    result["hooks_executed"] += 1
                else:
                    result["hooks_failed"] += 1
            
            # 阶段4: 最终化
            self._current_phase = ShutdownPhase.FINALIZE
            self._notify_progress(ShutdownPhase.FINALIZE, "Finalization phase")
            
            self._current_phase = ShutdownPhase.COMPLETED
            self._shutdown_status = ShutdownStatus.COMPLETED
            result["status"] = "completed"
            
        except Exception as e:
            self._shutdown_status = ShutdownStatus.FAILED
            result["status"] = "failed"
            result["errors"].append(str(e))
            logger.error(f"Shutdown failed: {e}")
        
        finally:
            duration = (datetime.utcnow() - self._shutdown_start_time).total_seconds()
            result["duration_seconds"] = duration
            result["phase"] = self._current_phase.value
            
            logger.info(
                f"Shutdown completed: status={result['status']}, "
                f"duration={duration:.2f}s, "
                f"hooks={result['hooks_executed']}/{result['hooks_executed']+result['hooks_failed']}"
            )
        
        return result
    
    def request_shutdown(self) -> None:
        """请求关闭（异步触发）"""
        self._shutdown_requested.set()
        logger.info("Shutdown requested")
    
    def is_shutdown_requested(self) -> bool:
        """检查是否请求了关闭"""
        return self._shutdown_requested.is_set()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取关闭管理器状态
        
        Returns:
            Dict: 状态信息
        """
        with self._lock:
            return {
                "status": self._shutdown_status.value,
                "current_phase": self._current_phase.value,
                "registered_hooks": len(self._hooks),
                "registered_resources": len(self._resources),
                "shutdown_requested": self.is_shutdown_requested(),
                "shutdown_start_time": (
                    self._shutdown_start_time.isoformat()
                    if self._shutdown_start_time else None
                )
            }
    
    def reset(self) -> None:
        """重置关闭管理器状态"""
        with self._lock:
            self._shutdown_status = ShutdownStatus.IDLE
            self._current_phase = ShutdownPhase.PRE_SHUTDOWN
            self._shutdown_start_time = None
            self._shutdown_requested.clear()
            
            for hook in self._hooks.values():
                hook.executed = False
                hook.error = None
            
            for resource in self._resources.values():
                resource.state = "active"
        
        logger.info("Shutdown manager reset")
    
    def cleanup(self) -> None:
        """清理资源并重置"""
        self.shutdown(graceful=False)
        self.reset()
        
        # 移除信号处理器
        if self.enable_signal_handlers:
            for sig, handler in self._original_handlers.items():
                try:
                    signal.signal(sig, handler)
                except (OSError, ValueError):
                    pass
        
        logger.info("Shutdown manager cleaned up")


@contextmanager
def shutdown_context(manager: ShutdownManager):
    """
    关闭管理器上下文
    
    Usage:
        manager = ShutdownManager()
        with shutdown_context(manager):
            # ... do work ...
        # 自动执行关闭
    """
    try:
        yield manager
    finally:
        manager.shutdown(graceful=True)


# 全局关闭管理器实例
_global_shutdown_manager: Optional[ShutdownManager] = None


def get_global_shutdown_manager() -> ShutdownManager:
    """获取全局关闭管理器实例"""
    global _global_shutdown_manager
    if _global_shutdown_manager is None:
        _global_shutdown_manager = ShutdownManager()
    return _global_shutdown_manager


def set_global_shutdown_manager(manager: ShutdownManager) -> None:
    """设置全局关闭管理器实例"""
    global _global_shutdown_manager
    _global_shutdown_manager = manager


# 便捷函数
def register_hook(
    name: str,
    callback: Callable[..., Any],
    priority: int = 0,
    timeout_seconds: Optional[float] = None
) -> str:
    """使用全局关闭管理器注册钩子"""
    return get_global_shutdown_manager().register_hook(
        name, callback, priority, timeout_seconds
    )


def register_resource(
    resource_id: str,
    resource_type: str,
    name: str,
    cleanup_callback: Optional[Callable[..., Any]] = None
) -> None:
    """使用全局关闭管理器注册资源"""
    get_global_shutdown_manager().register_resource(
        resource_id, resource_type, name, cleanup_callback
    )


def request_shutdown() -> None:
    """请求全局关闭"""
    get_global_shutdown_manager().request_shutdown()


def shutdown(graceful: bool = True) -> Dict[str, Any]:
    """执行全局关闭"""
    return get_global_shutdown_manager().shutdown(graceful)
