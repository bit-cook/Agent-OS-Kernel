# -*- coding: utf-8 -*-
"""Agent 优化器 - 基于轨迹学习的策略优化

功能：
1. 分析成功/失败轨迹
2. 生成优化建议
3. 自动调整策略参数
"""

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import timezone, datetime, timezone, timedelta
import re

logger = logging.getLogger(__name__)


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    category: str
    priority: str  # high, medium, low
    description: str
    rationale: str
    proposed_change: Dict[str, Any]
    expected_impact: str


@dataclass
class StrategyAnalysis:
    """策略分析结果"""
    agent_name: str
    success_rate: float
    avg_tokens: float
    avg_duration: float
    common_patterns: Dict[str, int]
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[OptimizationSuggestion] = field(default_factory=list)


class AgentOptimizer:
    """Agent 优化器"""
    
    def __init__(self, trajectory_recorder):
        self.recorder = trajectory_recorder
    
    def analyze(self, agent_name: str) -> StrategyAnalysis:
        """分析 Agent 策略"""
        metrics = self.recorder.get_average_metrics(agent_name)
        patterns = self.recorder.get_common_patterns(agent_name)
        
        # 分析成功 vs 失败
        trajectories = self.recorder.get_trajectories(agent_name)
        successful = [t for t in trajectories if t.success]
        failed = [t for t in trajectories if not t.success]
        
        strengths = []
        weaknesses = []
        suggestions = []
        
        # 分析成功模式
        if successful:
            success_patterns = {}
            for traj in successful:
                pattern = " -> ".join([s.phase.value for s in traj.steps[:3]])
                if pattern not in success_patterns:
                    success_patterns[pattern] = 0
                success_patterns[pattern] += 1
            
            # 识别优势
            if metrics.get('success_rate', 0) > 0.8:
                strengths.append("高成功率 (>80%)")
            if metrics.get('avg_tokens', 0) < 500:
                strengths.append("资源使用高效")
            
            # 分析成功模式
            for pattern, count in success_patterns.items():
                if count > 2:
                    suggestions.append(
                        OptimizationSuggestion(
                            category="pattern",
                            priority="medium",
                            description=f"常见成功模式: {pattern}",
                            rationale=f"这个模式在 {count} 个成功案例中出现",
                            proposed_change={"encourage_pattern": pattern},
                            expected_impact="提高成功率"
                        )
                    )
        
        # 分析失败模式
        if failed:
            failure_reasons = []
            for traj in failed:
                # 查找失败的共同特征
                if traj.total_tools_used > 10:
                    failure_reasons.append("工具使用过多")
                if traj.avg_confidence < 0.4:
                    failure_reasons.append("置信度低")
                if traj.duration() > 300:
                    failure_reasons.append("执行时间过长")
            
            # 统计失败原因
            reason_counts = {}
            for reason in failure_reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            for reason, count in reason_counts.items():
                if count >= 2:
                    weaknesses.append(f"频繁 {reason}")
                    suggestions.append(
                        OptimizationSuggestion(
                            category="improvement",
                            priority="high" if count > 3 else "medium",
                            description=f"避免 {reason}",
                            rationale=f"在 {count} 个失败案例中出现",
                            proposed_change={"avoid_pattern": reason},
                            expected_impact="减少失败率"
                        )
                    )
        
        # 生成优化建议
        if metrics.get('avg_tokens', 0) > 1000:
            suggestions.append(
                OptimizationSuggestion(
                    category="efficiency",
                    priority="medium",
                    description="优化上下文使用",
                    rationale="平均 Token 使用较高",
                    proposed_change={"max_tokens": 1000, "compress_context": True},
                    expected_impact="降低 API 成本"
                )
            )
        
        if metrics.get('avg_duration', 0) > 180:
            suggestions.append(
                OptimizationSuggestion(
                    category="performance",
                    priority="low",
                    description="优化执行流程",
                    rationale="平均执行时间较长",
                    proposed_change={"parallelize": True, "timeout": 120},
                    expected_impact="提高响应速度"
                )
            )
        
        return StrategyAnalysis(
            agent_name=agent_name,
            success_rate=metrics.get('success_rate', 0),
            avg_tokens=metrics.get('avg_tokens', 0),
            avg_duration=metrics.get('avg_duration', 0),
            common_patterns=patterns,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions
        )
    
    def generate_prompt_template(self, agent_name: str) -> str:
        """生成优化的 Prompt 模板"""
        analysis = self.analyze(agent_name)
        
        template_parts = []
        
        # 添加角色定义
        template_parts.append(f"# {agent_name}\n")
        template_parts.append("你是一个专业的 AI 助手，善于解决问题。\n")
        
        # 添加成功模式提示
        if analysis.success_rate > 0.7:
            template_parts.append("## 成功策略\n")
            template_parts.append("- 先思考，再行动\n")
            template_parts.append("- 分步骤解决问题\n")
            template_parts.append("- 保持简洁高效\n")
        
        # 添加避免事项
        if analysis.weaknesses:
            template_parts.append("\n## 注意事项\n")
            for weakness in analysis.weaknesses[:3]:
                template_parts.append(f"- 避免 {weakness}\n")
        
        return "".join(template_parts)
    
    def apply_optimization(self, agent_name: str, suggestion: OptimizationSuggestion) -> Dict[str, Any]:
        """应用优化建议"""
        logger.info(f"Applying optimization for {agent_name}: {suggestion.description}")
        
        # 这里应该更新 Agent 的配置
        # 简化处理：返回应用结果
        return {
            'applied': True,
            'agent': agent_name,
            'suggestion': suggestion.description,
            'timestamp': lambda: datetime.now(timezone.utc).isoformat()
        }
    
    def batch_optimize(self, agent_name: str) -> Dict[str, Any]:
        """批量优化"""
        analysis = self.analyze(agent_name)
        results = []
        
        for suggestion in analysis.suggestions:
            if suggestion.priority in ['high', 'medium']:
                result = self.apply_optimization(agent_name, suggestion)
                results.append(result)
        
        return {
            'agent': agent_name,
            'total_suggestions': len(analysis.suggestions),
            'applied': len(results),
            'results': results
        }
    
    def compare_strategies(self, agent_names: List[str]) -> Dict[str, Any]:
        """比较不同 Agent 策略"""
        comparisons = {}
        
        for name in agent_names:
            metrics = self.recorder.get_average_metrics(name)
            comparisons[name] = {
                'success_rate': metrics.get('success_rate', 0),
                'avg_tokens': metrics.get('avg_tokens', 0),
                'avg_duration': metrics.get('avg_duration', 0),
                'total_trajectories': metrics.get('total_trajectories', 0)
            }
        
        # 找出最佳
        best = max(comparisons.items(), key=lambda x: x[1]['success_rate'])
        
        return {
            'comparisons': comparisons,
            'best_agent': best[0],
            'best_metrics': best[1]
        }
    
    def get_report(self, agent_name: str) -> Dict[str, Any]:
        """生成完整报告"""
        analysis = self.analyze(agent_name)
        
        return {
            'agent_name': agent_name,
            'generated_at': lambda: datetime.now(timezone.utc).isoformat(),
            'summary': {
                'success_rate': f"{analysis.success_rate:.1%}",
                'avg_tokens': f"{analysis.avg_tokens:.0f}",
                'avg_duration': f"{analysis.avg_duration:.1f}s"
            },
            'strengths': analysis.strengths,
            'weaknesses': analysis.weaknesses,
            'suggestions_count': len(analysis.suggestions),
            'top_suggestions': [
                {
                    'description': s.description,
                    'priority': s.priority,
                    'impact': s.expected_impact
                }
                for s in analysis.suggestions[:5]
            ],
            'common_patterns': dict(list(analysis.common_patterns.items())[:5])
        }
