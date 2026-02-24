# -*- coding: utf-8 -*-
"""
Health Checker Module - Agent-OS-Kernel 健康检查器模块

提供全面的系统和服务健康检查功能：
1. 服务健康检查 - 检查本地和远程服务的运行状态
2. 依赖检查 - 检查系统依赖项是否可用
3. 自定义检查 - 支持用户自定义健康检查函数
4. 健康报告 - 生成详细的健康状态报告
"""

import asyncio
import logging
import time
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """检查类型枚举"""
    SERVICE = "service"           # 服务检查
    DEPENDENCY = "dependency"     # 依赖检查
    CUSTOM = "custom"             # 自定义检查
    RESOURCE = "resource"        # 资源检查
    NETWORK = "network"           # 网络检查


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: HealthStatus
    check_type: CheckType
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    response_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_healthy(self) -> bool:
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    
    @property
    def is_critical(self) -> bool:
        return self.status == HealthStatus.UNHEALTHY


@dataclass
class ServiceCheckConfig:
    """服务检查配置"""
    name: str
    host: str
    port: int
    check_type: str = "tcp"  # tcp, http, ping
    path: str = "/"          # HTTP检查时的路径
    timeout_seconds: float = 5.0
    expected_status: int = 200  # HTTP期望状态码
    max_response_time_ms: float = 1000.0
    enabled: bool = True


@dataclass
class DependencyCheckConfig:
    """依赖检查配置"""
    name: str
    check_function: Optional[Callable[[], Tuple[bool, str]]] = None
    command: Optional[str] = None
    import_name: Optional[str] = None
    description: str = ""
    is_critical: bool = False
    enabled: bool = True


@dataclass
class CustomCheckConfig:
    """自定义检查配置"""
    name: str
    check_function: Callable[[], HealthCheckResult]
    description: str = ""
    check_type: CheckType = CheckType.CUSTOM
    enabled: bool = True


@dataclass
class HealthReport:
    """健康报告"""
    overall_status: HealthStatus
    check_results: List[HealthCheckResult]
    summary: Dict[str, int] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    
    def get_summary(self) -> Dict[str, int]:
        """获取检查结果摘要"""
        if not self.summary:
            self.summary = {
                "total": len(self.check_results),
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
                "unknown": 0,
            }
            for result in self.check_results:
                if result.status == HealthStatus.HEALTHY:
                    self.summary["healthy"] += 1
                elif result.status == HealthStatus.DEGRADED:
                    self.summary["degraded"] += 1
                elif result.status == HealthStatus.UNHEALTHY:
                    self.summary["unhealthy"] += 1
                else:
                    self.summary["unknown"] += 1
        return self.summary
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_status": self.overall_status.value,
            "summary": self.get_summary(),
            "check_results": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "check_type": r.check_type.value,
                    "message": r.message,
                    "details": r.details,
                    "response_time_ms": r.response_time_ms,
                    "timestamp": r.timestamp,
                }
                for r in self.check_results
            ],
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


class BaseHealthChecker(ABC):
    """健康检查器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._results: Dict[str, HealthCheckResult] = {}
    
    @abstractmethod
    def check(self) -> HealthCheckResult:
        """执行健康检查"""
        pass
    
    def get_last_result(self) -> Optional[HealthCheckResult]:
        """获取上次检查结果"""
        return self._results.get(self.name)


class ServiceHealthChecker(BaseHealthChecker):
    """服务健康检查器"""
    
    def __init__(self, config: ServiceCheckConfig):
        super().__init__(config.name)
        self.config = config
    
    def check(self) -> HealthCheckResult:
        """执行服务健康检查"""
        start_time = time.time()
        
        try:
            if self.config.check_type == "tcp":
                return self._check_tcp(start_time)
            elif self.config.check_type == "http":
                return self._check_http(start_time)
            elif self.config.check_type == "ping":
                return self._check_ping(start_time)
            else:
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.UNKNOWN,
                    check_type=CheckType.SERVICE,
                    message=f"Unknown check type: {self.config.check_type}",
                    response_time_ms=(time.time() - start_time) * 1000,
                )
        except Exception as e:
            logger.error(f"Service check failed: {e}")
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.SERVICE,
                message=f"Check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _check_tcp(self, start_time: float) -> HealthCheckResult:
        """TCP端口检查"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout_seconds)
            result = sock.connect_ex((self.config.host, self.config.port))
            sock.close()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if result == 0:
                if response_time_ms > self.config.max_response_time_ms:
                    return HealthCheckResult(
                        name=self.config.name,
                        status=HealthStatus.DEGRADED,
                        check_type=CheckType.SERVICE,
                        message=f"TCP connection successful but slow ({response_time_ms:.2f}ms)",
                        response_time_ms=response_time_ms,
                    )
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.HEALTHY,
                    check_type=CheckType.SERVICE,
                    message=f"TCP connection successful ({response_time_ms:.2f}ms)",
                    response_time_ms=response_time_ms,
                )
            else:
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.UNHEALTHY,
                    check_type=CheckType.SERVICE,
                    message=f"TCP connection failed (error code: {result})",
                    response_time_ms=response_time_ms,
                )
        except Exception as e:
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.SERVICE,
                message=f"TCP check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _check_http(self, start_time: float) -> HealthCheckResult:
        """HTTP健康检查"""
        try:
            import urllib.request
            import urllib.error
            
            url = f"http://{self.config.host}:{self.config.port}{self.config.path}"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                response_time_ms = (time.time() - start_time) * 1000
                status_code = response.status
                
                if status_code == self.config.expected_status:
                    return HealthCheckResult(
                        name=self.config.name,
                        status=HealthStatus.HEALTHY if response_time_ms < self.config.max_response_time_ms else HealthStatus.DEGRADED,
                        check_type=CheckType.SERVICE,
                        message=f"HTTP {status_code} - {response_time_ms:.2f}ms",
                        response_time_ms=response_time_ms,
                        details={"status_code": status_code},
                    )
                else:
                    return HealthCheckResult(
                        name=self.config.name,
                        status=HealthStatus.DEGRADED,
                        check_type=CheckType.SERVICE,
                        message=f"HTTP {status_code} (expected {self.config.expected_status})",
                        response_time_ms=response_time_ms,
                        details={"status_code": status_code},
                    )
        except urllib.error.HTTPError as e:
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.DEGRADED if e.code < 500 else HealthStatus.UNHEALTHY,
                check_type=CheckType.SERVICE,
                message=f"HTTP error: {e.code} {e.reason}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.SERVICE,
                message=f"HTTP check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _check_ping(self, start_time: float) -> HealthCheckResult:
        """Ping检查"""
        try:
            import subprocess
            
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(int(self.config.timeout_seconds)), self.config.host],
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds + 1,
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if result.returncode == 0:
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.HEALTHY if response_time_ms < self.config.max_response_time_ms else HealthStatus.DEGRADED,
                    check_type=CheckType.SERVICE,
                    message=f"Ping successful ({response_time_ms:.2f}ms)",
                    response_time_ms=response_time_ms,
                )
            else:
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.UNHEALTHY,
                    check_type=CheckType.SERVICE,
                    message=f"Ping failed",
                    response_time_ms=response_time_ms,
                )
        except Exception as e:
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.SERVICE,
                message=f"Ping check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )


class DependencyHealthChecker(BaseHealthChecker):
    """依赖健康检查器"""
    
    def __init__(self, config: DependencyCheckConfig):
        super().__init__(config.name)
        self.config = config
    
    def check(self) -> HealthCheckResult:
        """执行依赖健康检查"""
        start_time = time.time()
        
        try:
            if self.config.check_function:
                return self._check_function(start_time)
            elif self.config.command:
                return self._check_command(start_time)
            elif self.config.import_name:
                return self._check_import(start_time)
            else:
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.UNKNOWN,
                    check_type=CheckType.DEPENDENCY,
                    message="No check method configured",
                    response_time_ms=(time.time() - start_time) * 1000,
                )
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.DEPENDENCY,
                message=f"Check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _check_function(self, start_time: float) -> HealthCheckResult:
        """通过函数检查依赖"""
        try:
            success, message = self.config.check_function()
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.HEALTHY if success else HealthStatus.UNHEALTHY,
                check_type=CheckType.DEPENDENCY,
                message=message,
                response_time_ms=response_time_ms,
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.DEPENDENCY,
                message=f"Function check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _check_command(self, start_time: float) -> HealthCheckResult:
        """通过命令检查依赖"""
        try:
            import subprocess
            
            result = subprocess.run(
                self.config.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if result.returncode == 0:
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.HEALTHY,
                    check_type=CheckType.DEPENDENCY,
                    message=f"Command executed successfully",
                    response_time_ms=response_time_ms,
                )
            else:
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.UNHEALTHY,
                    check_type=CheckType.DEPENDENCY,
                    message=f"Command failed: {result.stderr or result.stdout}",
                    response_time_ms=response_time_ms,
                )
        except Exception as e:
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.DEPENDENCY,
                message=f"Command check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _check_import(self, start_time: float) -> HealthCheckResult:
        """通过导入检查依赖"""
        try:
            __import__(self.config.import_name)
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.HEALTHY,
                check_type=CheckType.DEPENDENCY,
                message=f"Module '{self.config.import_name}' is available",
                response_time_ms=response_time_ms,
            )
        except ImportError as e:
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.DEPENDENCY,
                message=f"Import failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=CheckType.DEPENDENCY,
                message=f"Import check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )


class CustomHealthChecker(BaseHealthChecker):
    """自定义健康检查器"""
    
    def __init__(self, config: CustomCheckConfig):
        super().__init__(config.name)
        self.config = config
    
    def check(self) -> HealthCheckResult:
        """执行自定义健康检查"""
        start_time = time.time()
        
        try:
            result = self.config.check_function()
            if isinstance(result, HealthCheckResult):
                result.response_time_ms = (time.time() - start_time) * 1000
                result.check_type = self.config.check_type
                return result
            else:
                return HealthCheckResult(
                    name=self.config.name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    check_type=self.config.check_type,
                    message="Custom check completed",
                    response_time_ms=(time.time() - start_time) * 1000,
                )
        except Exception as e:
            logger.error(f"Custom check failed: {e}")
            return HealthCheckResult(
                name=self.config.name,
                status=HealthStatus.UNHEALTHY,
                check_type=self.config.check_type,
                message=f"Custom check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )


class HealthChecker:
    """健康检查器管理器"""
    
    def __init__(self):
        self._service_checkers: Dict[str, ServiceHealthChecker] = {}
        self._dependency_checkers: Dict[str, DependencyHealthChecker] = {}
        self._custom_checkers: Dict[str, CustomHealthChecker] = {}
        self._results: Dict[str, HealthCheckResult] = {}
        self._last_report: Optional[HealthReport] = None
    
    def add_service_check(self, config: ServiceCheckConfig) -> None:
        """添加服务健康检查"""
        if config.enabled:
            self._service_checkers[config.name] = ServiceHealthChecker(config)
    
    def add_dependency_check(self, config: DependencyCheckConfig) -> None:
        """添加依赖健康检查"""
        if config.enabled:
            self._dependency_checkers[config.name] = DependencyHealthChecker(config)
    
    def add_custom_check(self, config: CustomCheckConfig) -> None:
        """添加自定义健康检查"""
        if config.enabled:
            self._custom_checkers[config.name] = CustomHealthChecker(config)
    
    def check_service(self, name: str) -> Optional[HealthCheckResult]:
        """执行指定服务的健康检查"""
        checker = self._service_checkers.get(name)
        if checker:
            result = checker.check()
            self._results[name] = result
            return result
        return None
    
    def check_dependency(self, name: str) -> Optional[HealthCheckResult]:
        """执行指定依赖的健康检查"""
        checker = self._dependency_checkers.get(name)
        if checker:
            result = checker.check()
            self._results[name] = result
            return result
        return None
    
    def check_custom(self, name: str) -> Optional[HealthCheckResult]:
        """执行指定自定义检查"""
        checker = self._custom_checkers.get(name)
        if checker:
            result = checker.check()
            self._results[name] = result
            return result
        return None
    
    def check_all(self) -> HealthReport:
        """执行所有健康检查"""
        start_time = time.time()
        results = []
        
        # 执行服务检查
        for checker in self._service_checkers.values():
            results.append(checker.check())
        
        # 执行依赖检查
        for checker in self._dependency_checkers.values():
            results.append(checker.check())
        
        # 执行自定义检查
        for checker in self._custom_checkers.values():
            results.append(checker.check())
        
        # 计算总体状态
        overall_status = self._calculate_overall_status(results)
        
        # 创建报告
        report = HealthReport(
            overall_status=overall_status,
            check_results=results,
            duration_ms=(time.time() - start_time) * 1000,
        )
        report.get_summary()
        
        self._last_report = report
        self._results = {r.name: r for r in results}
        
        return report
    
    def _calculate_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """计算总体健康状态"""
        if not results:
            return HealthStatus.UNKNOWN
        
        # 检查是否有严重问题
        has_unhealthy = any(r.status == HealthStatus.UNHEALTHY for r in results)
        has_degraded = any(r.status == HealthStatus.DEGRADED for r in results)
        
        if has_unhealthy:
            # 如果有任何关键依赖不可用，返回不健康
            critical_failed = any(
                r.status == HealthStatus.UNHEALTHY and 
                isinstance(r.check_type, CheckType) and 
                r.check_type == CheckType.DEPENDENCY
                for r in results
            )
            return HealthStatus.UNHEALTHY if critical_failed else HealthStatus.DEGRADED
        elif has_degraded:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def get_status(self) -> Dict[str, HealthStatus]:
        """获取所有检查的状态"""
        return {name: result.status for name, result in self._results.items()}
    
    def get_last_report(self) -> Optional[HealthReport]:
        """获取上次健康报告"""
        return self._last_report
    
    def get_checkers_count(self) -> Dict[str, int]:
        """获取检查器数量统计"""
        return {
            "service_checkers": len(self._service_checkers),
            "dependency_checkers": len(self._dependency_checkers),
            "custom_checkers": len(self._custom_checkers),
            "total_checkers": len(self._service_checkers) + len(self._dependency_checkers) + len(self._custom_checkers),
        }
    
    def clear(self) -> None:
        """清除所有检查器和结果"""
        self._service_checkers.clear()
        self._dependency_checkers.clear()
        self._custom_checkers.clear()
        self._results.clear()
        self._last_report = None


def create_health_checker() -> HealthChecker:
    """创建健康检查器实例"""
    return HealthChecker()


def create_service_check(
    name: str,
    host: str,
    port: int,
    check_type: str = "tcp",
    **kwargs,
) -> ServiceCheckConfig:
    """创建服务检查配置"""
    return ServiceCheckConfig(
        name=name,
        host=host,
        port=port,
        check_type=check_type,
        **kwargs,
    )


def create_dependency_check(
    name: str,
    check_function: Optional[Callable[[], Tuple[bool, str]]] = None,
    command: Optional[str] = None,
    import_name: Optional[str] = None,
    **kwargs,
) -> DependencyCheckConfig:
    """创建依赖检查配置"""
    return DependencyCheckConfig(
        name=name,
        check_function=check_function,
        command=command,
        import_name=import_name,
        **kwargs,
    )


def create_custom_check(
    name: str,
    check_function: Callable[[], HealthCheckResult],
    check_type: CheckType = CheckType.CUSTOM,
    **kwargs,
) -> CustomCheckConfig:
    """创建自定义检查配置"""
    return CustomCheckConfig(
        name=name,
        check_function=check_function,
        check_type=check_type,
        **kwargs,
    )
