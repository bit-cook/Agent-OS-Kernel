# -*- coding: utf-8 -*-
"""
Tool Registry - 工具注册表

管理所有可用工具的注册和发现
"""

import logging
from typing import Dict, List, Optional, Any

from .base import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册表

    管理工具的生命周期和访问
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.categories: Dict[str, List[str]] = {}
        logger.debug("ToolRegistry initialized")

    def register(self, tool: Tool, category: str = "general"):
        """
        注册工具

        Args:
            tool: 工具实例
            category: 工具类别
        """
        name = tool.name()

        if name in self.tools:
            logger.warning(f"Tool '{name}' already registered, overwriting")

        self.tools[name] = tool

        if category not in self.categories:
            self.categories[category] = []
        if name not in self.categories[category]:
            self.categories[category].append(name)

        logger.info(f"Registered tool: {name} (category: {category})")

    def unregister(self, name: str):
        """注销工具"""
        if name in self.tools:
            del self.tools[name]

            # 从分类中移除
            for category, tools in self.categories.items():
                if name in tools:
                    tools.remove(name)

            logger.info(f"Unregistered tool: {name}")

    def get(self, name: str) -> Optional[Tool]:
        """
        获取工具

        Args:
            name: 工具名称

        Returns:
            工具实例，如果不存在则返回 None
        """
        return self.tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有工具

        Args:
            category: 工具类别过滤，None 表示所有

        Returns:
            工具信息列表
        """
        if category:
            tool_names = self.categories.get(category, [])
        else:
            tool_names = list(self.tools.keys())

        return [
            {
                "name": name,
                "description": self.tools[name].description(),
                "category": self._get_category(name),
            }
            for name in tool_names
            if name in self.tools
        ]

    def get_schemas(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有工具的 JSON Schema

        Args:
            category: 工具类别过滤

        Returns:
            Schema 列表
        """
        if category:
            tool_names = self.categories.get(category, [])
        else:
            tool_names = list(self.tools.keys())

        return [self.tools[name].get_schema() for name in tool_names if name in self.tools]

    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        执行工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            执行结果
        """
        tool = self.get(name)

        if not tool:
            return {
                "success": False,
                "data": None,
                "error": f"Tool '{name}' not found",
                "metadata": {},
            }

        # 验证参数
        valid, error = tool.validate_params(**kwargs)
        if not valid:
            return {"success": False, "data": None, "error": error, "metadata": {}}

        # 执行工具
        try:
            result = tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.exception(f"Error executing tool '{name}'")
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "metadata": {"exception": type(e).__name__},
            }

    def auto_discover_cli_tools(self):
        """
        自动发现系统 CLI 工具

        检测常见的 CLI 工具并注册
        """
        from .base import CLITool

        common_tools = [
            ("grep", "Search text using patterns", "GrepTool"),
            ("find", "Find files and directories", "FindTool"),
            ("cat", "Display file contents", "CatTool"),
            ("ls", "List directory contents", "LsTool"),
            ("pwd", "Print working directory", "PwdTool"),
            ("head", "Output first part of files", "HeadTool"),
            ("tail", "Output last part of files", "TailTool"),
            ("wc", "Word, line, character count", "WcTool"),
            ("curl", "Transfer data from URLs", "CurlTool"),
        ]

        registered = 0
        for cmd, desc, tool_name in common_tools:
            try:
                import subprocess

                result = subprocess.run([cmd, "--version"], capture_output=True, timeout=1)
                if result.returncode in (0, 1, 2):  # 有些工具返回非0但也存在
                    self.register(CLITool(cmd, tool_name, desc), category="system")
                    registered += 1
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        logger.info(f"Auto-discovered {registered} CLI tools")

    def _get_category(self, tool_name: str) -> str:
        """获取工具的类别"""
        for category, tools in self.categories.items():
            if tool_name in tools:
                return category
        return "unknown"

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_tools": len(self.tools),
            "categories": {cat: len(tools) for cat, tools in self.categories.items()},
        }
