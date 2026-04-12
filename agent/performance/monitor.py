"""
Performance Monitor - 运行时性能监控
实时监控关键指标，支持告警
版本: v5.0
"""
import time
import threading
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json

# ========== 监控指标类型 ==========

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"          # 计数器
    GAUGE = "gauge"             # 瞬时值
    HISTOGRAM = "histogram"     # 直方图
    RATE = "rate"              # 速率

@dataclass
class MetricSample:
    """指标样本"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class MetricWindow:
    """指标窗口"""
    name: str
    samples: List[MetricSample] = field(default_factory=list)
    max_size: int = 1000

    def add(self, sample: MetricSample) -> None:
        self.samples.append(sample)
        if len(self.samples) > self.max_size:
            self.samples.pop(0)

    def recent(self, seconds: float = 60) -> List[MetricSample]:
        """获取最近N秒的样本"""
        cutoff = time.time() - seconds
        return [s for s in self.samples if s.timestamp >= cutoff]

    def avg(self, seconds: float = 60) -> float:
        """计算平均值"""
        recent_samples = self.recent(seconds)
        if not recent_samples:
            return 0.0
        return sum(s.value for s in recent_samples) / len(recent_samples)

    def max(self, seconds: float = 60) -> float:
        """计算最大值"""
        recent_samples = self.recent(seconds)
        if not recent_samples:
            return 0.0
        return max(s.value for s in recent_samples)

    def min(self, seconds: float = 60) -> float:
        """计算最小值"""
        recent_samples = self.recent(seconds)
        if not recent_samples:
            return 0.0
        return min(s.value for s in recent_samples)


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: str = "warning"  # info, warning, critical
    window_seconds: float = 60
    cooldown_seconds: float = 300

    def evaluate(self, value: float) -> bool:
        """评估条件"""
        if self.condition == "gt":
            return value > self.threshold
        elif self.condition == "lt":
            return value < self.threshold
        elif self.condition == "gte":
            return value >= self.threshold
        elif self.condition == "lte":
            return value <= self.threshold
        elif self.condition == "eq":
            return abs(value - self.threshold) < 0.001
        return False


# ========== 运行时监控器 ==========

class RuntimeMonitor:
    """
    运行时性能监控器

    功能：
    1. 实时指标收集
    2. 滑动窗口统计
    3. 告警管理
    4. 健康检查

    预设指标：
    - request_count: 请求计数
    - request_latency: 请求延迟
    - error_count: 错误计数
    - active_sessions: 活跃会话数
    - cache_hit_rate: 缓存命中率
    - memory_usage: 内存使用
    """

    # 预设告警规则
    DEFAULT_ALERT_RULES = [
        AlertRule(
            name="High Latency",
            metric="request_latency_p95",
            condition="gt",
            threshold=2.0,
            severity="warning",
            window_seconds=300
        ),
        AlertRule(
            name="Critical Latency",
            metric="request_latency_p99",
            condition="gt",
            threshold=5.0,
            severity="critical",
            window_seconds=300
        ),
        AlertRule(
            name="High Error Rate",
            metric="error_rate",
            condition="gt",
            threshold=0.05,
            severity="critical",
            window_seconds=60
        ),
        AlertRule(
            name="Low Cache Hit Rate",
            metric="cache_hit_rate",
            condition="lt",
            threshold=0.5,
            severity="warning",
            window_seconds=300
        ),
    ]

    def __init__(self):
        self._metrics: Dict[str, MetricWindow] = {}
        self._alert_rules: Dict[str, AlertRule] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._alert_cooldowns: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._enabled = True

        # 注册预设指标
        self._init_metrics()

        # 注册预设告警规则
        for rule in self.DEFAULT_ALERT_RULES:
            self._alert_rules[rule.name] = rule

    def _init_metrics(self) -> None:
        """初始化预设指标"""
        preset_metrics = [
            ("request_count", MetricType.COUNTER),
            ("request_latency", MetricType.HISTOGRAM),
            ("error_count", MetricType.COUNTER),
            ("active_sessions", MetricType.GAUGE),
            ("cache_hits", MetricType.COUNTER),
            ("cache_misses", MetricType.COUNTER),
            ("rag_retrieval_time", MetricType.HISTOGRAM),
            ("emotion_detection_time", MetricType.HISTOGRAM),
            ("crisis_detection_time", MetricType.HISTOGRAM),
        ]

        for name, mtype in preset_metrics:
            self._metrics[name] = MetricWindow(name=name)

    # ========== 指标操作 ==========

    def record(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        记录指标

        Args:
            metric_name: 指标名称
            value: 指标值
            labels: 可选标签
        """
        if not self._enabled:
            return

        with self._lock:
            if metric_name not in self._metrics:
                self._metrics[metric_name] = MetricWindow(name=metric_name)

            sample = MetricSample(
                name=metric_name,
                value=value,
                labels=labels or {}
            )
            self._metrics[metric_name].add(sample)

            # 检查告警
            self._check_alerts(metric_name, value)

    def increment(self, metric_name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """递增计数器"""
        self.record(metric_name, value, labels)

    def gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """设置瞬时值"""
        self.record(metric_name, value, labels)

    # ========== 指标查询 ==========

    def get(self, metric_name: str, window_seconds: float = 60) -> Dict[str, float]:
        """获取指标统计"""
        with self._lock:
            if metric_name not in self._metrics:
                return {}

            window = self._metrics[metric_name]
            return {
                "avg": window.avg(window_seconds),
                "max": window.max(window_seconds),
                "min": window.min(window_seconds),
                "count": len(window.recent(window_seconds)),
            }

    def get_all_stats(self, window_seconds: float = 60) -> Dict[str, Dict[str, float]]:
        """获取所有指标统计"""
        with self._lock:
            return {
                name: self.get(name, window_seconds)
                for name in self._metrics.keys()
            }

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        stats = self.get_all_stats(60)

        # 计算综合健康分数
        health_score = 100.0
        issues = []

        # 检查延迟
        latency = stats.get("request_latency", {})
        if latency:
            if latency.get("max", 0) > 5.0:
                health_score -= 30
                issues.append("极高延迟")
            elif latency.get("avg", 0) > 1.0:
                health_score -= 10

        # 检查错误率
        error_count = stats.get("error_count", {}).get("count", 0)
        request_count = stats.get("request_count", {}).get("count", 1)
        error_rate = error_count / max(request_count, 1)

        if error_rate > 0.1:
            health_score -= 40
            issues.append(f"高错误率 ({error_rate:.1%})")
        elif error_rate > 0.05:
            health_score -= 20
            issues.append(f"错误率上升 ({error_rate:.1%})")

        # 检查缓存命中率
        cache_hits = stats.get("cache_hits", {}).get("count", 0)
        cache_misses = stats.get("cache_misses", {}).get("count", 0)
        total_cache = cache_hits + cache_misses

        if total_cache > 0:
            hit_rate = cache_hits / total_cache
            if hit_rate < 0.3:
                health_score -= 10
                issues.append(f"缓存命中率低 ({hit_rate:.1%})")

        # 确定状态
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "score": max(0, health_score),
            "issues": issues,
            "timestamp": time.time(),
        }

    # ========== 告警管理 ==========

    def _check_alerts(self, metric_name: str, value: float) -> None:
        """检查告警规则"""
        for rule in self._alert_rules.values():
            if rule.metric != metric_name:
                continue

            # 检查冷却
            if rule.name in self._alert_cooldowns:
                if time.time() - self._alert_cooldowns[rule.name] < rule.cooldown_seconds:
                    continue

            # 评估条件
            if rule.evaluate(value):
                self._fire_alert(rule)

    def _fire_alert(self, rule: AlertRule) -> None:
        """触发告警"""
        alert = {
            "name": rule.name,
            "severity": rule.severity,
            "metric": rule.metric,
            "threshold": rule.threshold,
            "timestamp": time.time(),
        }

        self._alerts.append(alert)
        self._alert_cooldowns[rule.name] = time.time()

        # 记录到日志
        severity_icons = {
            "info": "[INFO]",
            "warning": "[WARN]",
            "critical": "[CRIT]",
        }
        icon = severity_icons.get(rule.severity, "[ALERT]")
        print(f"{icon} Alert: {rule.name} - {rule.metric} 触发告警 (阈值: {rule.threshold})")

    def get_active_alerts(self, max_age_seconds: float = 3600) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        cutoff = time.time() - max_age_seconds
        return [a for a in self._alerts if a["timestamp"] >= cutoff]

    def add_alert_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        with self._lock:
            self._alert_rules[rule.name] = rule

    def clear_alerts(self) -> None:
        """清除告警历史"""
        with self._lock:
            self._alerts.clear()

    # ========== 报告 ==========

    def generate_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        health = self.get_health_status()
        stats = self.get_all_stats(300)  # 5分钟窗口

        return {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "metrics": stats,
            "active_alerts": self.get_active_alerts(),
            "alert_rules": {
                name: {
                    "condition": f"{rule.condition} {rule.threshold}",
                    "severity": rule.severity,
                }
                for name, rule in self._alert_rules.items()
            },
        }

    def print_report(self) -> None:
        """打印监控报告"""
        report = self.generate_report()

        print()
        print("=" * 60)
        print(" 运行时监控报告")
        print("=" * 60)

        # 健康状态
        health = report["health"]
        status_color = {
            "healthy": "\033[92m",    # 绿色
            "degraded": "\033[93m",   # 黄色
            "unhealthy": "\033[91m", # 红色
        }
        color = status_color.get(health["status"], "")
        reset = "\033[0m"

        print(f"\n健康状态: {color}{health['status'].upper()}{reset} (分数: {health['score']})")

        if health["issues"]:
            print("问题:")
            for issue in health["issues"]:
                print(f"  - {issue}")

        # 关键指标
        print("\n关键指标 (5分钟窗口):")
        print("-" * 40)

        key_metrics = ["request_count", "request_latency", "error_count", "cache_hits", "cache_misses"]
        for name in key_metrics:
            if name in report["metrics"]:
                m = report["metrics"][name]
                if m.get("count", 0) > 0:
                    print(f"  {name}: count={m['count']}, avg={m['avg']*1000:.2f}ms, max={m['max']*1000:.2f}ms")

        # 活跃告警
        alerts = report["active_alerts"]
        if alerts:
            print(f"\n活跃告警 ({len(alerts)}):")
            for alert in alerts:
                print(f"  [{alert['severity']}] {alert['name']}")
        else:
            print("\n无活跃告警")

        print()


# ========== 全局监控器 ==========

_monitor_global: Optional[RuntimeMonitor] = None


def get_monitor() -> RuntimeMonitor:
    """获取全局监控器"""
    global _monitor_global
    if _monitor_global is None:
        _monitor_global = RuntimeMonitor()
    return _monitor_global


# ========== 便捷函数 ==========

def record_metric(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """记录指标"""
    get_monitor().record(name, value, labels)


def increment_counter(name: str, value: float = 1.0) -> None:
    """递增计数器"""
    get_monitor().increment(name, value)


def set_gauge(name: str, value: float) -> None:
    """设置瞬时值"""
    get_monitor().gauge(name, value)


def get_health() -> Dict[str, Any]:
    """获取健康状态"""
    return get_monitor().get_health_status()


def print_monitor_report() -> None:
    """打印监控报告"""
    get_monitor().print_report()
