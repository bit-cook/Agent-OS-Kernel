"""
Monitoring System - 监控告警系统

健康检查、性能指标、告警规则
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from datetime import timezone, timezone, timedelta
from enum import Enum
import asyncio


class AlertSeverity(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """告警"""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    created_at: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


@dataclass
class HealthCheck:
    """健康检查"""
    name: str
    status: str  # healthy, unhealthy, unknown
    message: str
    duration_ms: float


class MonitoringSystem:
    """监控告警系统"""
    
    def __init__(self):
        self._alerts: List[Alert] = []
        self._health_checks: Dict[str, Callable] = {}
        self._metrics: Dict[str, float] = {}
        self._alert_rules: List[Dict] = []
        self._notifications: List[Callable] = []
    
    def add_health_check(self, name: str, check_func: Callable):
        """添加健康检查"""
        self._health_checks[name] = check_func
    
    async def check_all(self) -> List[HealthCheck]:
        """执行所有健康检查"""
        results = []
        
        for name, check_func in self._health_checks.items():
            start = datetime.now()
            try:
                if asyncio.iscoroutinefunction(check_func):
                    healthy = await check_func()
                else:
                    healthy = check_func()
                
                status = "healthy" if healthy else "unhealthy"
                message = f"{name} is {status}"
            except Exception as e:
                status = "unhealthy"
                message = f"{name} failed: {str(e)}"
            
            duration = (datetime.now() - start).total_seconds() * 1000
            
            results.append(HealthCheck(
                name=name,
                status=status,
                message=message,
                duration_ms=duration
            ))
        
        return results
    
    def record_metric(self, name: str, value: float):
        """记录指标"""
        self._metrics[name] = value
    
    def get_metric(self, name: str) -> float:
        """获取指标"""
        return self._metrics.get(name, 0.0)
    
    def add_alert_rule(self, rule: Dict):
        """添加告警规则"""
        self._alert_rules.append(rule)
    
    async def check_alerts(self):
        """检查告警规则"""
        for rule in self._alert_rules:
            metric = self.get_metric(rule["metric"])
            threshold = rule.get("threshold", 0)
            condition = rule.get("condition", "gt")
            
            should_alert = False
            if condition == "gt" and metric > threshold:
                should_alert = True
            elif condition == "lt" and metric < threshold:
                should_alert = True
            
            if should_alert:
                self.create_alert(
                    name=rule["name"],
                    severity=AlertSeverity[rule["severity"].upper()],
                    message=rule["message"]
                )
    
    def create_alert(self, name: str, severity: AlertSeverity, message: str):
        """创建告警"""
        alert_id = f"alert_{datetime.now(timezone.utc).timestamp()}"
        
        alert = Alert(
            id=alert_id,
            name=name,
            severity=severity,
            message=message,
            created_at=datetime.now(timezone.utc)
        )
        
        self._alerts.append(alert)
        
        # 通知
        for notify in self._notifications:
            try:
                if asyncio.iscoroutinefunction(notify):
                    asyncio.create_task(notify(alert))
                else:
                    notify(alert)
            except Exception:
                pass
    
    def add_notification(self, callback: Callable):
        """添加通知回调"""
        self._notifications.append(callback)
    
    def acknowledge_alert(self, alert_id: str):
        """确认告警"""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc)
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [a for a in self._alerts if a.status == AlertStatus.ACTIVE]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "active_alerts": len(self.get_active_alerts()),
            "total_alerts": len(self._alerts),
            "health_checks": len(self._health_checks),
            "metrics": len(self._metrics),
            "alert_rules": len(self._alert_rules)
        }
