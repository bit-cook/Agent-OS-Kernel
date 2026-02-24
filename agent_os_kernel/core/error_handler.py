"""
错误处理器模块 - Agent OS Kernel

提供完整的错误处理功能:
- 错误捕获
- 错误分类
- 错误恢复
- 错误报告
"""

import traceback
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
from datetime import datetime
from dataclasses import dataclass, field
from functools import wraps
import json
import threading


# 配置日志
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类"""
    VALIDATION_ERROR = "validation_error"
    RUNTIME_ERROR = "runtime_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    CONFIGURATION_ERROR = "configuration_error"
    RESOURCE_ERROR = "resource_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """错误信息数据类"""
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    traceback_str: Optional[str] = None
    error_code: Optional[str] = None
    is_recovered: bool = False
    recovery_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "traceback_str": self.traceback_str,
            "error_code": self.error_code,
            "is_recovered": self.is_recovered,
            "recovery_attempts": self.recovery_attempts
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class ErrorHandler:
    """错误处理器主类"""
    
    def __init__(self, max_recovery_attempts: int = 3):
        self.max_recovery_attempts = max_recovery_attempts
        self.error_history: List[ErrorInfo] = []
        self.error_callbacks: Dict[ErrorCategory, List[Callable]] = {}
        self._lock = threading.Lock()
        
        # 错误分类映射
        self._error_category_map: Dict[Type[Exception], ErrorCategory] = {
            ValueError: ErrorCategory.VALIDATION_ERROR,
            TypeError: ErrorCategory.VALIDATION_ERROR,
            KeyError: ErrorCategory.VALIDATION_ERROR,
            RuntimeError: ErrorCategory.RUNTIME_ERROR,
            ConnectionError: ErrorCategory.NETWORK_ERROR,
            TimeoutError: ErrorCategory.TIMEOUT_ERROR,
            PermissionError: ErrorCategory.AUTHORIZATION_ERROR,
            FileNotFoundError: ErrorCategory.RESOURCE_ERROR,
            MemoryError: ErrorCategory.RESOURCE_ERROR,
            OSError: ErrorCategory.RESOURCE_ERROR,
        }
        
        # 严重级别映射
        self._severity_map: Dict[Type[Exception], ErrorSeverity] = {
            ValueError: ErrorSeverity.LOW,
            TypeError: ErrorSeverity.LOW,
            KeyError: ErrorSeverity.MEDIUM,
            RuntimeError: ErrorSeverity.MEDIUM,
            ConnectionError: ErrorSeverity.HIGH,
            TimeoutError: ErrorSeverity.MEDIUM,
            PermissionError: ErrorSeverity.HIGH,
            FileNotFoundError: ErrorSeverity.MEDIUM,
            MemoryError: ErrorSeverity.CRITICAL,
            OSError: ErrorSeverity.MEDIUM,
        }
    
    def capture_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ) -> ErrorInfo:
        """
        捕获异常并创建错误信息
        
        Args:
            exception: 捕获的异常
            context: 错误上下文信息
            error_code: 错误代码
            
        Returns:
            ErrorInfo: 错误信息对象
        """
        category = self._classify_error(exception)
        severity = self._determine_severity(exception)
        
        error_info = ErrorInfo(
            error_type=type(exception).__name__,
            message=str(exception),
            category=category,
            severity=severity,
            context=context or {},
            traceback_str=traceback.format_exc(),
            error_code=error_code
        )
        
        with self._lock:
            self.error_history.append(error_info)
        
        # 调用相关的错误回调
        self._trigger_callbacks(error_info)
        
        logger.error(f"Error captured: {error_info.error_type} - {error_info.message}")
        
        return error_info
    
    def capture_error(
        self,
        error_type: str,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        traceback_str: Optional[str] = None
    ) -> ErrorInfo:
        """
        捕获错误信息（非异常场景）
        
        Args:
            error_type: 错误类型
            message: 错误消息
            category: 错误分类
            severity: 严重级别
            context: 错误上下文
            error_code: 错误代码
            traceback_str: 堆栈跟踪
            
        Returns:
            ErrorInfo: 错误信息对象
        """
        error_info = ErrorInfo(
            error_type=error_type,
            message=message,
            category=category,
            severity=severity,
            context=context or {},
            traceback_str=traceback_str,
            error_code=error_code
        )
        
        with self._lock:
            self.error_history.append(error_info)
        
        self._trigger_callbacks(error_info)
        
        logger.error(f"Error captured: {error_type} - {message}")
        
        return error_info
    
    def _classify_error(self, exception: Exception) -> ErrorCategory:
        """分类错误"""
        for exc_type, category in self._error_category_map.items():
            if isinstance(exception, exc_type):
                return category
        return ErrorCategory.UNKNOWN_ERROR
    
    def _determine_severity(self, exception: Exception) -> ErrorSeverity:
        """确定错误严重级别"""
        for exc_type, severity in self._severity_map.items():
            if isinstance(exception, exc_type):
                return severity
        return ErrorSeverity.MEDIUM
    
    def classify_exception(self, exception: Exception) -> ErrorCategory:
        """
        对异常进行分类
        
        Args:
            exception: 待分类的异常
            
        Returns:
            ErrorCategory: 错误分类
        """
        return self._classify_error(exception)
    
    def classify_error_message(self, error_message: str) -> ErrorCategory:
        """
        根据错误消息进行分类
        
        Args:
            error_message: 错误消息
            
        Returns:
            ErrorCategory: 错误分类
        """
        message_lower = error_message.lower()
        
        if any(keyword in message_lower for keyword in ["validation", "invalid", "expected"]):
            return ErrorCategory.VALIDATION_ERROR
        elif any(keyword in message_lower for keyword in ["network", "connection", "socket"]):
            return ErrorCategory.NETWORK_ERROR
        elif any(keyword in message_lower for keyword in ["database", "sql", "query"]):
            return ErrorCategory.DATABASE_ERROR
        elif any(keyword in message_lower for keyword in ["auth", "login", "password", "token"]):
            return ErrorCategory.AUTHENTICATION_ERROR
        elif any(keyword in message_lower for keyword in ["permission", "access", "denied", "forbidden"]):
            return ErrorCategory.AUTHORIZATION_ERROR
        elif any(keyword in message_lower for keyword in ["config", "setting", "configuration"]):
            return ErrorCategory.CONFIGURATION_ERROR
        elif any(keyword in message_lower for keyword in ["resource", "memory", "disk", "file"]):
            return ErrorCategory.RESOURCE_ERROR
        elif any(keyword in message_lower for keyword in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT_ERROR
        
        return ErrorCategory.UNKNOWN_ERROR
    
    def register_callback(
        self,
        category: ErrorCategory,
        callback: Callable[[ErrorInfo], None]
    ) -> None:
        """
        注册错误回调函数
        
        Args:
            category: 错误分类
            callback: 回调函数
        """
        if category not in self.error_callbacks:
            self.error_callbacks[category] = []
        self.error_callbacks[category].append(callback)
    
    def _trigger_callbacks(self, error_info: ErrorInfo) -> None:
        """触发所有相关的错误回调"""
        callbacks = self.error_callbacks.get(error_info.category, [])
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def recover(
        self,
        error_info: ErrorInfo,
        recovery_strategy: Callable[[ErrorInfo], Any]
    ) -> tuple[bool, Any]:
        """
        尝试恢复错误
        
        Args:
            error_info: 错误信息
            recovery_strategy: 恢复策略函数
            
        Returns:
            tuple: (是否成功恢复, 恢复结果)
        """
        if error_info.recovery_attempts >= self.max_recovery_attempts:
            logger.warning(f"Max recovery attempts reached for error: {error_info.error_type}")
            return False, None
        
        error_info.recovery_attempts += 1
        
        try:
            result = recovery_strategy(error_info)
            error_info.is_recovered = True
            logger.info(f"Error recovered successfully: {error_info.error_type}")
            return True, result
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return False, None
    
    def auto_recover(
        self,
        error_info: ErrorInfo,
        fallback_value: Any = None
    ) -> Any:
        """
        自动恢复（使用默认策略）
        
        Args:
            error_info: 错误信息
            fallback_value: 降级值
            
        Returns:
            Any: 恢复结果或降级值
        """
        # 默认恢复策略
        recovery_strategies = {
            ErrorCategory.VALIDATION_ERROR: lambda e: None,
            ErrorCategory.NETWORK_ERROR: lambda e: self._network_recovery(e),
            ErrorCategory.DATABASE_ERROR: lambda e: self._database_recovery(e),
            ErrorCategory.TIMEOUT_ERROR: lambda e: self._timeout_recovery(e),
        }
        
        strategy = recovery_strategies.get(
            error_info.category,
            lambda e: fallback_value
        )
        
        success, result = self.recover(error_info, strategy)
        
        if success:
            return result
        return fallback_value
    
    def _network_recovery(self, error_info: ErrorInfo) -> Any:
        """网络错误恢复策略"""
        # 简单的重试逻辑
        import time
        time.sleep(1)  # 等待1秒后重试
        return "network_recovered"
    
    def _database_recovery(self, error_info: ErrorInfo) -> Any:
        """数据库错误恢复策略"""
        return "database_recovered"
    
    def _timeout_recovery(self, error_info: ErrorInfo) -> Any:
        """超时错误恢复策略"""
        return "timeout_extended"
    
    def generate_report(
        self,
        include_context: bool = True,
        severity_filter: Optional[ErrorSeverity] = None
    ) -> Dict[str, Any]:
        """
        生成错误报告
        
        Args:
            include_context: 是否包含上下文
            severity_filter: 严重级别过滤
            
        Returns:
            Dict: 错误报告
        """
        with self._lock:
            errors = self.error_history.copy()
        
        if severity_filter:
            errors = [e for e in errors if e.severity == severity_filter]
        
        error_summary = {
            "total_errors": len(errors),
            "by_category": {},
            "by_severity": {},
            "recovered_count": sum(1 for e in errors if e.is_recovered),
            "errors": []
        }
        
        for error in errors:
            # 按分类统计
            cat_key = error.category.value
            error_summary["by_category"][cat_key] = error_summary["by_category"].get(cat_key, 0) + 1
            
            # 按严重级别统计
            sev_key = error.severity.value
            error_summary["by_severity"][sev_key] = error_summary["by_severity"].get(sev_key, 0) + 1
            
            # 添加错误详情
            error_data = {
                "error_type": error.error_type,
                "message": error.message,
                "category": error.category.value,
                "severity": error.severity.value,
                "timestamp": error.timestamp.isoformat(),
                "error_code": error.error_code,
                "is_recovered": error.is_recovered,
                "recovery_attempts": error.recovery_attempts
            }
            
            if include_context:
                error_data["context"] = error.context
                error_data["traceback"] = error.traceback_str
            
            error_summary["errors"].append(error_data)
        
        return error_summary
    
    def get_error_history(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        limit: int = 100
    ) -> List[ErrorInfo]:
        """
        获取错误历史
        
        Args:
            category: 错误分类过滤
            severity: 严重级别过滤
            limit: 最大返回数量
            
        Returns:
            List[ErrorInfo]: 错误信息列表
        """
        with self._lock:
            errors = self.error_history.copy()
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        return errors[-limit:]
    
    def clear_history(self) -> None:
        """清空错误历史"""
        with self._lock:
            self.error_history.clear()
        logger.info("Error history cleared")
    
    def register_error_type(
        self,
        exception_type: Type[Exception],
        category: ErrorCategory,
        severity: ErrorSeverity
    ) -> None:
        """
        注册新的错误类型映射
        
        Args:
            exception_type: 异常类型
            category: 错误分类
            severity: 严重级别
        """
        self._error_category_map[exception_type] = category
        self._severity_map[exception_type] = severity


def handle_errors(
    error_handler: Optional[ErrorHandler] = None,
    context: Optional[Dict[str, Any]] = None,
    fallback: Any = None,
    reraise: bool = False
):
    """
    错误处理装饰器
    
    Args:
        error_handler: 错误处理器实例
        context: 错误上下文
        fallback: 失败时的返回值
        reraise: 是否重新抛出异常
        
    Returns:
        Decorator: 装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = error_handler or get_global_error_handler()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = handler.capture_exception(e, context)
                if reraise:
                    raise
                return fallback
        
        return wrapper
    return decorator


# 全局错误处理器实例
_global_error_handler: Optional[ErrorHandler] = None


def get_global_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_global_error_handler(handler: ErrorHandler) -> None:
    """设置全局错误处理器实例"""
    global _global_error_handler
    _global_error_handler = handler


# 便捷函数
def capture_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None
) -> ErrorInfo:
    """使用全局错误处理器捕获异常"""
    return get_global_error_handler().capture_exception(
        exception, context, error_code
    )


def capture_error(
    error_type: str,
    message: str,
    category: ErrorCategory,
    severity: ErrorSeverity,
    context: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None
) -> ErrorInfo:
    """使用全局错误处理器捕获错误"""
    return get_global_error_handler().capture_error(
        error_type, message, category, severity, context, error_code
    )


def generate_report(
    include_context: bool = True,
    severity_filter: Optional[ErrorSeverity] = None
) -> Dict[str, Any]:
    """使用全局错误处理器生成报告"""
    return get_global_error_handler().generate_report(
        include_context, severity_filter
    )
