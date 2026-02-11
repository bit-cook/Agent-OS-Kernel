"""
Enhanced Config Manager - 配置管理增强版

支持配置热重载、环境变量、配置文件模板
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from datetime import timezone, timezone
from pathlib import Path
import yaml
import os
import asyncio


@dataclass
class ConfigSection:
    """配置节"""
    name: str
    data: Dict[str, Any]
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EnhancedConfigManager:
    """增强配置管理器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self._config: Dict[str, ConfigSection] = {}
        self._observers: List[callable] = []
        
        if config_path and Path(config_path).exists():
            self.load(config_path)
        
        self._load_env_vars()
    
    def load(self, config_path: str):
        """加载配置文件"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        for section_name, section_data in data.items():
            self._config[section_name] = ConfigSection(
                name=section_name,
                data=section_data or {}
            )
    
    def _load_env_vars(self):
        """加载环境变量"""
        env_prefix = "AGENT_OS_"
        
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lower()
                self.set("env", config_key, value)
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置"""
        if section in self._config:
            return self._config[section].data.get(key, default)
        return default
    
    def set(self, section: str, key: str, value: Any):
        """设置配置"""
        if section not in self._config:
            self._config[section] = ConfigSection(name=section, data={})
        
        self._config[section].data[key] = value
        self._config[section].updated_at = datetime.now(timezone.utc)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "sections": len(self._config),
            "observers": len(self._observers)
        }
