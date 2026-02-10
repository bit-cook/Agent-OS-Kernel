# -*- coding: utf-8 -*-
"""轨迹记录器 - Agent 学习的基础

记录 Agent 的执行轨迹，用于：
1. 经验积累
2. 模式识别
3. 策略优化
"""

import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrajectoryPhase(Enum):
    """轨迹阶段"""
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    WAITING = "waiting"


@dataclass
class TrajectoryStep:
    """轨迹步骤"""
    step_id: str
    phase: TrajectoryPhase
    timestamp: float
    thought: Optional[str] = None
    action: Optional[Dict] = None
    tool_call: Optional[Dict] = None
    observation: Optional[str] = None
    reflection: Optional[str] = None
    confidence: float = 0.5
    metadata: Dict = field(default_factory=dict)


@dataclass
class Trajectory:
    """完整轨迹"""
    trajectory_id: str
    agent_name: str
    agent_pid: str
    task: str
    start_time: float
    end_time: Optional[float] = None
    steps: List[TrajectoryStep] = field(default_factory=list)
    outcome: Optional[str] = None
    success: bool = False
    total_tokens: int = 0
    total_tools_used: int = 0
    avg_confidence: float = 0.5
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trajectory_id': self.trajectory_id,
            'agent_name': self.agent_name,
            'agent_pid': self.agent_pid,
            'task': self.task,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'steps_count': len(self.steps),
            'outcome': self.outcome,
            'success': self.success,
            'total_tokens': self.total_tokens,
            'total_tools_used': self.total_tools_used,
            'avg_confidence': self.avg_confidence,
            'steps': [s.__dict__ for s in self.steps]
        }
    
    def duration(self) -> float:
        """获取持续时间"""
        end = self.end_time or time.time()
        return end - self.start_time


class TrajectoryRecorder:
    """轨迹记录器"""
    
    def __init__(self, storage_dir: str = "./trajectories"):
        self.storage_dir = storage_dir
        self.current_trajectory: Optional[Trajectory] = None
        self.trajectories: List[Trajectory] = []
        self.step_count = 0
        
        import os
        os.makedirs(storage_dir, exist_ok=True)
    
    def start_recording(self, agent_name: str, agent_pid: str, task: str) -> str:
        """开始记录轨迹"""
        self.current_trajectory = Trajectory(
            trajectory_id=f"traj_{int(time.time())}_{agent_name}",
            agent_name=agent_name,
            agent_pid=agent_pid,
            task=task,
            start_time=time.time()
        )
        self.step_count = 0
        logger.info(f"Started recording trajectory for {agent_name}")
        return self.current_trajectory.trajectory_id
    
    def add_step(
        self,
        phase: TrajectoryPhase,
        thought: Optional[str] = None,
        action: Optional[Dict] = None,
        tool_call: Optional[Dict] = None,
        observation: Optional[str] = None,
        reflection: Optional[str] = None,
        confidence: float = 0.5,
        metadata: Dict = None
    ):
        """添加步骤"""
        if not self.current_trajectory:
            logger.warning("No active trajectory, ignoring step")
            return
        
        step = TrajectoryStep(
            step_id=f"step_{self.step_count}",
            phase=phase,
            timestamp=time.time(),
            thought=thought,
            action=action,
            tool_call=tool_call,
            observation=observation,
            reflection=reflection,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        self.current_trajectory.steps.append(step)
        self.step_count += 1
        
        # 更新置信度
        self._update_avg_confidence()
    
    def finish_recording(
        self,
        outcome: str,
        success: bool,
        total_tokens: int = 0,
        total_tools_used: int = 0
    ) -> Trajectory:
        """完成记录"""
        if not self.current_trajectory:
            logger.warning("No active trajectory to finish")
            return None
        
        self.current_trajectory.end_time = time.time()
        self.current_trajectory.outcome = outcome
        self.current_trajectory.success = success
        self.current_trajectory.total_tokens = total_tokens
        self.current_trajectory.total_tools_used = total_tools_used
        self.current_trajectory.avg_confidence = self._update_avg_confidence()
        
        trajectory = self.current_trajectory
        self.trajectories.append(trajectory)
        self.current_trajectory = None
        
        # 保存到文件
        self._save_to_file(trajectory)
        
        logger.info(f"Finished recording trajectory {trajectory.trajectory_id}: {success}")
        return trajectory
    
    def _update_avg_confidence(self) -> float:
        """更新平均置信度"""
        if not self.current_trajectory or not self.current_trajectory.steps:
            return 0.5
        
        total = sum(s.confidence for s in self.current_trajectory.steps)
        avg = total / len(self.current_trajectory.steps)
        self.current_trajectory.avg_confidence = avg
        return avg
    
    def _save_to_file(self, trajectory: Trajectory):
        """保存到文件"""
        import os
        filename = os.path.join(
            self.storage_dir,
            f"{trajectory.trajectory_id}.json"
        )
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(trajectory.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trajectory: {e}")
    
    def get_trajectories(
        self,
        agent_name: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100
    ) -> List[Trajectory]:
        """获取轨迹列表"""
        result = []
        
        for traj in reversed(self.trajectories):
            if agent_name and traj.agent_name != agent_name:
                continue
            if success is not None and traj.success != success:
                continue
            result.append(traj)
            if len(result) >= limit:
                break
        
        return result
    
    def get_success_rate(self, agent_name: Optional[str] = None) -> float:
        """获取成功率"""
        trajectories = self.get_trajectories(agent_name)
        if not trajectories:
            return 0.0
        
        successful = sum(1 for t in trajectories if t.success)
        return successful / len(trajectories)
    
    def get_common_patterns(self, agent_name: str = None) -> Dict[str, int]:
        """识别常见模式"""
        patterns = {}
        
        trajectories = self.get_trajectories(agent_name)
        for traj in trajectories:
            # 分析步骤序列
            sequence = [s.phase.value for s in traj.steps]
            pattern_key = " -> ".join(sequence[:5])  # 只取前5步
            
            if pattern_key not in patterns:
                patterns[pattern_key] = 0
            patterns[pattern_key] += 1
        
        # 按频率排序
        sorted_patterns = dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True))
        return sorted_patterns
    
    def get_average_metrics(self, agent_name: Optional[str] = None) -> Dict[str, float]:
        """获取平均指标"""
        trajectories = self.get_trajectories(agent_name)
        if not trajectories:
            return {}
        
        total_tokens = sum(t.total_tokens for t in trajectories)
        total_tools = sum(t.total_tools_used for t in trajectories)
        total_duration = sum(t.duration() for t in trajectories)
        
        return {
            'avg_tokens': total_tokens / len(trajectories),
            'avg_tools': total_tools / len(trajectories),
            'avg_duration': total_duration / len(trajectories),
            'success_rate': self.get_success_rate(agent_name),
            'total_trajectories': len(trajectories)
        }
    
    def clear(self, agent_name: Optional[str] = None):
        """清空轨迹"""
        if agent_name:
            self.trajectories = [
                t for t in self.trajectories
                if t.agent_name != agent_name
            ]
        else:
            self.trajectories = []
        logger.info("Trajectories cleared")
