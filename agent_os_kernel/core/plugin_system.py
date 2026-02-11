# -*- coding: utf-8 -*-
"""
Plugin System for Agent-OS-Kernel

提供完整的插件系统，包括：
- 插件加载 (Plugin Loading)
- 插件注册 (Plugin Registration)
- 插件通信 (Plugin Communication)
- 插件生命周期 (Plugin Lifecycle)
"""

import importlib
import importlib.util
import inspect
import os
import sys
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime


class PluginState(Enum):
    """插件状态枚举"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UNLOADING = "unloading"


class PluginEventType(Enum):
    """插件事件类型"""
    LOADED = "plugin_loaded"
    UNLOADED = "plugin_unloaded"
    ENABLED = "plugin_enabled"
    DISABLED = "plugin_disabled"
    ERROR = "plugin_error"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    STATE_CHANGED = "state_changed"


@dataclass
class PluginInfo:
    """插件元信息"""
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = "main"
    state: PluginState = PluginState.UNLOADED
    loaded_at: Optional[datetime] = None
    config_schema: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
            "state": self.state.value,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "config_schema": self.config_schema,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginInfo':
        """从字典创建"""
        return cls(
            plugin_id=data["plugin_id"],
            name=data["name"],
            version=data["version"],
            author=data["author"],
            description=data["description"],
            dependencies=data.get("dependencies", []),
            entry_point=data.get("entry_point", "main"),
            state=PluginState(data.get("state", "unloaded")),
            loaded_at=datetime.fromisoformat(data["loaded_at"]) if data.get("loaded_at") else None,
            config_schema=data.get("config_schema", {}),
        )


@dataclass
class BasePlugin:
    """插件基类"""
    plugin_id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    state: PluginState = PluginState.UNLOADED
    config: Dict[str, Any] = field(default_factory=dict)
    
    def initialize(self) -> bool:
        """初始化插件"""
        return True
    
    def enable(self) -> bool:
        """启用插件"""
        self.state = PluginState.ENABLED
        return True
    
    def disable(self) -> True:
        """禁用插件"""
        self.state = PluginState.DISABLED
        return True
    
    def shutdown(self) -> bool:
        """关闭插件"""
        self.state = PluginState.UNLOADED
        return True
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            plugin_id=self.plugin_id,
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            state=self.state,
        )


@dataclass
class PluginMessage:
    """插件消息"""
    message_id: str
    source_plugin: str
    target_plugin: Optional[str]
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "source_plugin": self.source_plugin,
            "target_plugin": self.target_plugin,
            "message_type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "correlation_id": self.correlation_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMessage':
        """从字典创建"""
        return cls(
            message_id=data["message_id"],
            source_plugin=data["source_plugin"],
            target_plugin=data.get("target_plugin"),
            message_type=data["message_type"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            reply_to=data.get("reply_to"),
            correlation_id=data.get("correlation_id"),
        )


@dataclass
class PluginEvent:
    """插件事件"""
    event_type: PluginEventType
    plugin_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type.value,
            "plugin_id": self.plugin_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class PluginBase(ABC):
    """插件基类 - 所有插件必须继承此类"""
    
    def __init__(self, plugin_id: str, name: str, version: str):
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.state = PluginState.UNLOADED
        self.config: Dict[str, Any] = {}
        self.plugin_manager: Optional['PluginManager'] = None
        
    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件 - 在加载后调用"""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """关闭插件 - 在卸载前调用"""
        pass
    
    def enable(self) -> bool:
        """启用插件"""
        self.state = PluginState.ENABLED
        return True
    
    def disable(self) -> bool:
        """禁用插件"""
        self.state = PluginState.DISABLED
        return True
    
    def on_message(self, message: PluginMessage) -> Optional[PluginMessage]:
        """接收消息 - 子类可重写"""
        return None
    
    def on_event(self, event: PluginEvent) -> None:
        """接收事件 - 子类可重写"""
        pass
    
    def get_dependencies(self) -> List[str]:
        """获取依赖列表"""
        return []
    
    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        return {}
    
    def send_message(self, target_plugin: str, message_type: str, payload: Dict[str, Any]) -> str:
        """发送消息给其他插件"""
        if self.plugin_manager:
            return self.plugin_manager.send_message(
                source_plugin=self.plugin_id,
                target_plugin=target_plugin,
                message_type=message_type,
                payload=payload
            )
        raise RuntimeError("Plugin is not attached to a plugin manager")
    
    def broadcast_message(self, message_type: str, payload: Dict[str, Any]) -> List[str]:
        """广播消息给所有插件"""
        if self.plugin_manager:
            return self.plugin_manager.broadcast_message(
                source_plugin=self.plugin_id,
                message_type=message_type,
                payload=payload
            )
        raise RuntimeError("Plugin is not attached to a plugin manager")
    
    def publish_event(self, event_type: PluginEventType, data: Dict[str, Any] = None) -> None:
        """发布事件"""
        if self.plugin_manager:
            self.plugin_manager.publish_event(
                plugin_id=self.plugin_id,
                event_type=event_type,
                data=data or {}
            )
        else:
            raise RuntimeError("Plugin is not attached to a plugin manager")


class PluginManager:
    """
    插件管理器
    
    提供完整的插件生命周期管理和通信功能。
    """
    
    def __init__(self, plugin_dir: Optional[str] = None):
        self._plugins: Dict[str, PluginBase] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._event_handlers: Dict[PluginEventType, List[Callable]] = {}
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._message_channels: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._plugin_dir = plugin_dir
        self._message_history: List[PluginMessage] = []
        self._event_history: List[PluginEvent] = []
        
    @property
    def plugins(self) -> Dict[str, PluginBase]:
        """获取所有已加载的插件"""
        return self._plugins.copy()
    
    @property
    def plugin_count(self) -> int:
        """获取插件数量"""
        return len(self._plugins)
    
    def register_plugin(self, plugin: PluginBase) -> bool:
        """
        注册插件到管理器
        
        Args:
            plugin: 插件实例
            
        Returns:
            bool: 是否注册成功
        """
        with self._lock:
            if plugin.plugin_id in self._plugins:
                return False
            
            # 检查依赖
            dependencies = plugin.get_dependencies()
            for dep in dependencies:
                if dep not in self._plugins and dep not in self._plugin_info:
                    raise RuntimeError(f"Missing dependency: {dep}")
            
            # 创建插件信息
            info = PluginInfo(
                plugin_id=plugin.plugin_id,
                name=plugin.name,
                version=plugin.version,
                author="Unknown",
                description=plugin.__doc__ or "",
                dependencies=dependencies,
                state=PluginState.LOADED,
            )
            
            plugin.plugin_manager = self
            self._plugins[plugin.plugin_id] = plugin
            self._plugin_info[plugin.plugin_id] = info
            
            self._publish_event(plugin.plugin_id, PluginEventType.LOADED)
            return True
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        注销插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否成功注销
        """
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins[plugin_id]
            
            # 调用关闭方法
            try:
                plugin.shutdown()
            except Exception as e:
                print(f"Error shutting down plugin {plugin_id}: {e}")
            
            # 清理消息处理器
            if plugin_id in self._message_handlers:
                del self._message_handlers[plugin_id]
            
            # 移除插件
            del self._plugins[plugin_id]
            if plugin_id in self._plugin_info:
                self._plugin_info[plugin_id].state = PluginState.UNLOADED
            
            self._publish_event(plugin_id, PluginEventType.UNLOADED)
            return True
    
    def load_plugin(self, plugin_path: str) -> bool:
        """
        从文件路径加载插件模块
        
        Args:
            plugin_path: 插件Python文件路径
            
        Returns:
            bool: 是否加载成功
        """
        with self._lock:
            path = Path(plugin_path)
            if not path.exists():
                raise FileNotFoundError(f"Plugin file not found: {plugin_path}")
            
            # 动态导入模块
            module_name = path.stem
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Cannot load module: {module_name}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找插件类
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (inspect.isclass(attr) and 
                    issubclass(attr, PluginBase) and 
                    attr != PluginBase):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                raise RuntimeError(f"No PluginBase subclass found in {plugin_path}")
            
            # 实例化并注册插件
            plugin = plugin_class()
            return self.register_plugin(plugin)
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """
        启用插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否启用成功
        """
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins[plugin_id]
            if plugin.state == PluginState.ERROR:
                return False
            
            try:
                result = plugin.enable()
                if result:
                    self._plugin_info[plugin_id].state = PluginState.ENABLED
                    self._publish_event(plugin_id, PluginEventType.ENABLED)
                return result
            except Exception as e:
                print(f"Error enabling plugin {plugin_id}: {e}")
                return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """
        禁用插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否禁用成功
        """
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins[plugin_id]
            try:
                result = plugin.disable()
                if result:
                    self._plugin_info[plugin_id].state = PluginState.DISABLED
                    self._publish_event(plugin_id, PluginEventType.DISABLED)
                return result
            except Exception as e:
                print(f"Error disabling plugin {plugin_id}: {e}")
                return False
    
    def initialize_plugin(self, plugin_id: str) -> bool:
        """
        初始化插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            bool: 是否初始化成功
        """
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins[plugin_id]
            if plugin.state not in [PluginState.LOADED, PluginState.DISABLED]:
                return False
            
            try:
                result = plugin.initialize()
                if result:
                    self._plugin_info[plugin_id].loaded_at = datetime.now()
                    if plugin.state == PluginState.LOADED:
                        self._plugin_info[plugin_id].state = PluginState.ENABLED
                        plugin.state = PluginState.ENABLED
                return result
            except Exception as e:
                print(f"Error initializing plugin {plugin_id}: {e}")
                self._plugin_info[plugin_id].state = PluginState.ERROR
                plugin.state = PluginState.ERROR
                self._publish_event(plugin_id, PluginEventType.ERROR, {"error": str(e)})
                return False
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """
        获取插件实例
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            Optional[PluginBase]: 插件实例，不存在返回None
        """
        return self._plugins.get(plugin_id)
    
    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """
        获取插件信息
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            Optional[PluginInfo]: 插件信息
        """
        return self._plugin_info.get(plugin_id)
    
    def list_plugins(self) -> List[PluginInfo]:
        """列出所有已注册的插件信息"""
        return list(self._plugin_info.values())
    
    def list_plugin_ids(self) -> List[str]:
        """列出所有插件ID"""
        return list(self._plugins.keys())
    
    # === 消息通信 ===
    
    def send_message(
        self,
        source_plugin: str,
        target_plugin: str,
        message_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> str:
        """
        发送消息给指定插件
        
        Args:
            source_plugin: 源插件ID
            target_plugin: 目标插件ID
            message_type: 消息类型
            payload: 消息负载
            correlation_id: 关联ID（用于请求/响应）
            
        Returns:
            str: 消息ID
        """
        with self._lock:
            if target_plugin not in self._plugins:
                raise ValueError(f"Target plugin not found: {target_plugin}")
            
            message = PluginMessage(
                message_id=str(uuid.uuid4()),
                source_plugin=source_plugin,
                target_plugin=target_plugin,
                message_type=message_type,
                payload=payload,
                correlation_id=correlation_id
            )
            
            # 添加到历史记录
            self._message_history.append(message)
            
            # 发送给目标插件
            plugin = self._plugins[target_plugin]
            if plugin.state == PluginState.ENABLED:
                try:
                    response = plugin.on_message(message)
                    if response:
                        self._message_history.append(response)
                    self._publish_event(source_plugin, PluginEventType.MESSAGE_SENT, message.to_dict())
                    if response:
                        self._publish_event(target_plugin, PluginEventType.MESSAGE_RECEIVED, response.to_dict())
                except Exception as e:
                    print(f"Error processing message: {e}")
            
            return message.message_id
    
    def broadcast_message(
        self,
        source_plugin: str,
        message_type: str,
        payload: Dict[str, Any]
    ) -> List[str]:
        """
        广播消息给所有插件
        
        Args:
            source_plugin: 源插件ID
            message_type: 消息类型
            payload: 消息负载
            
        Returns:
            List[str]: 消息ID列表
        """
        message_ids = []
        for plugin_id in self._plugins:
            if plugin_id != source_plugin:
                msg_id = self.send_message(
                    source_plugin=source_plugin,
                    target_plugin=plugin_id,
                    message_type=message_type,
                    payload=payload
                )
                message_ids.append(msg_id)
        return message_ids
    
    def register_message_handler(
        self,
        plugin_id: str,
        message_type: str,
        handler: Callable[[PluginMessage], Optional[PluginMessage]]
    ) -> None:
        """
        注册消息处理器
        
        Args:
            plugin_id: 插件ID
            message_type: 消息类型
            handler: 处理函数
        """
        key = f"{plugin_id}:{message_type}"
        if key not in self._message_handlers:
            self._message_handlers[key] = []
        self._message_handlers[key].append(handler)
    
    def register_channel_handler(
        self,
        channel: str,
        handler: Callable[[PluginMessage], None]
    ) -> None:
        """
        注册通道处理器（用于订阅特定通道的消息）
        
        Args:
            channel: 通道名称
            handler: 处理函数
        """
        if channel not in self._message_channels:
            self._message_channels[channel] = []
        self._message_channels[channel].append(handler)
    
    # === 事件系统 ===
    
    def register_event_handler(
        self,
        event_type: PluginEventType,
        handler: Callable[[PluginEvent], None]
    ) -> None:
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def _publish_event(
        self,
        plugin_id: str,
        event_type: PluginEventType,
        data: Dict[str, Any] = None
    ) -> None:
        """
        发布事件
        
        Args:
            plugin_id: 插件ID
            event_type: 事件类型
            data: 事件数据
        """
        event = PluginEvent(
            event_type=event_type,
            plugin_id=plugin_id,
            data=data or {}
        )
        
        self._event_history.append(event)
        
        # 调用注册的处理器
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")
    
    def publish_event(
        self,
        plugin_id: str,
        event_type: PluginEventType,
        data: Dict[str, Any] = None
    ) -> None:
        """
        发布事件（公共方法）
        
        Args:
            plugin_id: 插件ID
            event_type: 事件类型
            data: 事件数据
        """
        self._publish_event(plugin_id, event_type, data)
    
    # === 生命周期管理 ===
    
    def shutdown(self) -> None:
        """关闭管理器，卸载所有插件"""
        with self._lock:
            for plugin_id in list(self._plugins.keys()):
                self.unregister_plugin(plugin_id)
            
            # 清理所有处理器
            self._event_handlers.clear()
            self._message_handlers.clear()
            self._message_channels.clear()
    
    def get_plugin_state(self, plugin_id: str) -> Optional[PluginState]:
        """
        获取插件状态
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            Optional[PluginState]: 插件状态
        """
        if plugin_id in self._plugin_info:
            return self._plugin_info[plugin_id].state
        return None
    
    def get_message_history(self, plugin_id: Optional[str] = None) -> List[PluginMessage]:
        """
        获取消息历史
        
        Args:
            plugin_id: 可选的插件ID过滤
            
        Returns:
            List[PluginMessage]: 消息列表
        """
        if plugin_id:
            return [m for m in self._message_history 
                   if m.source_plugin == plugin_id or m.target_plugin == plugin_id]
        return self._message_history.copy()
    
    def get_event_history(self, plugin_id: Optional[str] = None) -> List[PluginEvent]:
        """
        获取事件历史
        
        Args:
            plugin_id: 可选的插件ID过滤
            
        Returns:
            List[PluginEvent]: 事件列表
        """
        if plugin_id:
            return [e for e in self._event_history if e.plugin_id == plugin_id]
        return self._event_history.copy()


def create_plugin_manager(plugin_dir: Optional[str] = None) -> PluginManager:
    """
    创建插件管理器
    
    Args:
        plugin_dir: 插件目录路径
        
    Returns:
        PluginManager: 插件管理器实例
    """
    return PluginManager(plugin_dir=plugin_dir)


def discover_plugins(plugin_dir: str) -> List[str]:
    """
    发现目录中的所有插件文件
    
    Args:
        plugin_dir: 插件目录路径
        
    Returns:
        List[str]: 插件文件路径列表
    """
    plugin_dir_path = Path(plugin_dir)
    if not plugin_dir_path.exists() or not plugin_dir_path.is_dir():
        return []
    
    plugins = []
    for file_path in plugin_dir_path.glob("*.py"):
        # 跳过以_开头的文件
        if not file_path.name.startswith("_"):
            plugins.append(str(file_path))
    
    return plugins
