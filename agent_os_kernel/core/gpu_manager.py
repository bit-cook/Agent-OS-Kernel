"""
GPU Resource Manager - GPU资源管理器

支持NVIDIA GPU监控、内存管理、计算分配
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import asyncio


@dataclass
class GPUInfo:
    """GPU信息"""
    id: int
    name: str
    memory_total: int  # MB
    memory_used: int  # MB
    utilization: float  # 0-100
    temperature: float
    power: float  # W


@dataclass
class GPUAllocation:
    """GPU分配"""
    gpu_id: int
    memory_allocated: int  # MB
    processes: List[str] = field(default_factory=list)


class GPUManager:
    """GPU资源管理器"""
    
    def __init__(self):
        self._allocations: Dict[int, GPUAllocation] = {}
        self._monitoring_interval = 5.0  # seconds
        self._monitoring = False
    
    async def get_gpu_info(self, gpu_id: int) -> Optional[GPUInfo]:
        """获取GPU信息"""
        # 模拟GPU信息获取
        # 实际实现需要nvidia-ml-py
        return GPUInfo(
            id=gpu_id,
            name="NVIDIA GPU",
            memory_total=24576,
            memory_used=8192,
            utilization=45.5,
            temperature=65.0,
            power=150.0
        )
    
    async def get_all_gpus(self) -> List[GPUInfo]:
        """获取所有GPU"""
        # 模拟多GPU
        gpus = []
        for i in range(4):  # 4 GPUs
            info = await self.get_gpu_info(i)
            gpus.append(info)
        return gpus
    
    async def allocate(self, gpu_id: int, memory_mb: int, process_id: str) -> bool:
        """分配GPU内存"""
        if gpu_id not in self._allocations:
            self._allocations[gpu_id] = GPUAllocation(
                gpu_id=gpu_id,
                memory_allocated=0,
                processes=[]
            )
        
        alloc = self._allocations[gpu_id]
        
        # 检查可用内存
        info = await self.get_gpu_info(gpu_id)
        available = info.memory_total - info.memory_used - alloc.memory_allocated
        
        if available >= memory_mb:
            alloc.memory_allocated += memory_mb
            alloc.processes.append(process_id)
            return True
        
        return False
    
    async def release(self, gpu_id: int, process_id: str):
        """释放GPU内存"""
        if gpu_id in self._allocations:
            alloc = self._allocations[gpu_id]
            if process_id in alloc.processes:
                alloc.processes.remove(process_id)
    
    async def start_monitoring(self):
        """开始监控"""
        self._monitoring = True
        while self._monitoring:
            # 收集GPU指标
            for i in range(4):
                await self.get_gpu_info(i)
                # 这里可以记录到监控系统
            await asyncio.sleep(self._monitoring_interval)
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total_allocated = sum(a.memory_allocated for a in self._allocations.values())
        
        return {
            "gpu_count": 4,
            "total_allocated_mb": total_allocated,
            "active_allocations": len(self._allocations)
        }
