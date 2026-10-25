# -*- coding: utf-8 -*-
"""
Built-in Tools - 内置工具

常用的基础工具实现
"""

import os
import json
import math
import logging
import sys
import ipaddress
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .base import Tool, ToolParameter


logger = logging.getLogger(__name__)


class PathEscapesWorkspaceError(Exception):
    """路径解析后逃出授权根目录"""


def _resolve_within_roots(filepath: str,
                          allowed_roots: List[str]) -> Path:
    """
    将 filepath 解析为绝对路径，并验证它位于某个授权根目录内。

    安全语义：
    - 相对路径按"工作区根目录"解析（root / filepath），而非进程 cwd——
      工具被授予的根即它的世界
    - Path.resolve() 展开 ``..`` 与 symlink，再 relative_to 校验，
      因此 ``../``、绝对路径穿越、symlink escape 一律拒绝
    - 根目录自身也 resolve 后比较，避免根目录本身是 symlink 时被绕过

    Raises:
        PathEscapesWorkspaceError: 路径不在任何授权根内
    """
    candidate = Path(filepath)
    if not candidate.is_absolute():
        # 相对路径：依次尝试各授权根；最后兼容 cwd
        candidates = [Path(root) / candidate for root in allowed_roots]
        candidates.append(Path.cwd() / candidate)
    else:
        candidates = [candidate]

    for c in candidates:
        resolved = c.resolve()
        for root in allowed_roots:
            root_resolved = Path(root).resolve()
            try:
                resolved.relative_to(root_resolved)
                return resolved
            except ValueError:
                continue
    raise PathEscapesWorkspaceError(
        f"Path {filepath!r} resolves outside allowed roots {allowed_roots}"
    )


def _default_roots(allowed_roots: Optional[List[str]]) -> List[str]:
    """未显式授权时，默认工作区 = 当前工作目录"""
    return allowed_roots if allowed_roots else [os.getcwd()]


class CalculatorTool(Tool):
    """计算器工具"""
    
    def name(self) -> str:
        return "calculator"
    
    def description(self) -> str:
        return "Evaluate mathematical expressions safely"
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="Mathematical expression to evaluate (e.g., '2 + 2', 'sin(pi/4)')",
                required=True
            )
        ]
    
    def execute(self, expression: str, **kwargs) -> Dict[str, Any]:
        """安全地计算数学表达式"""
        try:
            # 安全评估：只允许数学运算
            allowed_names = {
                "abs": abs,
                "max": max,
                "min": min,
                "sum": sum,
                "pow": pow,
                "round": round,
                "math": math,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "sqrt": math.sqrt,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
            }
            
            # 编译表达式
            code = compile(expression, "<string>", "eval")
            
            # 检查只允许安全的操作
            for name in code.co_names:
                if name not in allowed_names:
                    return {
                        "success": False,
                        "data": None,
                        "error": f"Disallowed name: {name}",
                        "metadata": {}
                    }
            
            result = eval(code, {"__builtins__": {}}, allowed_names)
            
            return {
                "success": True,
                "data": result,
                "error": None,
                "metadata": {"expression": expression}
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "metadata": {"expression": expression}
            }


class SearchTool(Tool):
    """搜索工具（模拟）"""
    
    def name(self) -> str:
        return "search"
    
    def description(self) -> str:
        return "Search for information (mock implementation)"
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of results",
                required=False,
                default=5
            )
        ]
    
    def execute(self, query: str, limit: int = 5, **kwargs) -> Dict[str, Any]:
        """模拟搜索"""
        # 这里应该集成真实的搜索 API
        # 例如：Google Custom Search, Bing API, SerpAPI 等
        
        mock_results = [
            {
                "title": f"Result {i+1} for: {query}",
                "snippet": f"This is a mock search result snippet for query '{query}'...",
                "url": f"https://example.com/result/{i+1}"
            }
            for i in range(min(limit, 5))
        ]
        
        return {
            "success": True,
            "data": {
                "query": query,
                "results": mock_results,
                "total_results": len(mock_results)
            },
            "error": None,
            "metadata": {"source": "mock"}
        }


class FileReadTool(Tool):
    """文件读取工具（workspace 根约束：只读授权根目录内的文件）"""
    
    def __init__(self, allowed_roots: Optional[List[str]] = None):
        # 默认工作区 = 当前工作目录；显式授权根由 Kernel/策略提供
        self.allowed_roots = _default_roots(allowed_roots)
    
    def name(self) -> str:
        return "read_file"
    
    def description(self) -> str:
        return "Read contents of a file (restricted to the workspace root)"
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="filepath",
                type="string",
                description="Path to the file to read (must resolve inside the workspace root)",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of characters to read",
                required=False,
                default=10000
            )
        ]
    
    def execute(self, filepath: str, limit: int = 10000, **kwargs) -> Dict[str, Any]:
        """读取文件内容（拒绝逃逸工作区的路径）"""
        try:
            # 安全检查：解析后必须位于授权根内（防 ../ 与 symlink escape）
            safe_path = _resolve_within_roots(filepath, self.allowed_roots)
            
            if not safe_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"File not found: {safe_path}",
                    "metadata": {}
                }
            
            if not safe_path.is_file():
                return {
                    "success": False,
                    "data": None,
                    "error": f"Not a file: {safe_path}",
                    "metadata": {}
                }
            
            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read(limit)
            
            # 检测是否被截断
            truncated = len(content) >= limit
            
            return {
                "success": True,
                "data": content,
                "error": None,
                "metadata": {
                    "filepath": str(safe_path),
                    "size": safe_path.stat().st_size,
                    "truncated": truncated
                }
            }
            
        except PathEscapesWorkspaceError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Access denied: {e}",
                "metadata": {"filepath": filepath, "denied": True}
            }
        except UnicodeDecodeError:
            return {
                "success": False,
                "data": None,
                "error": "File appears to be binary",
                "metadata": {"filepath": filepath}
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "metadata": {"filepath": filepath}
            }


class FileWriteTool(Tool):
    """文件写入工具（workspace 根约束：只写授权根目录内的路径）"""
    
    def __init__(self, allowed_roots: Optional[List[str]] = None):
        # 默认工作区 = 当前工作目录；显式授权根由 Kernel/策略提供
        self.allowed_roots = _default_roots(allowed_roots)
    
    def name(self) -> str:
        return "write_file"
    
    def description(self) -> str:
        return "Write content to a file (restricted to the workspace root)"
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="filepath",
                type="string",
                description="Path to the file to write (must resolve inside the workspace root)",
                required=True
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Content to write",
                required=True
            ),
            ToolParameter(
                name="append",
                type="boolean",
                description="Append to file instead of overwriting",
                required=False,
                default=False
            )
        ]
    
    def execute(self, filepath: str, content: str, append: bool = False, 
                **kwargs) -> Dict[str, Any]:
        """写入文件（拒绝逃逸工作区的路径）"""
        try:
            # 安全检查：解析后必须位于授权根内（防 ../ 与 symlink escape）
            safe_path = _resolve_within_roots(filepath, self.allowed_roots)
            
            # 确保目录存在
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'a' if append else 'w'
            with open(safe_path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "data": f"Written {len(content)} characters to {safe_path}",
                "error": None,
                "metadata": {
                    "filepath": str(safe_path),
                    "bytes_written": len(content.encode('utf-8')),
                    "append": append
                }
            }
            
        except PathEscapesWorkspaceError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Access denied: {e}",
                "metadata": {"filepath": filepath, "denied": True}
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "metadata": {"filepath": filepath}
            }


class PythonExecuteTool(Tool):
    """Python 代码执行工具

    安全语义（审计 P0-01）：
    - 默认 fail closed：未显式允许宿主执行时，返回结构化
      ``isolation_unavailable`` 错误，绝不在宿主静默执行
    - 显式 opt-in（allow_host_execution=True）时才走子进程，
      且使用 argv（无 shell）、当前解释器、工作区内 cwd、超时强杀
    """
    
    def __init__(self, allow_host_execution: bool = False,
                 allowed_roots: Optional[List[str]] = None):
        self.allow_host_execution = allow_host_execution
        self.allowed_roots = _default_roots(allowed_roots)
    
    def name(self) -> str:
        return "execute_python"
    
    def description(self) -> str:
        return ("Execute Python code. Fails closed with isolation_unavailable "
                "unless host execution is explicitly enabled (sandbox required).")
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="Python code to execute",
                required=True
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="Execution timeout in seconds",
                required=False,
                default=10
            )
        ]
    
    def execute(self, code: str, timeout: int = 10, **kwargs) -> Dict[str, Any]:
        """执行 Python 代码（默认拒绝宿主执行）"""
        import subprocess
        import tempfile
        
        # Fail closed：没有隔离环境时不在宿主执行任意代码
        if not self.allow_host_execution:
            return {
                "success": False,
                "data": None,
                "error": ("isolation_unavailable: no sandbox runtime configured; "
                          "refusing to execute arbitrary code on the host. "
                          "Pass allow_host_execution=True explicitly to override."),
                "metadata": {"isolation_unavailable": True}
            }
        
        temp_file = None
        try:
            # 创建临时文件（放在工作区内，避免 /tmp 争用）
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False,
                dir=self.allowed_roots[0]
            ) as f:
                f.write(code)
                temp_file = f.name
            
            # 在子进程中执行：argv 形式（无 shell）、当前解释器
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.allowed_roots[0]
            )
            
            return {
                "success": result.returncode == 0,
                "data": result.stdout if result.returncode == 0 else None,
                "error": result.stderr if result.returncode != 0 else None,
                "metadata": {
                    "exit_code": result.returncode,
                    "isolated": False,
                    "note": "host execution explicitly enabled by caller"
                }
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "data": None,
                "error": f"Execution timed out after {timeout} seconds",
                "metadata": {"timeout": True}
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "metadata": {}
            }
        finally:
            if temp_file:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass


class WebFetchTool(Tool):
    """网页抓取工具（带 SSRF 防护）"""
    
    # 显式阻断的网段（在常规私网判定之外）
    BLOCKED_NETWORKS = [
        ipaddress.ip_network("169.254.0.0/16"),   # 链路本地 / 云元数据（169.254.169.254）
        ipaddress.ip_network("100.64.0.0/10"),    # CGNAT
        ipaddress.ip_network("192.0.0.0/24"),     # IETF 协议分配
        ipaddress.ip_network("::1/128"),          # IPv6 环回
        ipaddress.ip_network("fc00::/7"),         # IPv6 ULA
        ipaddress.ip_network("fe80::/10"),        # IPv6 链路本地
    ]
    
    def name(self) -> str:
        return "fetch_url"
    
    def description(self) -> str:
        return "Fetch content from a URL (public http/https only; private/metadata addresses blocked)"
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="url",
                type="string",
                description="URL to fetch (http/https, public hosts only)",
                required=True
            ),
            ToolParameter(
                name="method",
                type="string",
                description="HTTP method",
                required=False,
                default="GET",
                enum=["GET", "POST", "PUT", "DELETE"]
            ),
            ToolParameter(
                name="headers",
                type="object",
                description="HTTP headers",
                required=False
            ),
            ToolParameter(
                name="data",
                type="string",
                description="Request body data",
                required=False
            )
        ]
    
    def _is_blocked_ip(self, ip_str: str) -> bool:
        """判断 IP 是否落在阻断网段（私网/环回/链路本地/元数据）"""
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return True  # 无法解析的一律按阻断处理
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
        for net in self.BLOCKED_NETWORKS:
            if ip.version == net.version and ip in net:
                return True
        return False
    
    def _validate_url(self, url: str) -> Optional[str]:
        """校验 URL  scheme 与目标主机；返回拒绝原因或 None"""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return f"Blocked scheme: {parsed.scheme!r} (only http/https allowed)"
        hostname = parsed.hostname
        if not hostname:
            return "URL has no hostname"
        # DNS 解析后逐一检查（防 DNS 重绑定到一个私网 IP）
        import socket
        try:
            infos = socket.getaddrinfo(hostname, parsed.port or 80, proto=socket.IPPROTO_TCP)
        except Exception as e:
            return f"DNS resolution failed for {hostname}: {e}"
        for info in infos:
            ip_str = info[4][0]
            if self._is_blocked_ip(ip_str):
                return f"Blocked target: {hostname} resolves to {ip_str} (private/metadata address)"
        return None
    
    def execute(self, url: str, method: str = "GET",
                headers: Optional[Dict] = None,
                data: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """获取 URL 内容（阻断私网/元数据端点）"""
        try:
            import urllib.request
            import urllib.error
            
            denial = self._validate_url(url)
            if denial:
                return {
                    "success": False,
                    "data": None,
                    "error": f"SSRF protection: {denial}",
                    "metadata": {"url": url, "blocked": True}
                }
            
            req = urllib.request.Request(url, method=method)
            
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
            
            if data:
                req.data = data.encode('utf-8')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8', errors='ignore')
                
                return {
                    "success": True,
                    "data": {
                        "content": content[:50000],  # 限制返回大小
                        "status": response.status,
                        "headers": dict(response.headers)
                    },
                    "error": None,
                    "metadata": {
                        "url": url,
                        "method": method,
                        "content_length": len(content)
                    }
                }
                
        except urllib.error.HTTPError as e:
            return {
                "success": False,
                "data": None,
                "error": f"HTTP {e.code}: {e.reason}",
                "metadata": {"url": url, "status": e.code}
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "metadata": {"url": url}
            }


class JsonTool(Tool):
    """JSON 处理工具"""
    
    def name(self) -> str:
        return "json_tool"
    
    def description(self) -> str:
        return "Parse and format JSON data"
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="Action to perform",
                required=True,
                enum=["parse", "format", "extract"]
            ),
            ToolParameter(
                name="data",
                type="string",
                description="JSON string to process",
                required=True
            ),
            ToolParameter(
                name="path",
                type="string",
                description="JSON path for extract action (e.g., 'key.nested_key')",
                required=False
            )
        ]
    
    def execute(self, action: str, data: str, path: Optional[str] = None, 
                **kwargs) -> Dict[str, Any]:
        """处理 JSON 数据"""
        try:
            parsed = json.loads(data)
            
            if action == "parse":
                return {
                    "success": True,
                    "data": parsed,
                    "error": None,
                    "metadata": {"type": type(parsed).__name__}
                }
            
            elif action == "format":
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                return {
                    "success": True,
                    "data": formatted,
                    "error": None,
                    "metadata": {}
                }
            
            elif action == "extract":
                if not path:
                    return {
                        "success": False,
                        "data": None,
                        "error": "Path required for extract action",
                        "metadata": {}
                    }
                
                keys = path.split('.')
                result = parsed
                for key in keys:
                    if isinstance(result, dict) and key in result:
                        result = result[key]
                    else:
                        return {
                            "success": False,
                            "data": None,
                            "error": f"Path not found: {path}",
                            "metadata": {}
                        }
                
                return {
                    "success": True,
                    "data": result,
                    "error": None,
                    "metadata": {"path": path}
                }
            
            else:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Unknown action: {action}",
                    "metadata": {}
                }
                
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Invalid JSON: {e}",
                "metadata": {}
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "metadata": {}
            }
