# -*- coding: utf-8 -*-
"""Config Manager - 配置管理器

支持多环境配置、动态更新、配置热加载。
"""

import asyncio
import logging
import yaml
import json
import hashlib
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ConfigSection:
    """配置区块"""
    name: str
    data: Dict[str, Any]
    version: int = 0
    updated_at: datetime = None
    hash: str = ""
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)


class ConfigManager:
    """配置管理器"""
    
    def __init__(
        self,
        config_dir: str = "config",
        enable_hot_reload: bool = True,
        hot_reload_interval: int = 30
    ):
        self.config_dir = Path(config_dir)
        self.enable_hot_reload = enable_hot_reload
        self.hot_reload_interval = hot_reload_interval
        
        self._configs: Dict[str, ConfigSection] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._reload_task: Optional[asyncio.Task] = None
        
        logger.info(f"ConfigManager initialized: dir={config_dir}")
    
    async def initialize(self):
        """初始化"""
        if not self._running:
            self._running = True
            await self._load_all()
            
            if self.enable_hot_reload:
                self._reload_task = asyncio.create_task(self._reload_loop())
            
            logger.info("ConfigManager started")
    
    async def shutdown(self):
        """关闭"""
        self._running = False
        if self._reload_task:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass
        
        logger.info("ConfigManager shutdown")
    
    async def load(self, name: str, file_path: str = None) -> bool:
        """加载配置"""
        path = Path(file_path) if file_path else self.config_dir / f"{name}.yaml"
        
        try:
            with open(path, 'r') as f:
                if path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f) or {}
                elif path.suffix == '.json':
                    data = json.load(f)
                else:
                    data = f.read()
            
            hash_str = hashlib.md5(str(data).encode()).hexdigest()
            
            config = ConfigSection(
                name=name,
                data=data,
                version=1,
                hash=hash_str
            )
            
            async with self._lock:
                old_hash = self._configs.get(name, ConfigSection(name=name, data={})).hash
                self._configs[name] = config
            
            if old_hash != hash_str:
                await self._notify_change(name, config)
            
            logger.info(f"Loaded config: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load config {name}: {e}")
            return False
    
    async def _load_all(self):
        """加载所有配置"""
        if not self.config_dir.exists():
            return
        
        for path in self.config_dir.glob("*.yaml"):
            await self.load(path.stem)
    
    async def get(self, name: str, key: str = None, default: Any = None) -> Any:
        """获取配置"""
        async with self._lock:
            config = self._configs.get(name)
        
        if not config:
            return default
        
        if key is None:
            return config.data
        
        return config.data.get(key, default)
    
    async def set(self, name: str, key: str, value: Any):
        """设置配置"""
        async with self._lock:
            if name not in self._configs:
                self._configs[name] = ConfigSection(name=name, data={})
            
            self._configs[name].data[key] = value
            self._configs[name].version += 1
            self._configs[name].updated_at = datetime.now(timezone.utc)
        
        await self._notify_change(name, self._configs[name])
    
    async def delete(self, name: str, key: str):
        """删除配置"""
        async with self._lock:
            if name in self._configs and key in self._configs[name].data:
                del self._configs[name].data[key]
                self._configs[name].version += 1
        
        await self._notify_change(name, self._configs[name])
    
    def watch(self, name: str, callback: Callable):
        """监听配置变更"""
        self._callbacks[name] = callback
    
    async def _notify_change(self, name: str, config: ConfigSection):
        """通知配置变更"""
        if name in self._callbacks:
            try:
                await self._callbacks[name](config)
            except Exception as e:
                logger.error(f"Config callback error: {e}")
    
    async def _reload_loop(self):
        """热加载循环"""
        while self._running:
            try:
                await asyncio.sleep(self.hot_reload_interval)
                
                for path in self.config_dir.glob("*.yaml"):
                    name = path.stem
                    mtime = path.stat().st_mtime
                    
                    async with self._lock:
                        config = self._configs.get(name)
                    
                    if config and config.updated_at.timestamp() < mtime:
                        await self.load(name)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reload error: {e}")
    
    def list_configs(self) -> list:
        """列出所有配置"""
        return list(self._configs.keys())
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_configs": len(self._configs),
            "hot_reload_enabled": self.enable_hot_reload,
            "callbacks_registered": len(self._callbacks)
        }


# 全局配置管理器
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
