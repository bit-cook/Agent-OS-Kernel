"""
Utilities 工具模块 - Agent OS Kernel

提供通用的工具函数:
- 文件操作工具
- 字符串处理工具
- 时间工具
- 验证工具
"""

import hashlib
import json
import random
import string
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


def generate_id(length: int = 32) -> str:
    """生成随机ID"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


def generate_uuid() -> str:
    """生成UUID风格的ID"""
    timestamp = hex(int(time.time() * 1000))[2:]
    random_part = ''.join(random.choices(string.hexdigits.lower(), k=32))
    return f"{timestamp}-{random_part[:8]}-{random_part[8:12]}-{random_part[12:16]}-{random_part[16:]}"


def hash_content(content: str, algorithm: str = 'sha256') -> str:
    """计算内容的哈希值"""
    if algorithm == 'md5':
        return hashlib.md5(content.encode()).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(content.encode()).hexdigest()
    elif algorithm == 'sha512':
        return hashlib.sha512(content.encode()).hexdigest()
    else:
        return hashlib.sha256(content.encode()).hexdigest()


def file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """计算文件的哈希值"""
    hasher = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def ensure_dir(directory: str) -> Path:
    """确保目录存在"""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(file_path: str) -> Dict:
    """读取JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(file_path: str, data: Any, indent: int = 2) -> None:
    """写入JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def normalize_text(text: str) -> str:
    """标准化文本"""
    return ' '.join(text.split()).strip()


def format_timestamp(timestamp: Optional[float] = None, format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化时间戳"""
    if timestamp is None:
        timestamp = time.time()
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(format)


def parse_timestamp(timestamp_str: str, format: str = '%Y-%m-%d %H:%M:%S') -> float:
    """解析时间戳字符串"""
    dt = datetime.strptime(timestamp_str, format)
    return dt.timestamp()


def is_valid_email(email: str) -> bool:
    """验证邮箱格式"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """验证URL格式"""
    import re
    pattern = r'^https?://[^\s]+$'
    return bool(re.match(pattern, url))


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator


class Timer:
    """计时器类"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self
    
    def stop(self) -> float:
        self.end_time = time.perf_counter()
        return self.elapsed
    
    @property
    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else time.perf_counter()
        return end - self.start_time
    
    def __enter__(self) -> 'Timer':
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
