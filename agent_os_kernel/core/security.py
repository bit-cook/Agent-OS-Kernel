# -*- coding: utf-8 -*-
"""
Security Subsystem - 安全子系统

类比操作系统的权限管理 + 沙箱：
- Docker 容器隔离
- 完整的审计追踪
- 决策过程可视化
- 执行回放功能
"""

import os
import uuid
import time
import logging
import subprocess
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """权限级别"""
    RESTRICTED = "restricted"    # 仅只读操作
    STANDARD = "standard"        # 标准权限
    ELEVATED = "elevated"        # 提升权限
    ADMIN = "admin"              # 管理权限


@dataclass
class SecurityPolicy:
    """
    安全策略配置
    
    定义 Agent 的权限和资源限制
    """
    permission_level: PermissionLevel = PermissionLevel.STANDARD
    
    # 文件系统限制
    allowed_paths: List[str] = field(default_factory=lambda: ["/tmp", "/workspace"])
    blocked_paths: List[str] = field(default_factory=lambda: ["/etc", "/root", "/var/log"])
    read_only: bool = False
    
    # 网络限制
    network_enabled: bool = True
    allowed_hosts: List[str] = field(default_factory=list)
    blocked_hosts: List[str] = field(default_factory=list)
    
    # 资源限制
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    max_execution_time: int = 300
    max_file_size_mb: int = 100
    
    # 工具限制
    allowed_tools: Optional[List[str]] = None  # None 表示允许所有
    blocked_tools: List[str] = field(default_factory=list)
    
    # 沙箱配置
    use_sandbox: bool = True
    sandbox_image: str = "agent-sandbox:latest"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'permission_level': self.permission_level.value,
            'allowed_paths': self.allowed_paths,
            'blocked_paths': self.blocked_paths,
            'read_only': self.read_only,
            'network_enabled': self.network_enabled,
            'allowed_hosts': self.allowed_hosts,
            'blocked_hosts': self.blocked_hosts,
            'max_memory_mb': self.max_memory_mb,
            'max_cpu_percent': self.max_cpu_percent,
            'max_execution_time': self.max_execution_time,
            'max_file_size_mb': self.max_file_size_mb,
            'allowed_tools': self.allowed_tools,
            'blocked_tools': self.blocked_tools,
            'use_sandbox': self.use_sandbox,
            'sandbox_image': self.sandbox_image,
        }


class SandboxManager:
    """
    沙箱管理器
    
    使用 Docker 容器隔离 Agent 执行环境
    """
    
    def __init__(self):
        self.containers: Dict[str, Any] = {}
        self.docker_available = self._check_docker()
        
        if self.docker_available:
            try:
                import docker
                self.docker_client = docker.from_env()
                logger.info("Docker sandbox available")
            except Exception as e:
                logger.warning(f"Docker client initialization failed: {e}")
                self.docker_available = False
                self.docker_client = None
        else:
            logger.warning("Docker not available, using fallback isolation")
            self.docker_client = None
    
    def _check_docker(self) -> bool:
        """检查 Docker 是否可用"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def create_sandbox(self, agent_pid: str, 
                      policy: Optional[SecurityPolicy] = None) -> Optional[str]:
        """
        为 Agent 创建隔离的沙箱
        
        Args:
            agent_pid: Agent PID
            policy: 安全策略
        
        Returns:
            容器 ID，如果创建失败则返回 None
        """
        policy = policy or SecurityPolicy()
        
        if not self.docker_available or not policy.use_sandbox:
            logger.info(f"Using process-level isolation for agent {agent_pid[:8]}...")
            return self._create_process_isolation(agent_pid, policy)
        
        try:
            # 创建工作目录
            workspace = f"/tmp/agent-os-{agent_pid}"
            os.makedirs(workspace, exist_ok=True)
            
            # 构建容器配置
            container_config = {
                'image': policy.sandbox_image,
                'detach': True,
                'name': f"agent-os-{agent_pid[:8]}",
                'environment': {
                    'AGENT_PID': agent_pid,
                    'PERMISSION_LEVEL': policy.permission_level.value,
                },
                'volumes': {
                    workspace: {'bind': '/workspace', 'mode': 'ro' if policy.read_only else 'rw'}
                },
                'network_mode': 'bridge' if policy.network_enabled else 'none',
                'mem_limit': f"{policy.max_memory_mb}m",
                'cpu_percent': policy.max_cpu_percent,
                'auto_remove': True,
            }
            
            container = self.docker_client.containers.run(**container_config)
            self.containers[agent_pid] = container
            
            logger.info(f"Created sandbox for agent {agent_pid[:8]}... (container: {container.id[:12]})")
            return container.id
            
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            return self._create_process_isolation(agent_pid, policy)
    
    def _create_process_isolation(self, agent_pid: str, 
                                  policy: SecurityPolicy) -> str:
        """
        创建进程级隔离（Docker 不可用时的回退方案）
        """
        # 创建工作目录作为隔离边界
        workspace = f"/tmp/agent-os-{agent_pid}"
        os.makedirs(workspace, exist_ok=True)
        
        # 记录隔离配置
        self.containers[agent_pid] = {
            'type': 'process',
            'workspace': workspace,
            'policy': policy,
            'created_at': time.time(),
        }
        
        return f"process-{agent_pid[:8]}"
    
    def execute_in_sandbox(self, agent_pid: str, command: str,
                          timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        在沙箱中执行命令
        
        Args:
            agent_pid: Agent PID
            command: 要执行的命令
            timeout: 超时时间（秒）
        
        Returns:
            执行结果
        """
        timeout = timeout or 30
        
        if agent_pid not in self.containers:
            return {
                'success': False,
                'error': 'Sandbox not found',
                'stdout': '',
                'stderr': ''
            }
        
        container = self.containers[agent_pid]
        
        # Docker 沙箱
        if hasattr(container, 'exec_run'):
            return self._execute_in_docker(container, command, timeout)
        
        # 进程级隔离
        return self._execute_in_process(container, command, timeout)
    
    def _execute_in_docker(self, container, command: str, 
                          timeout: int) -> Dict[str, Any]:
        """在 Docker 容器中执行"""
        try:
            result = container.exec_run(
                command,
                demux=True,
                timeout=timeout
            )
            
            stdout = result.output[0].decode() if result.output[0] else ""
            stderr = result.output[1].decode() if result.output[1] else ""
            
            return {
                'success': result.exit_code == 0,
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': result.exit_code
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': ''
            }
    
    def _execute_in_process(self, container_info: Dict, command: str,
                           timeout: int) -> Dict[str, Any]:
        """在进程级隔离中执行"""
        policy = container_info['policy']
        workspace = container_info['workspace']
        
        # 检查命令是否在允许的工具列表中
        cmd_parts = command.split()
        if cmd_parts:
            tool_name = cmd_parts[0]
            if policy.allowed_tools and tool_name not in policy.allowed_tools:
                return {
                    'success': False,
                    'error': f'Tool {tool_name} is not in allowed tools list',
                    'stdout': '',
                    'stderr': ''
                }
            if tool_name in policy.blocked_tools:
                return {
                    'success': False,
                    'error': f'Tool {tool_name} is blocked',
                    'stdout': '',
                    'stderr': ''
                }
        
        try:
            # 设置环境变量
            env = os.environ.copy()
            env['AGENT_PID'] = container_info.get('agent_pid', 'unknown')
            env['WORKSPACE'] = workspace
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace,
                env=env
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Command timed out after {timeout} seconds',
                'stdout': '',
                'stderr': ''
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': ''
            }
    
    def destroy_sandbox(self, agent_pid: str):
        """
        销毁沙箱
        
        Args:
            agent_pid: Agent PID
        """
        if agent_pid not in self.containers:
            return
        
        container = self.containers[agent_pid]
        
        try:
            # Docker 沙箱
            if hasattr(container, 'stop'):
                container.stop()
                container.remove()
                logger.info(f"Destroyed Docker sandbox for agent {agent_pid[:8]}...")
            
            # 进程级隔离：清理工作目录
            elif isinstance(container, dict) and 'workspace' in container:
                import shutil
                workspace = container['workspace']
                if os.path.exists(workspace):
                    shutil.rmtree(workspace, ignore_errors=True)
                logger.info(f"Cleaned up process isolation for agent {agent_pid[:8]}...")
            
        except Exception as e:
            logger.error(f"Error destroying sandbox: {e}")
        
        finally:
            del self.containers[agent_pid]
    
    def validate_file_access(self, agent_pid: str, filepath: str, 
                            mode: str = 'read') -> bool:
        """
        验证文件访问权限
        
        Args:
            agent_pid: Agent PID
            filepath: 文件路径
            mode: 'read' 或 'write'
        
        Returns:
            是否允许访问
        """
        if agent_pid not in self.containers:
            return False
        
        container = self.containers[agent_pid]
        
        # 获取策略
        if hasattr(container, 'policy'):
            policy = container.policy
        elif isinstance(container, dict):
            policy = container.get('policy', SecurityPolicy())
        else:
            return False
        
        # 检查写权限
        if mode == 'write' and policy.read_only:
            return False
        
        # 规范化路径
        abs_path = os.path.abspath(filepath)
        
        # 检查禁止路径
        for blocked in policy.blocked_paths:
            if abs_path.startswith(blocked):
                return False
        
        # 检查允许路径
        for allowed in policy.allowed_paths:
            if abs_path.startswith(allowed):
                return True
        
        # 默认拒绝
        return False
    
    def get_sandbox_info(self, agent_pid: str) -> Optional[Dict[str, Any]]:
        """获取沙箱信息"""
        if agent_pid not in self.containers:
            return None
        
        container = self.containers[agent_pid]
        
        if hasattr(container, 'attrs'):
            # Docker 容器
            return {
                'type': 'docker',
                'id': container.id,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else 'unknown',
            }
        elif isinstance(container, dict):
            # 进程级隔离
            return {
                'type': 'process',
                'workspace': container.get('workspace'),
                'created_at': container.get('created_at'),
            }
        
        return None


class PermissionManager:
    """
    权限管理器
    
    管理 Agent 的权限检查和授权
    """
    
    def __init__(self):
        self.agent_policies: Dict[str, SecurityPolicy] = {}
    
    def set_policy(self, agent_pid: str, policy: SecurityPolicy):
        """设置 Agent 的安全策略"""
        self.agent_policies[agent_pid] = policy
        logger.debug(f"Set security policy for agent {agent_pid[:8]}...")
    
    def get_policy(self, agent_pid: str) -> SecurityPolicy:
        """获取 Agent 的安全策略"""
        return self.agent_policies.get(agent_pid, SecurityPolicy())
    
    def can_use_tool(self, agent_pid: str, tool_name: str) -> bool:
        """检查是否可以使用工具"""
        policy = self.get_policy(agent_pid)
        
        if policy.allowed_tools is not None and tool_name not in policy.allowed_tools:
            return False
        
        if tool_name in policy.blocked_tools:
            return False
        
        return True
    
    def can_access_network(self, agent_pid: str, host: str) -> bool:
        """检查是否可以访问网络"""
        policy = self.get_policy(agent_pid)
        
        if not policy.network_enabled:
            return False
        
        if policy.blocked_hosts and host in policy.blocked_hosts:
            return False
        
        if policy.allowed_hosts and host not in policy.allowed_hosts:
            return False
        
        return True
    
    def check_resource_limits(self, agent_pid: str, 
                             memory_mb: int = 0,
                             execution_time: int = 0) -> Tuple[bool, str]:
        """
        检查资源限制
        
        Returns:
            (是否允许, 原因)
        """
        policy = self.get_policy(agent_pid)
        
        if memory_mb > policy.max_memory_mb:
            return False, f"Memory limit exceeded: {memory_mb}MB > {policy.max_memory_mb}MB"
        
        if execution_time > policy.max_execution_time:
            return False, f"Execution time limit exceeded: {execution_time}s > {policy.max_execution_time}s"
        
        return True, "OK"
