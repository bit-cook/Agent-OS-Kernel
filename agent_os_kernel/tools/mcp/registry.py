# -*- coding: utf-8 -*-
"""MCP Tool Registry - MCP 工具注册表

将 MCP 工具注册到 Agent-OS-Kernel 工具系统中。
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .client import MCPManager, MCPServerConfig, MCPToolCall, MCPToolResult
from ..base import Tool, ToolParameter
from ..registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class MCPToolWrapper:
    """MCP 工具包装器"""
    server_name: str
    tool_name: str
    description: str
    parameters: List[ToolParameter]


class MCPToolRegistry:
    """MCP 工具注册表"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self._tool_registry = tool_registry
        self._mcp_manager = MCPManager()
        self._wrapped_tools: Dict[str, MCPToolWrapper] = {}
    
    def add_server(self, name: str, command: str, args: List[str] = None, env: Dict[str, str] = None, url: str = None) -> bool:
        """添加 MCP 服务器"""
        config = MCPServerConfig(
            name=name,
            command=command or "",
            args=args or [],
            env=env or {},
            url=url
        )
        return self._mcp_manager.add_server(name, config)
    
    async def connect_server(self, name: str) -> bool:
        """连接到 MCP 服务器"""
        return await self._mcp_manager.connect(name)
    
    async def discover_tools(self, server_name: Optional[str] = None) -> int:
        """发现并注册工具"""
        tools_found = 0
        
        try:
            tools_by_server = await self._mcp_manager.list_tools(server_name)
            
            for server_name, tools in tools_by_server.items():
                for tool in tools:
                    # 包装 MCP 工具
                    wrapped = self._wrap_tool(server_name, tool)
                    self._wrapped_tools[wrapped.name] = wrapped
                    
                    # 注册到工具表
                    self._tool_registry.register(
                        MCPWrappedTool(wrapped),
                        replace_existing=True
                    )
                    tools_found += 1
                    logger.info(f"Registered MCP tool: {wrapped.name}")
            
            return tools_found
        except Exception as e:
            logger.error(f"Failed to discover MCP tools: {e}")
            return 0
    
    def _wrap_tool(self, server_name: str, tool) -> MCPToolWrapper:
        """包装 MCP 工具"""
        # 转换 schema 到参数
        parameters = []
        schema = getattr(tool, 'input_schema', {})
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        for param_name, param_info in properties.items():
            param = ToolParameter(
                name=param_name,
                type=param_info.get('type', 'string'),
                description=param_info.get('description', ''),
                required=param_name in required,
                default=param_info.get('default'),
                enum=param_info.get('enum')
            )
            parameters.append(param)
        
        return MCPToolWrapper(
            server_name=server_name,
            tool_name=tool.name,
            description=tool.description or '',
            parameters=parameters
        )
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """调用 MCP 工具"""
        if tool_name not in self._wrapped_tools:
            return {
                'success': False,
                'error': f'Tool not found: {tool_name}'
            }
        
        wrapped = self._wrapped_tools[tool_name]
        
        try:
            result = await self._mcp_manager.call_tool(
                wrapped.server_name,
                MCPToolCall(tool=wrapped.tool_name, arguments=kwargs)
            )
            
            if result.is_error:
                return {
                    'success': False,
                    'error': result.error
                }
            
            return {
                'success': True,
                'data': result.content
            }
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        return await self._mcp_manager.health_check()
    
    async def close_all(self):
        """关闭所有连接"""
        await self._mcp_manager.close_all()
    
    def list_wrapped_tools(self) -> List[Dict[str, Any]]:
        """列出已包装的工具"""
        return [
            {
                'name': name,
                'server': wrapped.server_name,
                'tool_name': wrapped.tool_name,
                'description': wrapped.description,
                'parameters': [
                    {
                        'name': p.name,
                        'type': p.type,
                        'required': p.required
                    }
                    for p in wrapped.parameters
                ]
            }
            for name, wrapped in self._wrapped_tools.items()
        ]


class MCPWrappedTool(Tool):
    """MCP 工具包装类"""
    
    def __init__(self, wrapper: MCPToolWrapper):
        self._wrapper = wrapper
        super().__init__(
            name=f"mcp_{wrapper.tool_name}",
            description=wrapper.description
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return self._wrapper.parameters
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具调用"""
        from .client import MCPManager
        manager = self._get_manager()
        return await manager.call_tool(self.name, **kwargs)
    
    def _get_manager(self) -> MCPManager:
        """获取 MCP 管理器 (单例模式)"""
        # 这里应该通过依赖注入获取
        # 简化处理，返回全局实例
        return _global_mcp_registry._mcp_manager if hasattr(self, '_registry') else None


# 全局 MCP 注册表实例
_global_mcp_registry: Optional[MCPToolRegistry] = None


def init_mcp_registry(tool_registry: ToolRegistry) -> MCPToolRegistry:
    """初始化全局 MCP 注册表"""
    global _global_mcp_registry
    _global_mcp_registry = MCPToolRegistry(tool_registry)
    return _global_mcp_registry


def get_mcp_registry() -> Optional[MCPToolRegistry]:
    """获取全局 MCP 注册表"""
    return _global_mcp_registry
