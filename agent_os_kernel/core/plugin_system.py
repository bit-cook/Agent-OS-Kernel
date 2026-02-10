# -*- coding: utf-8 -*-
"""插件系统"""

import importlib
import sys
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, field

from .types import PluginInfo


@dataclass
class Plugin:
    """插件"""
    info: PluginInfo
    module: Any
    enabled: bool = True
    hooks: Dict[str, Any] = field(default_factory=dict)


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List] = {}
        self._enabled = True
    
    def register_plugin(self, plugin_path: str) -> bool:
        """注册插件"""
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("plugin", plugin_path)
            if spec is None or spec.loader is None:
                return False
            
            module = importlib.util.module_from_spec(spec)
            sys.modules["plugin"] = module
            spec.loader.exec_module(module)
            
            # 获取插件信息
            if not hasattr(module, 'get_plugin_info'):
                return False
            
            info = module.get_plugin_info()
            if not isinstance(info, PluginInfo):
                return False
            
            # 创建插件实例
            plugin = Plugin(info=info, module=module)
            
            # 注册钩子
            if hasattr(module, 'register_hooks'):
                module.register_hooks(self)
            
            self._plugins[info.name] = plugin
            return True
            
        except Exception as e:
            print(f"Failed to register plugin {plugin_path}: {e}")
            return False
    
    def unregister_plugin(self, name: str) -> bool:
        """注销插件"""
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False
    
    def register_hook(self, hook_name: str, callback: Any, priority: int = 0):
        """注册钩子"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        
        self._hooks[hook_name].append({
            'callback': callback,
            'priority': priority
        })
        
        # 按优先级排序
        self._hooks[hook_name].sort(key=lambda x: x['priority'], reverse=True)
    
    def unregister_hook(self, hook_name: str, callback: Any):
        """注销钩子"""
        if hook_name in self._hooks:
            self._hooks[hook_name] = [
                h for h in self._hooks[hook_name]
                if h['callback'] != callback
            ]
    
    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """触发钩子"""
        results = []
        
        if hook_name not in self._hooks:
            return results
        
        for hook in self._hooks[hook_name]:
            try:
                result = hook['callback'](*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Hook {hook_name} failed: {e}")
        
        return results
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件"""
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件"""
        return [p.info for p in self._plugins.values()]
    
    def enable_plugin(self, name: str) -> bool:
        """启用插件"""
        if name in self._plugins:
            self._plugins[name].enabled = True
            return True
        return False
    
    def disable_plugin(self, name: str) -> bool:
        """禁用插件"""
        if name in self._plugins:
            self._plugins[name].enabled = False
            return True
        return False
    
    def get_plugin_info_dict(self) -> Dict[str, Dict]:
        """获取插件信息字典"""
        return {
            name: {
                'info': plugin.info.to_dict(),
                'enabled': plugin.enabled,
                'hooks': list(plugin.hooks.keys())
            }
            for name, plugin in self._plugins.items()
        }


# 内置钩子名称常量
class Hooks:
    """内置钩子名称"""
    BEFORE_AGENT_SPAWN = "before_agent_spawn"
    AFTER_AGENT_SPAWN = "after_agent_spawn"
    BEFORE_AGENT_RUN = "before_agent_run"
    AFTER_AGENT_RUN = "after_agent_run"
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    ON_ERROR = "on_error"
    ON_SHUTDOWN = "on_shutdown"
    ON_CHECKPOINT = "on_checkpoint"
    ON_RESTORE = "on_restore"
