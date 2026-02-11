"""
缓存工具模块 - 提供常用缓存策略
"""

from typing import Any, Optional, Dict, Callable
from datetime import datetime
from datetime import timezone, timezone
import time


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: Optional[int] = None):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Any] = {}
        self._order: list = []
    
    def get(self, key: str) -> Any:
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if self._is_expired(entry):
            self._remove(key)
            return None
        
        # Move to end (most recently used)
        self._order.remove(key)
        self._order.append(key)
        return entry["value"]
    
    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._order.remove(key)
        elif len(self._order) >= self.max_size:
            self._remove(self._order[0])
        
        self._cache[key] = {
            "value": value,
            "timestamp": datetime.now(timezone.utc)
        }
        self._order.append(key)
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            self._remove(key)
            return True
        return False
    
    def clear(self) -> None:
        self._cache.clear()
        self._order.clear()
    
    def _remove(self, key: str) -> None:
        del self._cache[key]
        if key in self._order:
            self._order.remove(key)
    
    def _is_expired(self, entry: Dict) -> bool:
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds()
        return elapsed > self.ttl_seconds
    
    @property
    def size(self) -> int:
        return len(self._cache)


class TTLCache:
    """简单TTL缓存"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
    
    def get(self, key: str) -> Any:
        if key not in self._cache:
            return None
        if self._is_expired(key):
            self.delete(key)
            return None
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
            return True
        return False
    
    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()
    
    def _is_expired(self, key: str) -> bool:
        return (time.time() - self._timestamps[key]) > self.ttl_seconds


def cached(ttl_seconds: int = 300, max_size: int = 100):
    """缓存装饰器"""
    cache = TTLCache(ttl_seconds)
    
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        return wrapper
    return decorator


__all__ = ["LRUCache", "TTLCache", "cached"]
