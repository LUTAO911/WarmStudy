"""
Performance Module - 性能测试与监控模块
"""
from .benchmark import (
    BenchmarkRunner,
    BenchmarkResult,
    BenchmarkSuite,
    NuanxueBenchmarkSuite,
    main as run_benchmark,
)

from .profiler import (
    Profiler,
    ProfileRecord,
    ProfilerStats,
    MemoryProfiler,
    profile,
    profile_block,
    get_profiler,
    print_bottlenecks,
)

from .monitor import (
    RuntimeMonitor,
    MetricType,
    MetricSample,
    MetricWindow,
    AlertRule,
    get_monitor,
    record_metric,
    increment_counter,
    set_gauge,
    get_health,
    print_monitor_report,
)

__all__ = [
    # Benchmark
    "BenchmarkRunner",
    "BenchmarkResult",
    "BenchmarkSuite",
    "NuanxueBenchmarkSuite",
    "run_benchmark",
    # Profiler
    "Profiler",
    "ProfileRecord",
    "ProfilerStats",
    "MemoryProfiler",
    "profile",
    "profile_block",
    "get_profiler",
    "print_bottlenecks",
    # Monitor
    "RuntimeMonitor",
    "MetricType",
    "MetricSample",
    "MetricWindow",
    "AlertRule",
    "get_monitor",
    "record_metric",
    "increment_counter",
    "set_gauge",
    "get_health",
    "print_monitor_report",
]
