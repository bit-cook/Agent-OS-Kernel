# -*- coding: utf-8 -*-
"""
Exceptions - 异常定义

标准化的异常层次结构，便于错误处理和调试
"""

from typing import Callable, Dict, Optional, TypeVar, Any
from datetime import datetime, timezone, timedelta


T = TypeVar('T')


class AgentOSKernelError(Exception):
    """基础异常"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def __str__(self):
        return self.message


class AgentError(AgentOSKernelError):
    """Agent 相关错误"""
    pass


class AgentNotFoundError(AgentError):
    """Agent 不存在"""
    pass


class AgentCreationError(AgentError):
    """Agent 创建失败"""
    pass


class AgentExecutionError(AgentError):
    """Agent 执行失败"""
    pass


class AgentTimeoutError(AgentError):
    """Agent 超时"""
    pass


class ContextError(AgentOSKernelError):
    """上下文相关错误"""
    pass


class ContextOverflowError(ContextError):
    """上下文溢出"""
    pass


class ContextNotFoundError(ContextError):
    """上下文不存在"""
    pass


class PageFaultError(ContextError):
    """页错误"""
    pass


class StorageError(AgentOSKernelError):
    """存储相关错误"""
    pass


class StorageConnectionError(StorageError):
    """存储连接失败"""
    pass


class StorageOperationError(StorageError):
    """存储操作失败"""
    pass


class CheckpointError(StorageError):
    """检查点错误"""
    pass


class SchedulerError(AgentOSKernelError):
    """调度相关异常"""
    pass


class SchedulerFullError(SchedulerError):
    """调度器已满"""
    pass


class SchedulingError(SchedulerError):
    """调度失败"""
    pass


class TaskError(AgentOSKernelError):
    """Task 执行错误"""
    pass


class TaskTimeoutError(TaskError):
    """Task 超时错误"""
    pass


class SecurityError(AgentOSKernelError):
    """安全相关异常"""
    pass


class PermissionDeniedError(SecurityError):
    """权限拒绝"""
    pass


class SandboxViolationError(SecurityError):
    """沙箱违规"""
    pass


class ValidationError(AgentOSKernelError):
    """验证错误"""
    pass


class ConfigurationError(AgentOSKernelError):
    """配置错误"""
    pass


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self._handlers: Dict[type, Callable] = {}
        self._default_handler: Optional[Callable] = None
        self._error_counts: Dict[type, int] = {}
    
    def register(self, error_type: type, handler: Callable):
        """注册错误处理器"""
        self._handlers[error_type] = handler
    
    def set_default(self, handler: Callable):
        """设置默认处理器"""
        self._default_handler = handler
    
    def handle(self, error: Exception) -> bool:
        """处理错误"""
        error_type = type(error)
        
        # 检查注册的处理器
        if error_type in self._handlers:
            self._handlers[error_type](error)
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
            return True
        
        # 检查父类处理器
        for handler_type, handler in self._handlers.items():
            if isinstance(error, handler_type):
                handler(error)
                self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
                return True
        
        # 使用默认处理器
        if self._default_handler:
            self._default_handler(error)
            return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_errors": sum(self._error_counts.values()),
            "by_type": self._error_counts.copy(),
            "handlers_registered": len(self._handlers),
        }


class retry:
    """重试装饰器"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """装饰器调用"""
        
        def wrapper(*args, **kwargs) -> T:
            """包装函数"""
            attempt = 0
            current_delay = self.delay
            
            while attempt < self.max_attempts:
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    attempt += 1
                    
                    if attempt >= self.max_attempts:
                        raise
                    
                    # 记录重试
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Retry attempt {attempt}/{self.max_attempts} "
                        f"after {current_delay:.2f}s: {e}"
                    )
                    
                    # 等待后重试
                    import time
                    time.sleep(current_delay)
                    
                    # 指数退避
                    current_delay *= self.backoff
            
            raise RuntimeError("Should not reach here")
        
        return wrapper
