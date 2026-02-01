# -*- coding: utf-8 -*-
"""
Tool System - 工具调用系统

实现 Agent-Native CLI 标准：
- 输出结构化（--json 支持）
- 错误码标准化（类似 HTTP 状态码）
- 自带发现机制（--desc 支持）

核心洞察（来自冯若航《AI Agent 的操作系统时刻》）：
- MCP 走了弯路：Token 开销大，重新发明轮子
- Unix CLI 已经优雅地做了 55 年
- 终局是 Agent-Native CLI：结构化输出、标准化错误码、机器可读
"""

import json
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ToolErrorCode(Enum):
    """
    工具错误码 - 类似 HTTP 状态码的语义
    
    2xx - 成功
    4xx - 客户端错误（参数错误、权限不足等）
    5xx - 服务器错误（工具执行失败等）
    """
    # 成功
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    
    # 客户端错误
    BAD_REQUEST = 400           # 参数错误
    UNAUTHORIZED = 401          # 未授权
    FORBIDDEN = 403             # 禁止访问
    NOT_FOUND = 404             # 资源不存在
    TIMEOUT = 408               # 超时
    CONFLICT = 409              # 冲突
    
    # 服务器错误
    INTERNAL_ERROR = 500        # 内部错误
    NOT_IMPLEMENTED = 501       # 未实现
    SERVICE_UNAVAILABLE = 503   # 服务不可用


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # string, integer, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 --desc 输出）"""
        result = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.enum:
            result["enum"] = self.enum
        return result


@dataclass
class ToolResult:
    """
    工具执行结果 - Agent-Native CLI 标准输出格式
    
    Attributes:
        success: 是否成功
        data: 返回数据
        error: 错误信息
        error_code: 错误码（ToolErrorCode）
        metadata: 元数据（执行时间、资源使用等）
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: ToolErrorCode = ToolErrorCode.SUCCESS
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 --json 输出）"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code.value,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def success(cls, data: Any = None, metadata: Optional[Dict] = None) -> 'ToolResult':
        """创建成功结果"""
        return cls(
            success=True,
            data=data,
            error_code=ToolErrorCode.SUCCESS,
            metadata=metadata or {}
        )
    
    @classmethod
    def error(cls, message: str, code: ToolErrorCode = ToolErrorCode.INTERNAL_ERROR,
              metadata: Optional[Dict] = None) -> 'ToolResult':
        """创建错误结果"""
        return cls(
            success=False,
            error=message,
            error_code=code,
            metadata=metadata or {}
        )


class Tool(ABC):
    """
    工具抽象基类 - Agent-Native CLI 标准
    
    所有工具必须实现：
    1. name() - 工具名称（唯一标识）
    2. description() - 工具描述（给 LLM 看）
    3. parameters() - 参数定义
    4. execute() - 执行逻辑
    
    可选实现：
    - get_capabilities() - 返回机器可读的能力描述（--desc）
    - validate_params() - 参数验证
    """
    
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识，如：query_db）"""
        pass
    
    @abstractmethod
    def description(self) -> str:
        """工具描述（给 LLM 看，如：Query database with SQL）"""
        pass
    
    def parameters(self) -> List[ToolParameter]:
        """参数定义列表"""
        return []
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        必须返回 ToolResult，包含结构化输出和标准化错误码。
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取工具能力描述（用于 --desc 输出）
        
        机器可读的能力描述，让 Agent 自动发现工具功能。
        """
        return {
            "name": self.name(),
            "description": self.description(),
            "parameters": [p.to_dict() for p in self.parameters()],
            "examples": self.get_examples(),
        }
    
    def get_examples(self) -> List[Dict[str, Any]]:
        """获取使用示例"""
        return []
    
    def validate_params(self, **kwargs) -> Tuple[bool, str]:
        """
        验证参数
        
        Returns:
            (是否有效, 错误信息)
        """
        params = {p.name: p for p in self.parameters()}
        
        # 检查必需参数
        for name, param in params.items():
            if param.required and name not in kwargs:
                return False, f"Missing required parameter: {name}"
        
        # 检查额外参数
        for name in kwargs:
            if name not in params:
                return False, f"Unknown parameter: {name}"
        
        return True, ""
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具的 JSON Schema（用于 LLM function calling）"""
        params = self.parameters()
        
        properties = {}
        required = []
        
        for param in params:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name(),
            "description": self.description(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }


class SimpleTool(Tool):
    """
    简单工具包装器
    
    用函数快速创建工具。
    """
    
    def __init__(self, name: str, description: str,
                 func: Callable, parameters: Optional[List[ToolParameter]] = None):
        self._name = name
        self._description = description
        self._func = func
        self._parameters = parameters or []
    
    def name(self) -> str:
        return self._name
    
    def description(self) -> str:
        return self._description
    
    def parameters(self) -> List[ToolParameter]:
        return self._parameters
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            result = self._func(**kwargs)
            return ToolResult.success(data=result)
        except Exception as e:
            return ToolResult.error(
                message=str(e),
                code=ToolErrorCode.INTERNAL_ERROR,
                metadata={"exception": type(e).__name__}
            )


class CLITool(Tool):
    """
    CLI 工具包装器 - Agent-Native CLI 标准
    
    将任意命令行工具包装成符合 Agent-Native CLI 标准的接口：
    - 支持 --json 输出结构化结果
    - 错误码标准化（exit code 映射到 ToolErrorCode）
    - 支持 --desc 输出能力描述
    """
    
    def __init__(self, command: str, tool_name: str, description: str,
                 timeout: int = 30, params: Optional[List[ToolParameter]] = None):
        self.command = command
        self._name = tool_name
        self._description = description
        self.timeout = timeout
        self._parameters = params or []
    
    def name(self) -> str:
        return self._name
    
    def description(self) -> str:
        return self._description
    
    def parameters(self) -> List[ToolParameter]:
        return self._parameters
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行 CLI 命令
        
        自动添加 --json 标志获取结构化输出。
        """
        # 构建命令
        cmd_parts = [self.command]
        
        # 添加参数
        for key, value in kwargs.items():
            if key == "_json":  # 内部参数，跳过
                continue
            cmd_parts.append(f"--{key}")
            if isinstance(value, list):
                cmd_parts.extend(str(v) for v in value)
            else:
                cmd_parts.append(str(value))
        
        # 强制 JSON 输出（Agent-Native CLI 标准）
        cmd_parts.append("--json")
        
        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # 解析 JSON 输出
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    return ToolResult.success(
                        data=data,
                        metadata={"exit_code": 0, "command": self.command}
                    )
                except json.JSONDecodeError:
                    # 如果不是 JSON，返回原始文本
                    return ToolResult.success(
                        data={"output": result.stdout},
                        metadata={"format": "text", "exit_code": 0}
                    )
            else:
                # 错误码映射
                error_code = self._map_exit_code(result.returncode)
                return ToolResult.error(
                    message=result.stderr or f"Command failed with exit code {result.returncode}",
                    code=error_code,
                    metadata={"exit_code": result.returncode, "command": self.command}
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult.error(
                message=f"Command timeout after {self.timeout} seconds",
                code=ToolErrorCode.TIMEOUT,
                metadata={"timeout": True}
            )
        except Exception as e:
            return ToolResult.error(
                message=str(e),
                code=ToolErrorCode.INTERNAL_ERROR,
                metadata={"exception": type(e).__name__}
            )
    
    def _map_exit_code(self, exit_code: int) -> ToolErrorCode:
        """将 exit code 映射到 ToolErrorCode"""
        mapping = {
            1: ToolErrorCode.INTERNAL_ERROR,
            2: ToolErrorCode.BAD_REQUEST,      # 误用命令
            126: ToolErrorCode.FORBIDDEN,      # 命令不可执行
            127: ToolErrorCode.NOT_FOUND,      # 命令未找到
            130: ToolErrorCode.TIMEOUT,        # Ctrl+C 终止
            137: ToolErrorCode.SERVICE_UNAVAILABLE,  # SIGKILL
        }
        return mapping.get(exit_code, ToolErrorCode.INTERNAL_ERROR)


class AgentNativeCLITool(CLITool):
    """
    Agent-Native CLI 工具
    
    完全遵循 Agent-Native CLI 标准的工具：
    - 必须支持 --json 输出
    - 必须支持 --desc 输出能力描述
    - 错误码遵循 ToolErrorCode 语义
    """
    
    def get_capabilities(self) -> Dict[str, Any]:
        """通过执行 --desc 获取能力描述"""
        try:
            result = subprocess.run(
                [self.command, "--desc"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        
        # 回退到默认实现
        return super().get_capabilities()


class ToolRegistry:
    """
    工具注册表
    
    管理所有可用工具，支持：
    - 工具注册和发现
    - CLI 工具自动发现
    - 工具搜索和过滤
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.categories: Dict[str, List[str]] = defaultdict(list)
    
    def register(self, tool: Tool, category: str = "general"):
        """注册工具"""
        self.tools[tool.name()] = tool
        self.categories[category].append(tool.name())
        logger = __import__('logging').getLogger(__name__)
        logger.debug(f"Registered tool: {tool.name()} (category: {category})")
    
    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有工具"""
        if category:
            tool_names = self.categories.get(category, [])
        else:
            tool_names = self.tools.keys()
        
        return [
            self.tools[name].get_capabilities()
            for name in tool_names
            if name in self.tools
        ]
    
    def auto_discover_cli_tools(self):
        """
        自动发现系统 CLI 工具
        
        发现并注册常见的 Unix CLI 工具。
        """
        # 常见工具列表（名称，描述，参数）
        common_tools = [
            ('grep', 'Search text using patterns', [
                ToolParameter('pattern', 'string', 'Search pattern', required=True),
                ToolParameter('file', 'string', 'File to search', required=True),
            ]),
            ('find', 'Find files and directories', [
                ToolParameter('path', 'string', 'Starting path', required=True),
                ToolParameter('name', 'string', 'File name pattern'),
            ]),
            ('wc', 'Count lines, words, or bytes', [
                ToolParameter('file', 'string', 'File to count', required=True),
                ToolParameter('lines', 'boolean', 'Count lines only'),
            ]),
            ('head', 'Output first part of files', [
                ToolParameter('file', 'string', 'File to read', required=True),
                ToolParameter('n', 'integer', 'Number of lines'),
            ]),
            ('tail', 'Output last part of files', [
                ToolParameter('file', 'string', 'File to read', required=True),
                ToolParameter('n', 'integer', 'Number of lines'),
            ]),
            ('cat', 'Concatenate and display files', [
                ToolParameter('file', 'string', 'File to display', required=True),
            ]),
            ('ls', 'List directory contents', [
                ToolParameter('path', 'string', 'Directory path'),
                ToolParameter('la', 'boolean', 'Show all files including hidden'),
            ]),
            ('curl', 'Transfer data from URLs', [
                ToolParameter('url', 'string', 'URL to fetch', required=True),
                ToolParameter('method', 'string', 'HTTP method'),
            ]),
            ('jq', 'Process JSON data', [
                ToolParameter('filter', 'string', 'JQ filter', required=True),
                ToolParameter('file', 'string', 'JSON file'),
            ]),
        ]
        
        for cmd, desc, params in common_tools:
            if self._check_command_exists(cmd):
                self.register(CLITool(cmd, cmd, desc, params=params), category="cli")
    
    def _check_command_exists(self, command: str) -> bool:
        """检查命令是否存在"""
        try:
            subprocess.run(
                [command, "--version"],
                capture_output=True,
                timeout=1
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def search_tools(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索工具"""
        results = []
        for name, tool in self.tools.items():
            if keyword.lower() in name.lower() or keyword.lower() in tool.description().lower():
                results.append(tool.get_capabilities())
        return results
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 JSON Schema（用于 LLM）"""
        return [tool.get_schema() for tool in self.tools.values()]


# 导入 logging
import logging
logger = logging.getLogger(__name__)
