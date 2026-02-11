# -*- coding: utf-8 -*-
"""Tool Market - 工具市场

动态工具发现、加载和管理系统。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import json
import importlib
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """工具信息"""
    tool_id: str
    name: str
    version: str
    description: str
    author: str
    category: str
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    installed_at: Optional[datetime] = None
    size_bytes: int = 0


class ToolMarket:
    """工具市场"""
    
    def __init__(
        self,
        cache_dir: str = "~/.cache/agent-os-kernel/tools"
    ):
        """
        初始化工具市场
        """
        self._cache_dir = Path(cache_dir).expanduser()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._registry: Dict[str, ToolInfo] = {}
        self._load_functions: Dict[str, Callable] = {}
        logger.info(f"ToolMarket initialized: cache={self._cache_dir}")
    
    async def initialize(self):
        """初始化"""
        await self._load_local_registry()
    
    async def search(
        self,
        query: str = "",
        category: str = None,
        limit: int = 20
    ) -> List[ToolInfo]:
        """搜索工具"""
        results = []
        for tool in self._registry.values():
            if query and query.lower() not in tool.name.lower():
                continue
            if category and tool.category != category:
                continue
            results.append(tool)
            if len(results) >= limit:
                break
        return results
    
    async def install(self, tool_id: str, version: str = "latest") -> bool:
        """安装工具"""
        tool = self._registry.get(tool_id)
        if not tool:
            return False
        tool.installed_at = datetime.now(timezone.utc)
        logger.info(f"Installed tool: {tool_id}")
        return True
    
    async def uninstall(self, tool_id: str) -> bool:
        """卸载工具"""
        if tool_id in self._registry:
            self._registry.pop(tool_id)
            self._load_functions.pop(tool_id, None)
            logger.info(f"Uninstalled tool: {tool_id}")
            return True
        return False
    
    def register_loader(self, tool_id: str, loader: Callable):
        """注册自定义加载器"""
        self._load_functions[tool_id] = loader
    
    async def _load_local_registry(self):
        """加载本地注册表"""
        registry_file = self._cache_dir / "registry.json"
        if registry_file.exists():
            with open(registry_file) as f:
                data = json.load(f)
                for tool_data in data.get("tools", []):
                    self._registry[tool_data["tool_id"]] = ToolInfo(**tool_data)
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_tools": len(self._registry),
            "installed_tools": sum(1 for t in self._registry.values() if t.installed_at)
        }


def get_tool_market() -> ToolMarket:
    """获取默认工具市场"""
    return ToolMarket()
