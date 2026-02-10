# -*- coding: utf-8 -*-
"""MCP Client - Model Context Protocol 客户端

支持连接 MCP 服务器并调用工具。
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import httpx
import structlog

logger = structlog.get_logger(__name__)


class MCPTransport(Enum):
    """MCP 传输方式"""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    command: str  # STDIO 方式的命令
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None  # HTTP/WebSocket 方式
    timeout: float = 30.0


@dataclass
class MCPToolDefinition:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class MCPToolCall:
    """MCP 工具调用请求"""
    tool: str
    arguments: Dict[str, Any]


@dataclass
class MCPToolResult:
    """MCP 工具调用结果"""
    content: List[Dict[str, Any]]
    is_error: bool = False
    error: Optional[str] = None


class MCPClient:
    """MCP 客户端"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._transport = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._tools: Dict[str, MCPToolDefinition] = {}
    
    async def connect(self) -> bool:
        """连接到 MCP 服务器"""
        try:
            if self.config.url:
                # HTTP/WebSocket 方式
                self._http_client = httpx.AsyncClient(timeout=self.config.timeout)
                logger.info(f"Connected to MCP server: {self.config.name}")
            else:
                # STDIO 方式 (需要实现进程管理)
                logger.info(f"STDIO server not implemented yet: {self.config.name}")
                return False
            
            self._connected = True
            await self._initialize()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def _initialize(self):
        """初始化连接"""
        if self._http_client:
            # 发送 initialize 请求
            response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            })
            logger.info(f"MCP Server {self.config.name} initialized")
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到 MCP 服务器"""
        if not self._http_client:
            raise RuntimeError("Not connected to MCP server")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            response = await self._http_client.post(
                self.config.url,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            raise
    
    async def list_tools(self) -> List[MCPToolDefinition]:
        """列出可用工具"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            response = await self._send_request("tools/list", {})
            
            self._tools = {}
            for tool_data in response.get("result", {}).get("tools", []):
                tool = MCPToolDefinition(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    annotations=tool_data.get("annotations")
                )
                self._tools[tool.name] = tool
            
            return list(self._tools.values())
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def call_tool(self, call: MCPToolCall) -> MCPToolResult:
        """调用工具"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            response = await self._send_request("tools/call", {
                "name": call.tool,
                "arguments": call.arguments
            })
            
            result = response.get("result", {})
            content = result.get("content", [])
            
            return MCPToolResult(
                content=content,
                is_error=result.get("isError", False),
                error=result.get("error", {}).get("message") if result.get("isError") else None
            )
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return MCPToolResult(
                content=[],
                is_error=True,
                error=str(e)
            )
    
    async def close(self):
        """关闭连接"""
        self._connected = False
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info(f"Disconnected from MCP server: {self.config.name}")


class MCPManager:
    """MCP 连接管理器"""
    
    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}
        self._default_timeout: float = 30.0
    
    def add_server(self, name: str, config: MCPServerConfig) -> bool:
        """添加 MCP 服务器"""
        try:
            self._clients[name] = MCPClient(config)
            logger.info(f"Added MCP server: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add MCP server: {e}")
            return False
    
    async def connect(self, name: str) -> bool:
        """连接到 MCP 服务器"""
        if name not in self._clients:
            logger.error(f"MCP server not found: {name}")
            return False
        return await self._clients[name].connect()
    
    async def connect_all(self):
        """连接所有服务器"""
        for name in self._clients:
            await self.connect(name)
    
    async def list_tools(self, server_name: Optional[str] = None) -> Dict[str, List[MCPToolDefinition]]:
        """列出所有工具"""
        tools = {}
        if server_name:
            if server_name in self._clients:
                tools[server_name] = await self._clients[server_name].list_tools()
        else:
            for name, client in self._clients.items():
                if client._connected:
                    tools[name] = await client.list_tools()
        return tools
    
    async def call_tool(self, server_name: str, call: MCPToolCall) -> MCPToolResult:
        """调用工具"""
        if server_name not in self._clients:
            raise ValueError(f"MCP server not found: {server_name}")
        return await self._clients[server_name].call_tool(call)
    
    async def close_all(self):
        """关闭所有连接"""
        for client in self._clients.values():
            if client._connected:
                await client.close()
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        return {
            name: client._connected
            for name, client in self._clients.items()
        }
