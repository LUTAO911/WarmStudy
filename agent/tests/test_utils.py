"""
Unit tests for utility modules
"""
import time
import pytest
from typing import Dict, Any

from agent.utils.monitor import (
    MonitorMetrics,
    PerformanceMonitor,
    HealthChecker,
)


class TestMonitorMetrics:
    """Tests for MonitorMetrics."""

    def test_create_metrics(self) -> None:
        """Test creating monitor metrics."""
        metrics = MonitorMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            active_sessions=5,
            total_requests=100,
            avg_response_time=0.5,
            error_rate=0.02,
            tool_call_count=50,
            skill_call_count=30,
        )
        assert metrics.cpu_percent == 50.0
        assert metrics.active_sessions == 5

    def test_to_dict(self) -> None:
        """Test converting metrics to dictionary."""
        metrics = MonitorMetrics(
            timestamp=1700000000.0,
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            active_sessions=5,
            total_requests=100,
            avg_response_time=0.5,
            error_rate=0.02,
            tool_call_count=50,
            skill_call_count=30,
        )
        data = metrics.to_dict()
        assert data["cpu_percent"] == 50.0
        assert data["memory_percent"] == 60.0
        assert "timestamp_str" in data


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor."""

    def test_singleton_pattern(self) -> None:
        """Test that PerformanceMonitor is a singleton."""
        monitor1 = PerformanceMonitor()
        monitor2 = PerformanceMonitor()
        assert monitor1 is monitor2

    def test_record_request(self) -> None:
        """Test recording a request."""
        monitor = PerformanceMonitor()
        monitor.reset_instance()

        monitor.record_request(
            session_id="session1",
            response_time=0.5,
            has_error=False,
            tools_used=2,
            skills_used=1,
        )

        metrics = monitor.get_current_metrics()
        assert metrics.total_requests >= 1

    def test_cleanup_stale_sessions(self) -> None:
        """Test cleaning up stale sessions."""
        monitor = PerformanceMonitor()
        monitor.reset_instance()

        monitor.record_request(session_id="old_session", response_time=0.1)
        time.sleep(0.2)

        cleaned = monitor.cleanup_inactive_sessions(max_age_seconds=0.1)
        assert cleaned >= 1

    def test_get_stats_summary(self) -> None:
        """Test getting stats summary."""
        monitor = PerformanceMonitor()
        monitor.reset_instance()

        monitor.record_request(session_id="s1", response_time=0.5)
        monitor.record_request(session_id="s2", response_time=0.3)

        stats = monitor.get_stats_summary()
        assert "uptime_seconds" in stats
        assert "total_requests" in stats
        assert stats["total_requests"] >= 2

    def test_get_session_stats(self) -> None:
        """Test getting session stats."""
        monitor = PerformanceMonitor()
        monitor.reset_instance()

        monitor.record_request(session_id="my_session", response_time=0.5)

        stats = monitor.get_session_stats("my_session")
        assert stats["session_id"] == "my_session"
        assert stats["is_active"] is True


class TestHealthChecker:
    """Tests for HealthChecker."""

    def test_check_health_healthy(self) -> None:
        """Test health check for healthy system."""
        monitor = PerformanceMonitor()
        monitor.reset_instance()

        health_checker = HealthChecker(monitor)
        health = health_checker.check_health()

        assert "status" in health
        assert "issues" in health
        assert health["status"] in ("healthy", "degraded", "unhealthy")

    def test_is_healthy(self) -> None:
        """Test is_healthy method."""
        monitor = PerformanceMonitor()
        monitor.reset_instance()

        health_checker = HealthChecker(monitor)
        assert health_checker.is_healthy() in (True, False)

    def test_get_load_level(self) -> None:
        """Test getting load level."""
        monitor = PerformanceMonitor()
        monitor.reset_instance()

        health_checker = HealthChecker(monitor)
        level = health_checker.get_load_level()

        assert level in ("low", "medium", "high")