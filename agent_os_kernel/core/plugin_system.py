# -*- coding: utf-8 -*-
"""
Plugin System - 插件系统

支持：
1. 插件加载/卸载
2. 插件生命周期管理
3. 插件钩子注册
4. 插件依赖管理
"""

import asyncio
import logging
import importlib
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import inspect
import sys

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    state: PluginState = PluginState.UNLOADED
    loaded_at: Optional[datetime] = None
    hooks: Dict[str, List[Callable]] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


class BasePlugin(ABC):
    """插件基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述"""
        pass
    
    def initialize(self, kernel: 'PluginManager'):
        """初始化"""
        pass
    
    def enable(self):
        """启用"""
        pass
    
    def disable(self):
        """禁用"""
        pass
    
    def cleanup(self):
        """清理"""
        pass
    
    def register_hook(self, event: str, callback: Callable):
        """注册钩子"""
        pass


class PluginManager:
    """
    插件管理器
    
    功能：
    1. 插件加载/卸载
    2. 插件启用/禁用
    3. 钩子管理
    4. 依赖解析
    """
    
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._info: Dict[str, PluginInfo] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._kernel = None
        self._lock = asyncio.Lock()
    
    def initialize(self, kernel):
        """初始化"""
        self._kernel = kernel
        logger.info("PluginManager initialized")
    
    async def load_plugin(self, plugin_class: type, **kwargs) -> PluginInfo:
        """加载插件"""
        async with self._lock:
            # 检查是否已加载
            if plugin_class.__name__ in self._plugins:
                logger.warning(f"Plugin already loaded: {plugin_class.__name__}")
                return self._info[plugin_class.__name__]
            
            # 创建插件实例
            plugin = plugin_class(**kwargs)
            
            # 创建信息
            info = PluginInfo(
                name=plugin.name,
                version=plugin.version,
                description=plugin.description,
                author=getattr(plugin, 'author', 'Unknown'),
                state=PluginState.LOADING
            )
            
            # 初始化
            try:
                plugin.initialize(self)
                info.state = PluginState.LOADED
                info.loaded_at = datetime.now()
                
                self._plugins[plugin_class.__name__] = plugin
                self._info[plugin_class.__name__] = info
                
                logger.info(f"Plugin loaded: {plugin.name} v{plugin.version}")
                
            except Exception as e:
                info.state = PluginState.ERROR
                logger.error(f"Plugin load failed: {e}")
                raise
        
        return info
    
    async def enable_plugin(self, name: str) -> bool:
        """启用插件"""
        async with self._lock:
            if name not in self._plugins:
                logger.warning(f"Plugin not found: {name}")
                return False
            
            plugin = self._plugins[name]
            
            try:
                plugin.enable()
                self._info[name].state = PluginState.ENABLED
                logger.info(f"Plugin enabled: {name}")
                return True
            except Exception as e:
                logger.error(f"Plugin enable failed: {e}")
                return False
    
    async def disable_plugin(self, name: str) -> bool:
        """禁用插件"""
        async with self._lock:
            if name not in self._plugins:
                return False
            
            plugin = self._plugins[name]
            
            try:
                plugin.disable()
                self._info[name].state = PluginState.DISABLED
                logger.info(f"Plugin disabled: {name}")
                return True
            except Exception as e:
                logger.error(f"Plugin disable failed: {e}")
                return False
    
    async def unload_plugin(self, name: str) -> bool:
        """卸载插件"""
        async with self._lock:
            if name not in self._plugins:
                return False
            
            plugin = self._plugins[name]
            
            try:
                # 清理
                plugin.cleanup()
                
                # 移除
                del self._plugins[name]
                del self._info[name]
                
                logger.info(f"Plugin unloaded: {name}")
                return True
            except Exception as e:
                logger.error(f"Plugin unload failed: {e}")
                return False
    
    def register_hook(self, plugin_name: str, event: str, callback: Callable):
        """注册钩子"""
        if event not in self._hooks:
            self._hooks[event] = []
        
        self._hooks[event].append({
            'plugin': plugin_name,
            'callback': callback
        })
        
        logger.info(f"Hook registered: {event} -> {plugin_name}")
    
    async def trigger_hook(self, event: str, *args, **kwargs):
        """触发钩子"""
        if event not in self._hooks:
            return []
        
        results = []
        
        for hook in self._hooks[event]:
            try:
                result = await hook['callback'](*args, **kwargs)
                results.append({
                    'plugin': hook['plugin'],
                    'result': result
                })
            except Exception as e:
                logger.error(f"Hook error: {e}")
        
        return results
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """获取插件"""
        return self._plugins.get(name)
    
    def get_info(self, name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._info.get(name)
    
    def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件"""
        return list(self._info.values())
    
    def list_loaded(self) -> List[str]:
        """列出已加载的插件"""
        return [name for name, info in self._info.items() 
                if info.state in (PluginState.LOADED, PluginState.ENABLED)]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            'total_plugins': len(self._plugins),
            'loaded': len([p for p in self._info.values() if p.state == PluginState.LOADED]),
            'enabled': len([p for p in self._info.values() if p.state == PluginState.ENABLED]),
            'hooks': {k: len(v) for k, v in self._hooks.items()}
        }


# 示例插件
class LoggingPlugin(BasePlugin):
    """日志插件"""
    
    @property
    def name(self) -> str:
        return "logging-plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Logging plugin for Agent OS Kernel"
    
    def initialize(self, manager: PluginManager):
        manager.register_hook(self.name, "agent_created", self.on_agent_created)
    
    async def on_agent_created(self, agent_id: str):
        logger.info(f"Agent created: {agent_id}")


# 便捷函数
def create_plugin_manager() -> PluginManager:
    """创建插件管理器"""
    return PluginManager()


def load_plugin_from_module(module_path: str) -> type:
    """从模块加载插件类"""
    module = importlib.import_module(module_path)
    
    for name, obj in inspect.getmembers(module):
        if (inspect.isclass(obj) and 
            issubclass(obj, BasePlugin) and 
            obj != BasePlugin):
            return obj
    
    raise ValueError(f"No plugin class found in {module_path}")
