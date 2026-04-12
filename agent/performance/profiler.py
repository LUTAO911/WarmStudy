"""
Performance Profiler - 性能分析器
函数级性能分析和瓶颈识别
版本: v5.0
"""
import time
import functools
import threading
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from contextlib import contextmanager

# ========== 性能数据 ==========

@dataclass
class ProfileRecord:
    """性能记录"""
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    last_called: float = 0.0

    def update(self, elapsed: float) -> None:
        self.call_count += 1
        self.total_time += elapsed
        self.min_time = min(self.min_time, elapsed)
        self.max_time = max(self.max_time, elapsed)
        self.avg_time = self.total_time / self.call_count
        self.last_called = time.time()


@dataclass
class ProfilerStats:
    """分析器统计"""
    records: Dict[str, ProfileRecord] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records": {
                name: {
                    "call_count": r.call_count,
                    "total_time": round(r.total_time, 4),
                    "min_time": round(r.min_time, 4),
                    "max_time": round(r.max_time, 4),
                    "avg_time": round(r.avg_time, 4),
                    "last_called": r.last_called,
                }
                for name, r in self.records.items()
            },
            "start_time": self.start_time,
            "uptime": time.time() - self.start_time,
        }


# ========== 函数装饰器 ==========

def profile(func: Callable) -> Callable:
    """
    性能分析装饰器

    使用方法:
        @profile
        def my_function():
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            _profiler_global.record(func.__name__, elapsed)

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            _profiler_global.record(func.__name__, elapsed)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return wrapper


# ========== 全局分析器 ==========

_profiler_global: Optional["Profiler"] = None


def get_profiler() -> "Profiler":
    """获取全局分析器"""
    global _profiler_global
    if _profiler_global is None:
        _profiler_global = Profiler()
    return _profiler_global


# ========== Profiler 类 ==========

class Profiler:
    """
    性能分析器

    功能：
    1. 函数级性能追踪
    2. 调用链分析
    3. 瓶颈识别
    4. 报告生成

    使用方法:
        profiler = Profiler()

        with profiler.profile("my_operation"):
            # 执行操作
            pass

        stats = profiler.get_stats()
        bottlenecks = profiler.find_bottlenecks()
    """

    def __init__(self):
        self._stats = ProfilerStats()
        self._enabled = True
        self._call_stack: List[str] = []
        self._context = threading.local()

    def record(self, func_name: str, elapsed: float) -> None:
        """记录函数执行"""
        if not self._enabled:
            return

        with self._stats.lock:
            if func_name not in self._stats.records:
                self._stats.records[func_name] = ProfileRecord(
                    function_name=func_name
                )

            self._stats.records[func_name].update(elapsed)

    @contextmanager
    def profile(self, name: str):
        """
        上下文管理器方式的性能分析

        使用方法:
            with profiler.profile("my_operation"):
                # 执行操作
                pass
        """
        start = time.perf_counter()
        self._call_stack.append(name)

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self._call_stack.pop()
            self.record(name, elapsed)

    def enable(self) -> None:
        """启用分析"""
        self._enabled = True

    def disable(self) -> None:
        """禁用分析"""
        self._enabled = False

    def reset(self) -> None:
        """重置统计数据"""
        with self._stats.lock:
            self._stats.records.clear()
            self._stats.start_time = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.to_dict()

    def find_bottlenecks(self, min_calls: int = 5, min_avg_ms: float = 10.0) -> List[Dict[str, Any]]:
        """
        查找性能瓶颈

        Args:
            min_calls: 最少调用次数
            min_avg_ms: 最小平均耗时（毫秒）

        Returns:
            List[Dict]: 瓶颈函数列表
        """
        bottlenecks = []

        for name, record in self._stats.records.items():
            if record.call_count < min_calls:
                continue

            avg_ms = record.avg_time * 1000
            if avg_ms < min_avg_ms:
                continue

            bottlenecks.append({
                "function": name,
                "call_count": record.call_count,
                "total_time_ms": record.total_time * 1000,
                "avg_time_ms": avg_ms,
                "max_time_ms": record.max_time * 1000,
                "suggestion": self._suggest_fix(name, record),
            })

        # 按平均耗时排序
        bottlenecks.sort(key=lambda x: x["avg_time_ms"], reverse=True)

        return bottlenecks

    def _suggest_fix(self, func_name: str, record: ProfileRecord) -> str:
        """根据函数名给出优化建议"""
        avg_ms = record.avg_time * 1000

        if "detect" in func_name.lower():
            if avg_ms > 50:
                return "考虑添加缓存，减少重复检测"
            return "性能可接受"

        elif "rag" in func_name.lower() or "retrieve" in func_name.lower():
            if avg_ms > 100:
                return "考虑启用查询缓存，或优化检索策略"
            return "性能可接受"

        elif "embedding" in func_name.lower():
            if avg_ms > 200:
                return "考虑批量处理嵌入请求"
            return "性能可接受"

        elif "llm" in func_name.lower() or "generate" in func_name.lower():
            if avg_ms > 500:
                return "LLM调用耗时较高，考虑添加响应缓存"
            return "性能可接受"

        return "继续观察"

    def print_report(self) -> None:
        """打印性能报告"""
        print()
        print("=" * 60)
        print(" 性能分析报告")
        print("=" * 60)

        stats = self._stats.to_dict()

        print(f"\n运行时间: {stats['uptime']:.2f}s")
        print(f"已追踪函数: {len(stats['records'])}")

        # 耗时排行
        print("\n耗时排行 (Top 10):")
        print("-" * 60)

        sorted_records = sorted(
            stats["records"].items(),
            key=lambda x: x[1]["total_time"],
            reverse=True
        )[:10]

        print(f"{'函数':<30} {'调用次数':>8} {'总耗时':>10} {'平均':>10} {'最大':>10}")
        print("-" * 60)

        for name, record in sorted_records:
            total_ms = record["total_time"] * 1000
            avg_ms = record["avg_time"] * 1000
            max_ms = record["max_time"] * 1000
            print(f"{name:<30} {record['call_count']:>8} {total_ms:>9.2f}ms {avg_ms:>9.2f}ms {max_ms:>9.2f}ms")

        # 瓶颈分析
        print("\n瓶颈分析:")
        print("-" * 60)

        bottlenecks = self.find_bottlenecks()
        if not bottlenecks:
            print("  未发现明显瓶颈")
        else:
            for i, b in enumerate(bottlenecks, 1):
                print(f"\n{i}. {b['function']}")
                print(f"   调用次数: {b['call_count']}, 平均: {b['avg_time_ms']:.2f}ms")
                print(f"   建议: {b['suggestion']}")

        print()


# ========== 内存分析 ==========

class MemoryProfiler:
    """
    内存分析器

    功能：
    1. 内存使用追踪
    2. 大对象识别
    3. 内存泄漏检测
    """

    def __init__(self):
        self._snapshots: List[Dict[str, Any]] = []
        self._start_memory = self._get_memory_usage()

    def _get_memory_usage(self) -> Dict[str, Any]:
        """获取当前内存使用"""
        try:
            import psutil
            process = psutil.Process()
            return {
                "rss": process.memory_info().rss,
                "vms": process.memory_info().vms,
            }
        except ImportError:
            return {"rss": 0, "vms": 0}

    def take_snapshot(self, label: str = "") -> Dict[str, Any]:
        """拍摄内存快照"""
        import os

        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()

            snapshot = {
                "label": label,
                "timestamp": time.time(),
                "rss": mem_info.rss,
                "vms": mem_info.vms,
                "rss_mb": mem_info.rss / (1024 * 1024),
            }
        except ImportError:
            snapshot = {
                "label": label,
                "timestamp": time.time(),
                "rss": 0,
                "vms": 0,
                "rss_mb": 0,
            }

        self._snapshots.append(snapshot)
        return snapshot

    def get_memory_delta(self) -> Dict[str, Any]:
        """获取内存变化"""
        if len(self._snapshots) < 2:
            return {"delta_rss": 0, "delta_vms": 0}

        first = self._snapshots[0]
        last = self._snapshots[-1]

        return {
            "delta_rss": last["rss"] - first["rss"],
            "delta_vms": last["vms"] - first["vms"],
            "delta_rss_mb": (last["rss"] - first["rss"]) / (1024 * 1024),
        }

    def report(self) -> str:
        """生成内存报告"""
        output = []
        output.append("\n" + "=" * 60)
        output.append(" 内存分析报告")
        output.append("=" * 60)

        if self._snapshots:
            delta = self.get_memory_delta()
            output.append(f"\n初始内存: {self._snapshots[0].get('rss_mb', 0):.2f} MB")
            output.append(f"当前内存: {self._snapshots[-1].get('rss_mb', 0):.2f} MB")
            output.append(f"内存增长: {delta['delta_rss_mb']:.2f} MB")
        else:
            output.append("\n无可用数据")

        return "\n".join(output)


# ========== asyncio兼容 ==========

import asyncio


# ========== 便捷函数 ==========

@contextmanager
def profile_block(name: str):
    """便捷的性能分析上下文管理器"""
    profiler = get_profiler()
    with profiler.profile(name):
        yield


def print_bottlenecks():
    """打印当前瓶颈"""
    profiler = get_profiler()
    profiler.print_report()
