"""
Mixins 模块 - Agent OS Kernel

提供可重用的 mixin 类，用于扩展其他类的功能:
- LoggingMixin - 日志功能
- SingletonMixin - 单例模式
- ThreadSafeMixin - 线程安全
- SerializationMixin - 序列化
- PropertiesMixin - 属性管理
"""

import logging
import threading
import json
from typing import Any, Dict, Optional, Type, TypeVar
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LoggingMixin:
    """日志混入类，为类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取 logger 实例"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        return self._logger
    
    def log_debug(self, message: str, **kwargs) -> None:
        """记录调试日志"""
        self.logger.debug(message, extra=kwargs)
    
    def log_info(self, message: str, **kwargs) -> None:
        """记录信息日志"""
        self.logger.info(message, extra=kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """记录警告日志"""
        self.logger.warning(message, extra=kwargs)
    
    def log_error(self, message: str, **kwargs) -> None:
        """记录错误日志"""
        self.logger.error(message, extra=kwargs)
    
    def log_exception(self, message: str, exc_info: Optional[Exception] = None) -> None:
        """记录异常日志"""
        self.logger.exception(message, exc_info=exc_info or True)


class SingletonMixin:
    """单例混入类，确保类只有一个实例"""
    
    _instance: Optional[T] = None
    _lock: threading.Lock = threading.Lock()
    
    def __new__(cls: Type[T]) -> T:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._singleton_init()
            return cls._instance
    
    def _singleton_init(self) -> None:
        """单例初始化方法，子类可重写"""
        pass
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（主要用于测试）"""
        with cls._lock:
            cls._instance = None


class ThreadSafeMixin:
    """线程安全混入类，为类提供线程安全保护"""
    
    @property
    def lock(self) -> threading.Lock:
        """获取锁实例"""
        if not hasattr(self, '_lock'):
            self._lock = threading.Lock()
        return self._lock
    
    def with_lock(self):
        """线程安全装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.lock:
                    return func(*args, **kwargs)
            return wrapper
        return decorator


class SerializationMixin:
    """序列化混入类，提供对象序列化功能"""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                result[key] = self._serialize_value(value)
        return result
    
    def _serialize_value(self, value: Any) -> Any:
        """序列化单个值"""
        if hasattr(value, 'to_dict'):
            return value.to_dict()
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, datetime):
            return value.isoformat()
        return value
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """从字典创建实例（子类需重写）"""
        raise NotImplementedError
    
    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """从JSON字符串创建实例"""
        return cls.from_dict(json.loads(json_str))


class PropertiesMixin:
    """属性管理混入类，提供属性的获取、设置、删除功能"""
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """获取属性值"""
        return getattr(self, key, default)
    
    def set_property(self, key: str, value: Any) -> None:
        """设置属性值"""
        setattr(self, key, value)
    
    def delete_property(self, key: str) -> None:
        """删除属性"""
        if hasattr(self, key):
            delattr(self, key)
    
    def has_property(self, key: str) -> bool:
        """检查属性是否存在"""
        return hasattr(self, key)
    
    def get_all_properties(self) -> Dict[str, Any]:
        """获取所有属性"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


class InitializationMixin:
    """初始化混入类，提供统一的初始化接口"""
    
    def initialize(self, **kwargs) -> None:
        """初始化方法"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.on_initialize(**kwargs)
    
    def on_initialize(self, **kwargs) -> None:
        """初始化回调，子类可重写"""
        pass
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return getattr(self, '_initialized', False)


class StatefulMixin:
    """状态管理混入类，提供状态切换功能"""
    
    def __init__(self):
        super().__init__()
        self._state: str = 'idle'
        self._state_history: list = []
    
    @property
    def state(self) -> str:
        """获取当前状态"""
        return self._state
    
    def set_state(self, new_state: str) -> None:
        """设置状态"""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self._state_history.append({
                'from': old_state,
                'to': new_state,
                'timestamp': datetime.utcnow()
            })
            self.on_state_change(old_state, new_state)
    
    def on_state_change(self, old_state: str, new_state: str) -> None:
        """状态变化回调，子类可重写"""
        pass
    
    def get_state_history(self) -> list:
        """获取状态历史"""
        return self._state_history.copy()
    
    def reset_state(self) -> None:
        """重置状态"""
        self.set_state('idle')


class CachedPropertyMixin:
    """缓存属性混入类，提供属性缓存功能"""
    
    def __init__(self):
        super().__init__()
        self._cache: Dict[str, Any] = {}
    
    def cached_property(self, func):
        """缓存属性装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(self, '_cache'):
                self._cache = {}
            key = func.__name__
            if key not in self._cache:
                self._cache[key] = func(*args, **kwargs)
            return self._cache[key]
        return wrapper
    
    def clear_cache(self, key: Optional[str] = None) -> None:
        """清除缓存"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
    
    def invalidate_cache(self, key: str) -> None:
        """使缓存失效"""
        self._cache.pop(key, None)


# 组合 Mixin - 常用功能组合
class BaseMixin(LoggingMixin, ThreadSafeMixin, SerializationMixin):
    """基础混入类，包含常用功能"""
    pass


class ComprehensiveMixin(LoggingMixin, SingletonMixin, ThreadSafeMixin, 
                         SerializationMixin, PropertiesMixin, InitializationMixin):
    """综合混入类，包含所有常用功能"""
    pass
