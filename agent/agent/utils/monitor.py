"""
Monitor - 性能监控与系统状态追踪 + Prometheus指标导出
版本: 2.0
增强: Prometheus兼容、A/B测试支持、告警机制
"""
import time
import psutil
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from collections import deque
from enum import Enum

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class MonitorMetrics:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    active_sessions: int
    total_requests: int
    avg_response_time: float
    error_rate: float
    tool_call_count: int
    skill_call_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "timestamp_str": datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_percent": round(self.memory_percent, 2),
            "memory_used_mb": round(self.memory_used_mb, 2),
            "active_sessions": self.active_sessions,
            "total_requests": self.total_requests,
            "avg_response_time": round(self.avg_response_time, 3),
            "error_rate": round(self.error_rate, 4),
            "tool_call_count": self.tool_call_count,
            "skill_call_count": self.skill_call_count
        }


@dataclass
class AlertRule:
    name: str
    metric: str
    threshold: float
    comparison: str
    level: AlertLevel
    enabled: bool = True


@dataclass
class Alert:
    rule_name: str
    level: AlertLevel
    message: str
    metric_value: float
    threshold: float
    timestamp: float


class PrometheusMetrics:
    def __init__(self, prefix: str = "rag_agent"):
        if not PROMETHEUS_AVAILABLE:
            self._enabled = False
            return

        self._enabled = True
        self.prefix = prefix

        self.requests_total = Counter(
            f"{prefix}_requests_total",
            "Total number of requests",
            ["endpoint", "method"]
        )

        self.request_duration = Histogram(
            f"{prefix}_request_duration_seconds",
            "Request duration in seconds",
            ["endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )

        self.active_sessions = Gauge(
            f"{prefix}_active_sessions",
            "Number of active sessions"
        )

        self.errors_total = Counter(
            f"{prefix}_errors_total",
            "Total number of errors",
            ["endpoint", "error_type"]
        )

        self.cpu_usage = Gauge(
            f"{prefix}_cpu_usage_percent",
            "CPU usage percentage"
        )

        self.memory_usage = Gauge(
            f"{prefix}_memory_usage_percent",
            "Memory usage percentage"
        )

        self.search_quality_score = Gauge(
            f"{prefix}_search_quality_score",
            "Search quality score (A/B test)",
            ["variant"]
        )

        self.cache_hits = Counter(
            f"{prefix}_cache_hits_total",
            "Total cache hits"
        )

        self.cache_misses = Counter(
            f"{prefix}_cache_misses_total",
            "Total cache misses"
        )

        self.tool_calls = Counter(
            f"{prefix}_tool_calls_total",
            "Total tool calls",
            ["tool_name"]
        )

    def record_request(self, endpoint: str, method: str, duration: float):
        if not self._enabled:
            return
        self.requests_total.labels(endpoint=endpoint, method=method).inc()
        self.request_duration.labels(endpoint=endpoint).observe(duration)

    def record_error(self, endpoint: str, error_type: str):
        if not self._enabled:
            return
        self.errors_total.labels(endpoint=endpoint, error_type=error_type).inc()

    def set_active_sessions(self, count: int):
        if not self._enabled:
            return
        self.active_sessions.set(count)

    def set_cpu_usage(self, percent: float):
        if not self._enabled:
            return
        self.cpu_usage.set(percent)

    def set_memory_usage(self, percent: float):
        if not self._enabled:
            return
        self.memory_usage.set(percent)

    def set_search_quality(self, variant: str, score: float):
        if not self._enabled:
            return
        self.search_quality_score.labels(variant=variant).set(score)

    def record_cache_hit(self):
        if not self._enabled:
            return
        self.cache_hits.inc()

    def record_cache_miss(self):
        if not self._enabled:
            return
        self.cache_misses.inc()

    def record_tool_call(self, tool_name: str):
        if not self._enabled:
            return
        self.tool_calls.labels(tool_name=tool_name).inc()

    def generate(self) -> bytes:
        if not self._enabled:
            return b""
        return generate_latest()


class ABTestTracker:
    def __init__(self):
        self._variants: Dict[str, Dict[str, int]] = {
            "control": {"impressions": 0, "clicks": 0, "conversions": 0},
            "treatment": {"impressions": 0, "clicks": 0, "conversions": 0}
        }
        self._scores: Dict[str, List[float]] = {
            "control": [],
            "treatment": []
        }
        self._lock = threading.Lock()

    def record_impression(self, variant: str):
        with self._lock:
            if variant in self._variants:
                self._variants[variant]["impressions"] += 1

    def record_click(self, variant: str):
        with self._lock:
            if variant in self._variants:
                self._variants[variant]["clicks"] += 1

    def record_conversion(self, variant: str):
        with self._lock:
            if variant in self._variants:
                self._variants[variant]["conversions"] += 1

    def record_score(self, variant: str, score: float):
        with self._lock:
            if variant in self._scores:
                self._scores[variant].append(score)

    def get_stats(self, variant: str) -> Dict[str, Any]:
        with self._lock:
            stats = self._variants.get(variant, {"impressions": 0, "clicks": 0, "conversions": 0})
            scores = self._scores.get(variant, [])

            ctr = stats["clicks"] / max(stats["impressions"], 1)
            conversion_rate = stats["conversions"] / max(stats["clicks"], 1)
            avg_score = sum(scores) / max(len(scores), 1)

            return {
                "variant": variant,
                "impressions": stats["impressions"],
                "clicks": stats["clicks"],
                "conversions": stats["conversions"],
                "ctr": round(ctr, 4),
                "conversion_rate": round(conversion_rate, 4),
                "avg_score": round(avg_score, 4),
                "sample_size": len(scores)
            }

    def get_comparison(self) -> Dict[str, Any]:
        control = self.get_stats("control")
        treatment = self.get_stats("treatment")

        score_diff = treatment["avg_score"] - control["avg_score"]
        score_diff_pct = score_diff / max(control["avg_score"], 0.001) * 100

        return {
            "control": control,
            "treatment": treatment,
            "score_difference": round(score_diff, 4),
            "score_difference_percent": round(score_diff_pct, 2),
            "recommendation": "treatment" if score_diff > 0 else "control"
        }

    def reset(self):
        with self._lock:
            for variant in self._variants:
                self._variants[variant] = {"impressions": 0, "clicks": 0, "conversions": 0}
                self._scores[variant] = []


class AdaptiveWeightTuner:
    def __init__(
        self,
        initial_vector_weight: float = 0.7,
        initial_bm25_weight: float = 0.3,
        learning_rate: float = 0.1
    ):
        self.vector_weight = initial_vector_weight
        self.bm25_weight = initial_bm25_weight
        self.learning_rate = learning_rate
        self._feedback_history: List[Dict[str, float]] = []
        self._lock = threading.Lock()

    def record_feedback(
        self,
        query: str,
        vector_score: float,
        bm25_score: float,
        user_rating: float
    ) -> None:
        with self._lock:
            self._feedback_history.append({
                "query": query,
                "vector_score": vector_score,
                "bm25_score": bm25_score,
                "user_rating": user_rating,
                "timestamp": time.time()
            })

            if len(self._feedback_history) >= 10:
                self._adjust_weights()

    def _adjust_weights(self) -> None:
        recent = self._feedback_history[-50:]

        vector_better = sum(
            1 for f in recent if abs(f["user_rating"] - f["vector_score"]) < abs(f["user_rating"] - f["bm25_score"])
        )
        bm25_better = len(recent) - vector_better

        if vector_better > bm25_better:
            adjustment = self.learning_rate * 0.1
            self.vector_weight = min(0.95, self.vector_weight + adjustment)
            self.bm25_weight = 1.0 - self.vector_weight
        elif bm25_better > vector_better:
            adjustment = self.learning_rate * 0.1
            self.bm25_weight = min(0.95, self.bm25_weight + adjustment)
            self.vector_weight = 1.0 - self.bm25_weight

        self._feedback_history.clear()

    def get_weights(self) -> Dict[str, float]:
        return {
            "vector_weight": round(self.vector_weight, 4),
            "bm25_weight": round(self.bm25_weight, 4)
        }

    def reset(self) -> None:
        with self._lock:
            self.vector_weight = 0.7
            self.bm25_weight = 0.3
            self._feedback_history.clear()


class AlertManager:
    def __init__(self):
        self._rules: List[AlertRule] = []
        self._alerts: List[Alert] = []
        self._handlers: List[Callable[[Alert], None]] = []
        self._lock = threading.Lock()

    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def remove_rule(self, rule_name: str) -> bool:
        with self._lock:
            for i, rule in enumerate(self._rules):
                if rule.name == rule_name:
                    del self._rules[i]
                    return True
            return False

    def check_metrics(self, metrics: MonitorMetrics) -> List[Alert]:
        new_alerts = []
        with self._lock:
            for rule in self._rules:
                if not rule.enabled:
                    continue

                value = getattr(metrics, rule.metric, 0)
                triggered = False

                if rule.comparison == "gt" and value > rule.threshold:
                    triggered = True
                elif rule.comparison == "lt" and value < rule.threshold:
                    triggered = True
                elif rule.comparison == "eq" and value == rule.threshold:
                    triggered = True

                if triggered:
                    alert = Alert(
                        rule_name=rule.name,
                        level=rule.level,
                        message=f"{rule.name}: {rule.metric}={value} (threshold={rule.threshold})",
                        metric_value=value,
                        threshold=rule.threshold,
                        timestamp=time.time()
                    )
                    new_alerts.append(alert)
                    self._alerts.append(alert)

        for alert in new_alerts:
            for handler in self._handlers:
                try:
                    handler(alert)
                except Exception:
                    pass

        return new_alerts

    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        with self._lock:
            if level:
                return [a for a in self._alerts if a.level == level]
            return list(self._alerts)

    def clear_alerts(self) -> None:
        with self._lock:
            self._alerts.clear()

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)


class PerformanceMonitor:
    _instance: Optional["PerformanceMonitor"] = None
    _lock_class: threading.RLock = threading.RLock()

    def __new__(cls) -> "PerformanceMonitor":
        if cls._instance is None:
            with cls._lock_class:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._request_times: deque = deque(maxlen=1000)
        self._error_count: int = 0
        self._total_requests: int = 0
        self._tool_calls: int = 0
        self._skill_calls: int = 0
        self._sessions: Dict[str, float] = {}
        self._start_time: float = time.time()
        self._lock: threading.Lock = threading.Lock()
        self._monitoring: bool = False
        self._monitor_thread: Optional[threading.Thread] = None

        self._prometheus = PrometheusMetrics()
        self._ab_tracker = ABTestTracker()
        self._weight_tuner = AdaptiveWeightTuner()
        self._alert_manager = AlertManager()

        self._setup_default_alert_rules()

    def _setup_default_alert_rules(self) -> None:
        self._alert_manager.add_rule(AlertRule(
            name="HighCPU",
            metric="cpu_percent",
            threshold=80.0,
            comparison="gt",
            level=AlertLevel.WARNING
        ))
        self._alert_manager.add_rule(AlertRule(
            name="HighMemory",
            metric="memory_percent",
            threshold=85.0,
            comparison="gt",
            level=AlertLevel.WARNING
        ))
        self._alert_manager.add_rule(AlertRule(
            name="HighErrorRate",
            metric="error_rate",
            threshold=0.1,
            comparison="gt",
            level=AlertLevel.ERROR
        ))
        self._alert_manager.add_rule(AlertRule(
            name="SlowResponse",
            metric="avg_response_time",
            threshold=10.0,
            comparison="gt",
            level=AlertLevel.WARNING
        ))

    def start_monitoring(self, interval: int = 30) -> None:
        if self._monitoring:
            return

        self._monitoring = True

        def _monitor_loop() -> None:
            while self._monitoring:
                self._cleanup_stale_sessions()
                self._update_system_metrics()
                time.sleep(interval)

        self._monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

    def _update_system_metrics(self) -> None:
        metrics = self.get_current_metrics()
        self._prometheus.set_cpu_usage(metrics.cpu_percent)
        self._prometheus.set_memory_usage(metrics.memory_percent)
        self._alert_manager.check_metrics(metrics)

    def _cleanup_stale_sessions(self, timeout: float = 3600.0) -> None:
        current_time: float = time.time()
        with self._lock:
            stale: List[str] = [
                sid for sid, last_active in self._sessions.items()
                if current_time - last_active > timeout
            ]
            for sid in stale:
                del self._sessions[sid]

    def record_request(
        self,
        session_id: str,
        response_time: float,
        has_error: bool = False,
        tools_used: int = 0,
        skills_used: int = 0
    ) -> None:
        with self._lock:
            self._request_times.append(response_time)
            self._total_requests += 1
            self._sessions[session_id] = time.time()

            if has_error:
                self._error_count += 1

            self._tool_calls += tools_used
            self._skill_calls += skills_used

        self._prometheus.record_request("chat", "POST", response_time)

    def record_search(
        self,
        variant: str,
        query: str,
        result_count: int,
        user_feedback: Optional[float] = None
    ) -> None:
        self._ab_tracker.record_impression(variant)
        if result_count > 0:
            self._ab_tracker.record_click(variant)
        if user_feedback is not None:
            self._ab_tracker.record_score(variant, user_feedback)

    def record_cache_hit(self) -> None:
        self._prometheus.record_cache_hit()

    def record_cache_miss(self) -> None:
        self._prometheus.record_cache_miss()

    def record_tool_call(self, tool_name: str) -> None:
        self._prometheus.record_tool_call(tool_name)

    def get_current_metrics(self) -> MonitorMetrics:
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent(interval=0.1)

        system_memory = psutil.virtual_memory()

        with self._lock:
            active_sessions = len(self._sessions)
            total_requests = self._total_requests
            error_count = self._error_count

            if self._request_times:
                avg_response_time = sum(self._request_times) / len(self._request_times)
            else:
                avg_response_time = 0.0

            error_rate = error_count / max(1, total_requests)

        return MonitorMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=system_memory.percent,
            memory_used_mb=memory_info.rss / 1024 / 1024,
            active_sessions=active_sessions,
            total_requests=total_requests,
            avg_response_time=avg_response_time,
            error_rate=error_rate,
            tool_call_count=self._tool_calls,
            skill_call_count=self._skill_calls
        )

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            last_active = self._sessions.get(session_id, 0.0)

        return {
            "session_id": session_id,
            "last_active": datetime.fromtimestamp(last_active).isoformat() if last_active else None,
            "is_active": session_id in self._sessions
        }

    def get_stats_summary(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time

        with self._lock:
            total = self._total_requests
            errors = self._error_count

        return {
            "uptime_seconds": round(uptime, 2),
            "uptime_hours": round(uptime / 3600, 2),
            "total_requests": total,
            "total_errors": errors,
            "error_rate_percent": round(errors / max(1, total) * 100, 2),
            "active_sessions": len(self._sessions),
            "total_tool_calls": self._tool_calls,
            "total_skill_calls": self._skill_calls,
            "requests_per_minute": round(total / max(1, uptime / 60), 2)
        }

    def get_ab_test_results(self) -> Dict[str, Any]:
        return self._ab_tracker.get_comparison()

    def get_adaptive_weights(self) -> Dict[str, float]:
        return self._weight_tuner.get_weights()

    def record_weight_feedback(
        self,
        query: str,
        vector_score: float,
        bm25_score: float,
        user_rating: float
    ) -> None:
        self._weight_tuner.record_feedback(query, vector_score, bm25_score, user_rating)

    def get_active_alerts(self, level: Optional[str] = None) -> List[Dict[str, Any]]:
        alert_level = AlertLevel[level.upper()] if level else None
        alerts = self._alert_manager.get_active_alerts(alert_level)
        return [
            {
                "rule_name": a.rule_name,
                "level": a.level.value,
                "message": a.message,
                "metric_value": a.metric_value,
                "threshold": a.threshold,
                "timestamp": datetime.fromtimestamp(a.timestamp).isoformat()
            }
            for a in alerts
        ]

    def get_prometheus_metrics(self) -> bytes:
        return self._prometheus.generate()

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        self._alert_manager.add_handler(handler)

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock_class:
            cls._instance = None


class HealthChecker:
    def __init__(self, monitor: PerformanceMonitor) -> None:
        self.monitor: PerformanceMonitor = monitor

    def check_health(self) -> Dict[str, Any]:
        metrics = self.monitor.get_current_metrics()

        issues: List[str] = []
        health_status = "healthy"

        if metrics.cpu_percent > 80:
            issues.append("High CPU usage")
            health_status = "degraded"

        if metrics.memory_percent > 85:
            issues.append("High memory usage")
            health_status = "degraded"

        if metrics.error_rate > 0.1:
            issues.append("High error rate")
            health_status = "unhealthy"

        if metrics.avg_response_time > 10:
            issues.append("Slow response times")
            if health_status == "healthy":
                health_status = "degraded"

        return {
            "status": health_status,
            "issues": issues,
            "metrics": metrics.to_dict(),
            "timestamp": datetime.now().isoformat()
        }

    def is_healthy(self) -> bool:
        health = self.check_health()
        return health["status"] in ("healthy", "degraded")

    def get_load_level(self) -> str:
        metrics = self.monitor.get_current_metrics()

        if metrics.cpu_percent > 90 or metrics.memory_percent > 90:
            return "high"
        elif metrics.cpu_percent > 70 or metrics.memory_percent > 75:
            return "medium"
        else:
            return "low"
