# -*- coding: utf-8 -*-
"""GPU Monitor - GPU 资源监控

支持 NVIDIA GPU 监控和资源分配。
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import subprocess
import json

logger = logging.getLogger(__name__)


@dataclass
class GPUDevice:
    """GPU 设备信息"""
    index: int
    name: str
    memory_total_mb: int
    memory_used_mb: int
    utilization_percent: float
    temperature_c: float
    power_watts: float
    cuda_version: str = ""
    driver_version: str = ""
    available: bool = True


@dataclass
class GPUAllocation:
    """GPU 分配"""
    allocation_id: str
    device_index: int
    agent_id: str
    memory_allocated_mb: int
    created_at: datetime
    expires_at: datetime = None


class GPUMonitor:
    """GPU 监控器"""
    
    def __init__(self):
        self._devices: List[GPUDevice] = []
        self._allocations: Dict[str, GPUAllocation] = {}
        self._monitoring: bool = False
    
    async def detect_devices(self) -> List[GPUDevice]:
        """检测 GPU 设备"""
        devices = []
        
        try:
            # 使用 nvidia-smi 检测
            result = await self._run_command([
                "nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits"
            ])
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    parts = [p.strip() for p in line.split(',')]
                    
                    if len(parts) >= 7:
                        device = GPUDevice(
                            index=int(parts[0]),
                            name=parts[1],
                            memory_total_mb=int(parts[2]),
                            memory_used_mb=int(parts[3]),
                            utilization_percent=float(parts[4]),
                            temperature_c=float(parts[5]),
                            power_watts=float(parts[6])
                        )
                        devices.append(device)
            
        except FileNotFoundError:
            logger.warning("nvidia-smi not found, GPU monitoring disabled")
        except Exception as e:
            logger.error(f"Failed to detect GPU devices: {e}")
        
        self._devices = devices
        return devices
    
    async def get_device_status(self, device_index: int = None) -> Dict[str, Any]:
        """获取设备状态"""
        if device_index is not None:
            devices = [d for d in self._devices if d.index == device_index]
            if not devices:
                return {"error": f"Device {device_index} not found"}
            device = devices[0]
            
            return {
                "index": device.index,
                "name": device.name,
                "memory_total_mb": device.memory_total_mb,
                "memory_used_mb": device.memory_used_mb,
                "memory_free_mb": device.memory_total_mb - device.memory_used_mb,
                "utilization_percent": device.utilization_percent,
                "temperature_c": device.temperature_c,
                "power_watts": device.power_watts
            }
        
        # 返回所有设备
        return {
            device.index: {
                "name": device.name,
                "memory_used_mb": device.memory_used_mb,
                "memory_total_mb": device.memory_total_mb,
                "utilization_percent": device.utilization_percent,
                "temperature_c": device.temperature_c
            }
            for device in self._devices
        }
    
    async def allocate_memory(
        self,
        agent_id: str,
        device_index: int,
        memory_mb: int
    ) -> Optional[GPUAllocation]:
        """分配 GPU 内存"""
        # 检查设备是否存在
        device = next((d for d in self._devices if d.index == device_index), None)
        
        if not device:
            logger.error(f"Device {device_index} not found")
            return None
        
        # 检查是否有足够内存
        available = device.memory_total_mb - device.memory_used_mb
        
        if memory_mb > available:
            logger.error(f"Insufficient GPU memory: {memory_mb} > {available}")
            return None
        
        # 创建分配
        allocation = GPUAllocation(
            allocation_id=f"alloc_{agent_id}_{device_index}_{int(datetime.now().timestamp())}",
            device_index=device_index,
            agent_id=agent_id,
            memory_allocated_mb=memory_mb,
            created_at=datetime.now()
        )
        
        self._allocations[allocation.allocation_id] = allocation
        
        # 更新设备状态
        device.memory_used_mb += memory_mb
        
        logger.info(f"GPU memory allocated: {agent_id} -> {device_index} ({memory_mb} MB)")
        
        return allocation
    
    async def release_memory(self, allocation_id: str) -> bool:
        """释放 GPU 内存"""
        if allocation_id not in self._allocations:
            return False
        
        allocation = self._allocations[allocation_id]
        
        # 更新设备状态
        device = next((d for d in self._devices if d.index == allocation.device_index), None)
        
        if device:
            device.memory_used_mb -= allocation.memory_allocated_mb
        
        del self._allocations[allocation_id]
        
        logger.info(f"GPU memory released: {allocation_id}")
        
        return True
    
    async def get_memory_usage(self, agent_id: str = None) -> Dict[str, Any]:
        """获取内存使用情况"""
        if agent_id:
            allocations = [a for a in self._allocations.values() if a.agent_id == agent_id]
            
            return {
                "agent_id": agent_id,
                "total_allocated_mb": sum(a.memory_allocated_mb for a in allocations),
                "allocations": [
                    {
                        "allocation_id": a.allocation_id,
                        "device_index": a.device_index,
                        "memory_mb": a.memory_allocated_mb
                    }
                    for a in allocations
                ]
            }
        
        # 总体使用
        total_allocated = sum(a.memory_allocated_mb for a in self._allocations.values())
        total_available = sum(d.memory_total_mb for d in self._devices)
        
        return {
            "total_allocated_mb": total_allocated,
            "total_available_mb": total_available,
            "utilization_percent": (total_allocated / total_available * 100) if total_available > 0 else 0,
            "devices": await self.get_device_status()
        }
    
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """运行命令"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return subprocess.CompletedProcess(
            cmd=cmd,
            returncode=process.returncode,
            stdout=stdout.decode(),
            stderr=stderr.decode()
        )
    
    async def start_monitoring(self, interval_seconds: int = 5):
        """开始监控"""
        self._monitoring = True
        
        while self._monitoring:
            await self._update_metrics()
            await asyncio.sleep(interval_seconds)
    
    async def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
    
    async def _update_metrics(self):
        """更新指标"""
        await self.detect_devices()


class GPUManager:
    """GPU 资源管理器"""
    
    def __init__(self):
        self.monitor = GPUMonitor()
        self._initialized = False
    
    async def initialize(self):
        """初始化"""
        if not self._initialized:
            await self.monitor.detect_devices()
            self._initialized = True
    
    async def allocate_for_agent(
        self,
        agent_id: str,
        required_memory_mb: int,
        preferred_devices: List[int] = None
    ) -> Optional[GPUAllocation]:
        """为 Agent 分配 GPU"""
        await self.initialize()
        
        # 首选设备
        if preferred_devices:
            for device_idx in preferred_devices:
                allocation = await self.monitor.allocate_memory(
                    agent_id=agent_id,
                    device_index=device_idx,
                    memory_mb=required_memory_mb
                )
                if allocation:
                    return allocation
        
        # 选择可用设备
        for device in self.monitor._devices:
            allocation = await self.monitor.allocate_memory(
                agent_id=agent_id,
                device_index=device.index,
                memory_mb=required_memory_mb
            )
            if allocation:
                return allocation
        
        return None
    
    async def release_agent_memory(self, agent_id: str) -> int:
        """释放 Agent 的所有 GPU 内存"""
        allocations = [
            a for a in self.monitor._allocations.values()
            if a.agent_id == agent_id
        ]
        
        released = 0
        for alloc in allocations:
            if await self.monitor.release_memory(alloc.allocation_id):
                released += alloc.memory_allocated_mb
        
        return released
    
    async def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "initialized": self._initialized,
            "devices_count": len(self.monitor._devices),
            "memory_usage": await self.monitor.get_memory_usage()
        }


# 模块级单例
_global_gpu_manager = GPUManager()


# 便捷函数
def get_gpu_manager() -> GPUManager:
    """获取 GPU 管理器"""
    return _global_gpu_manager


# 全局实例
_gpu_manager: Optional[GPUManager] = None


def init_gpu_manager() -> GPUManager:
    """初始化 GPU 管理器"""
    global _gpu_manager
    _gpu_manager = GPUManager()
    return _gpu_manager
