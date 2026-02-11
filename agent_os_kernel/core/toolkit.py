"""
工具模块集合 - Agent-OS-Kernel 核心工具包

提供常用的工具类和函数。
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from datetime import timezone, timezone
import json
import hashlib
import uuid
import re


class Timer:
    """高精度计时器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self) -> 'Timer':
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None
        return self
    
    def stop(self) -> float:
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        self.end_time = datetime.now(timezone.utc)
        return self.elapsed
    
    @property
    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()
    
    def reset(self) -> 'Timer':
        self.start_time = None
        self.end_time = None
        return self


class Singleton(type):
    """单例元类"""
    
    _instances: Dict[type, Any] = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    uid = uuid.uuid4().hex[:8]
    return f"{prefix}{uid}" if prefix else uid


def hash_data(data: Any, algorithm: str = "md5") -> str:
    """对数据进行哈希处理"""
    if isinstance(data, str):
        data = data.encode()
    elif isinstance(data, dict):
        data = json.dumps(data, sort_keys=True).encode()
    
    if algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    return hashlib.md5(data).hexdigest()


def deep_merge(base: Dict, overlay: Dict) -> Dict:
    """深度合并字典"""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        import time
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator


__all__ = ["Timer", "Singleton", "generate_id", "hash_data", "deep_merge", "retry"]
