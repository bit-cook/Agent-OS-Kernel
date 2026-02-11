"""
Logging System - 日志系统

结构化日志、级别控制、输出格式
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
from datetime import timezone, timezone
from enum import Enum
import json
import sys


class LogLevel(Enum):
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogRecord:
    """日志记录"""
    timestamp: str
    level: str
    message: str
    module: str = ""
    function: str = ""
    line: int = 0
    extra: Dict = field(default_factory=dict)


class StructuredLogger:
    """结构化日志器"""
    
    def __init__(self, name: str = "Agent-OS", level: str = "INFO"):
        self.name = name
        self.level = LogLevel[level.upper()]
        self._handlers: List[callable] = []
    
    def log(self, level: LogLevel, message: str, **extra):
        """记录日志"""
        if level.value < self.level.value:
            return
        
        record = LogRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.name,
            message=message,
            extra=extra
        )
        
        for handler in self._handlers:
            handler(record)
    
    def debug(self, message: str, **extra):
        self.log(LogLevel.DEBUG, message, **extra)
    
    def info(self, message: str, **extra):
        self.log(LogLevel.INFO, message, **extra)
    
    def warning(self, message: str, **extra):
        self.log(LogLevel.WARNING, message, **extra)
    
    def error(self, message: str, **extra):
        self.log(LogLevel.ERROR, message, **extra)
    
    def critical(self, message: str, **extra):
        self.log(LogLevel.CRITICAL, message, **extra)
    
    def add_handler(self, handler: callable):
        """添加处理器"""
        self._handlers.append(handler)
    
    def set_level(self, level: str):
        """设置级别"""
        self.level = LogLevel[level.upper()]


def default_handler(record: LogRecord):
    """默认处理器"""
    output = {
        "timestamp": record.timestamp,
        "level": record.level,
        "message": record.message,
        "module": record.module
    }
    
    if record.extra:
        output["extra"] = record.extra
    
    print(json.dumps(output))


# 创建默认日志器
logger = StructuredLogger("Agent-OS", "INFO")
logger.add_handler(default_handler)
