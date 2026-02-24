# -*- coding: utf-8 -*-
"""
初始化管理器模块 - Initialization Manager

提供系统组件的初始化、依赖管理、初始化顺序控制、健康检查和启动/关闭生命周期管理。

功能:
- 组件注册与初始化 (Component Registration & Initialization)
- 依赖管理 (Dependency Management)
- 初始化顺序控制 (Initialization Order Control)
- 健康检查 (Health Check)
- 启动/关闭生命周期管理 (Startup/Shutdown Lifecycle Management)
"""

import asyncio
import logging
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from functools import partial


logger = logging.getLogger(__name__)


class InitState(Enum):
    """初始化状态枚举"""
    NOT_INITIALIZED = auto()
    DEPENDENCIES_WAITING = auto()
    INITIALIZING = auto()
    INITIALIZED = auto()
    HEALTHY = auto()
    UNHEALTHY = auto()
    SHUTTING_DOWN = auto()
    SHUTDOWN = auto()
    FAILED = auto()


class InitError(Exception):
    """初始化错误异常"""
    
    def __init__(self, message: str, component: str, state: InitState, cause: Optional[Exception] = None):
        super().__init__(message)
        self.component = component
        self.state = state
        self.cause = cause


class DependencyCycleError(InitError):
    """依赖循环错误"""
    
    def __init__(self, cycle: List[str]):
        message = f"Dependency cycle detected: {' -> '.join(cycle)}"
        super().__init__(message, "system", InitState.DEPENDENCIES_WAITING)
        self.cycle = cycle


class ComponentNotFoundError(InitError):
    """组件未找到错误"""
    
    def __init__(self, component: str):
        message = f"Component '{component}' not found"
        super().__init__(message, component, InitState.NOT_INITIALIZED)
        self.component = component


@dataclass
class ComponentInfo:
    """组件信息"""
    name: str
    init_func: Callable[..., Any]
    shutdown_func: Optional[Callable[..., Any]] = None
    health_check_func: Optional[Callable[..., bool]] = None
    dependencies: List[str] = field(default_factory=list)
    state: InitState = InitState.NOT_INITIALIZED
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, ComponentInfo):
            return self.name == other.name
        return False


class InitializationManager:
    """初始化管理器主类"""
    
    def __init__(self):
        self._components: Dict[str, ComponentInfo] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._initialized_order: List[str] = []
        self._running = False
        self._lock = asyncio.Lock()
    
    def register_component(
        self,
        name: str,
        init_func: Callable[..., Any],
        shutdown_func: Optional[Callable[..., Any]] = None,
        health_check_func: Optional[Callable[..., bool]] = None,
        dependencies: Optional[List[str]] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ComponentInfo:
        """
        注册组件
        
        Args:
            name: 组件名称
            init_func: 初始化函数
            shutdown_func: 关闭函数（可选）
            health_check_func: 健康检查函数（可选）
            dependencies: 依赖组件名称列表（可选）
            priority: 初始化优先级（数值越大优先级越高）
            metadata: 元数据（可选）
            
        Returns:
            ComponentInfo: 组件信息对象
            
        Raises:
            ValueError: 组件名称已存在
        """
        if name in self._components:
            raise ValueError(f"Component '{name}' already registered")
        
        component = ComponentInfo(
            name=name,
            init_func=init_func,
            shutdown_func=shutdown_func,
            health_check_func=health_check_func,
            dependencies=dependencies or [],
            priority=priority,
            metadata=metadata or {}
        )
        
        self._components[name] = component
        self._dependency_graph[name] = set()
        
        # 更新依赖图
        for dep in component.dependencies:
            if dep not in self._components:
                # 延迟依赖检查
                self._dependency_graph[name].add(dep)
            else:
                self._dependency_graph[name].add(dep)
        
        logger.info(f"Component '{name}' registered with priority {priority}")
        return component
    
    def unregister_component(self, name: str) -> bool:
        """
        注销组件
        
        Args:
            name: 组件名称
            
        Returns:
            bool: 是否成功注销
        """
        if name not in self._components:
            return False
        
        # 从依赖图中移除
        for comp in self._dependency_graph.values():
            comp.discard(name)
        
        del self._components[name]
        del self._dependency_graph[name]
        
        # 从已初始化列表中移除
        if name in self._initialized_order:
            self._initialized_order.remove(name)
        
        logger.info(f"Component '{name}' unregistered")
        return True
    
    def get_component(self, name: str) -> Optional[ComponentInfo]:
        """
        获取组件信息
        
        Args:
            name: 组件名称
            
        Returns:
            ComponentInfo: 组件信息对象，不存在返回None
        """
        return self._components.get(name)
    
    def get_all_components(self) -> List[ComponentInfo]:
        """
        获取所有组件信息
        
        Returns:
            List[ComponentInfo]: 组件信息列表
        """
        return list(self._components.values())
    
    def _detect_dependency_cycle(self) -> Optional[List[str]]:
        """
        检测依赖循环
        
        Returns:
            Optional[List[str]]: 循环路径，不存在返回None
        """
        def dfs(node: str, path: List[str], visited: Set[str]) -> Optional[List[str]]:
            if node in path:
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            path.append(node)
            
            for dep in self._dependency_graph.get(node, set()):
                result = dfs(dep, path.copy(), visited)
                if result:
                    return result
            
            return None
        
        for component in self._components:
            result = dfs(component, [], set())
            if result:
                return result
        
        return None
    
    def _topological_sort(self) -> List[str]:
        """
        拓扑排序获取初始化顺序
        
        Returns:
            List[str]: 按依赖顺序排序的组件名称列表
        """
        # 检测循环
        cycle = self._detect_dependency_cycle()
        if cycle:
            raise DependencyCycleError(cycle)
        
        # Kahn算法拓扑排序
        in_degree: Dict[str, int] = {name: 0 for name in self._components}
        
        for name, deps in self._dependency_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # 按优先级排序初始化
        queue = asyncio.Queue()
        for name, degree in in_degree.items():
            if degree == 0:
                queue.put_nowait(name)
        
        result = []
        while not queue.empty():
            node = queue.get_nowait()
            result.append(node)
            
            # 按优先级找出所有未处理的节点
            for name, deps in self._dependency_graph.items():
                if node in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.put_nowait(name)
        
        # 按优先级重新排序
        priority_sorted = sorted(result, key=lambda x: self._components[x].priority, reverse=True)
        
        return priority_sorted
    
    async def initialize_all(self) -> None:
        """
        初始化所有组件
        
        Raises:
            DependencyCycleError: 依赖循环
            InitError: 初始化失败
        """
        if self._running:
            raise RuntimeError("Initialization manager is already running")
        
        self._running = True
        self._initialized_order = []
        
        # 按依赖顺序排序
        try:
            init_order = self._topological_sort()
        except DependencyCycleError as e:
            self._running = False
            raise
        
        logger.info(f"Initializing components in order: {init_order}")
        
        for component_name in init_order:
            component = self._components[component_name]
            component.state = InitState.DEPENDENCIES_WAITING
            
            # 等待依赖组件初始化
            for dep in component.dependencies:
                if dep not in self._components:
                    continue
                dep_comp = self._components[dep]
                if dep_comp.state not in (InitState.INITIALIZED, InitState.HEALTHY):
                    logger.debug(f"Waiting for dependency '{dep}' of '{component_name}'")
            
            try:
                component.state = InitState.INITIALIZING
                logger.info(f"Initializing component '{component_name}'")
                
                # 调用初始化函数
                if asyncio.iscoroutinefunction(component.init_func):
                    await component.init_func()
                else:
                    component.init_func()
                
                component.state = InitState.INITIALIZED
                self._initialized_order.append(component_name)
                logger.info(f"Component '{component_name}' initialized successfully")
                
            except Exception as e:
                component.state = InitState.FAILED
                component.error = e
                self._running = False
                raise InitError(
                    f"Failed to initialize component '{component_name}'",
                    component_name,
                    InitState.INITIALIZING,
                    cause=e
                )
        
        logger.info("All components initialized successfully")
    
    async def health_check(self, component_name: Optional[str] = None) -> Dict[str, bool]:
        """
        执行健康检查
        
        Args:
            component_name: 指定组件名称，为None检查所有
            
        Returns:
            Dict[str, bool]: 组件名称到健康状态的映射
        """
        results = {}
        
        if component_name:
            if component_name not in self._components:
                raise ComponentNotFoundError(component_name)
            
            comp = self._components[component_name]
            if comp.health_check_func is None:
                results[component_name] = comp.state == InitState.HEALTHY
            else:
                try:
                    if asyncio.iscoroutinefunction(comp.health_check_func):
                        results[component_name] = await comp.health_check_func()
                    else:
                        results[component_name] = comp.health_check_func()
                except Exception as e:
                    results[component_name] = False
                    logger.warning(f"Health check failed for '{component_name}': {e}")
        else:
            for name, comp in self._components.items():
                if comp.health_check_func is None:
                    results[name] = comp.state == InitState.HEALTHY
                else:
                    try:
                        if asyncio.iscoroutinefunction(comp.health_check_func):
                            results[name] = await comp.health_check_func()
                        else:
                            results[name] = comp.health_check_func()
                    except Exception as e:
                        results[name] = False
                        logger.warning(f"Health check failed for '{name}': {e}")
        
        return results
    
    async def shutdown(self) -> None:
        """
        关闭所有组件
        """
        if not self._running:
            return
        
        logger.info("Shutting down all components")
        
        # 按初始化顺序的逆序关闭
        for component_name in reversed(self._initialized_order):
            component = self._components[component_name]
            
            if component.state not in (InitState.INITIALIZED, InitState.HEALTHY):
                continue
            
            try:
                component.state = InitState.SHUTTING_DOWN
                logger.info(f"Shutting down component '{component_name}'")
                
                if component.shutdown_func is not None:
                    if asyncio.iscoroutinefunction(component.shutdown_func):
                        await component.shutdown_func()
                    else:
                        component.shutdown_func()
                
                component.state = InitState.SHUTDOWN
                logger.info(f"Component '{component_name}' shut down successfully")
                
            except Exception as e:
                component.state = InitState.FAILED
                component.error = e
                logger.error(f"Failed to shut down component '{component_name}': {e}")
        
        self._running = False
        self._initialized_order = []
        logger.info("All components shut down")
    
    def get_init_state(self, component_name: str) -> Optional[InitState]:
        """
        获取组件初始化状态
        
        Args:
            component_name: 组件名称
            
        Returns:
            InitState: 初始化状态，不存在返回None
        """
        comp = self._components.get(component_name)
        return comp.state if comp else None
    
    def get_init_order(self) -> List[str]:
        """
        获取初始化顺序
        
        Returns:
            List[str]: 组件名称列表
        """
        return list(self._initialized_order)
    
    def is_running(self) -> bool:
        """
        检查是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        return self._running
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """
        获取依赖图
        
        Returns:
            Dict[str, List[str]]: 组件名称到依赖列表的映射
        """
        return {name: list(deps) for name, deps in self._dependency_graph.items()}
    
    def reset(self) -> None:
        """重置初始化管理器"""
        self._components.clear()
        self._dependency_graph.clear()
        self._initialized_order.clear()
        self._running = False


def create_initialization_manager() -> InitializationManager:
    """
    创建初始化管理器
    
    Returns:
        InitializationManager: 初始化管理器实例
    """
    return InitializationManager()


# 便捷的组件注册装饰器
def component(
    name: Optional[str] = None,
    dependencies: Optional[List[str]] = None,
    priority: int = 0,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    组件装饰器
    
    Args:
        name: 组件名称，为None使用函数名
        dependencies: 依赖组件名称列表
        priority: 初始化优先级
        metadata: 元数据
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        component_name = name or func.__name__
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 延迟注册，实际注册由InitializationManager处理
            # 这里只是标记，用于后续查找
            return func(*args, **kwargs)
        
        wrapper._component_name = component_name
        wrapper._dependencies = dependencies or []
        wrapper._priority = priority
        wrapper._metadata = metadata or {}
        
        return wrapper
    return decorator


# 导入wraps用于装饰器
from functools import wraps
