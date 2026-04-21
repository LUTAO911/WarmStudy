"""
Performance Benchmark - 性能基准测试
测试各模块响应时间和吞吐量
版本: v5.0
"""
import time
import asyncio
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json

# ========== 基准测试结果 ==========

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    operation: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    throughput: float  # ops/second
    p50: float
    p95: float
    p99: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "operation": self.operation,
            "iterations": self.iterations,
            "total_time": round(self.total_time, 4),
            "avg_time": round(self.avg_time, 4),
            "min_time": round(self.min_time, 4),
            "max_time": round(self.max_time, 4),
            "std_dev": round(self.std_dev, 4),
            "throughput": round(self.throughput, 2),
            "p50": round(self.p50, 4),
            "p95": round(self.p95, 4),
            "p99": round(self.p99, 4),
            "timestamp": self.timestamp,
        }


@dataclass
class BenchmarkSuite:
    """基准测试套件"""
    name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def add_result(self, result: BenchmarkResult) -> None:
        self.results.append(result)

    def summary(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_tests": len(self.results),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": (self.completed_at or time.time()) - self.started_at,
            "results": [r.to_dict() for r in self.results],
        }


# ========== 基准测试运行器 ==========

class BenchmarkRunner:
    """
    基准测试运行器

    使用方法:
        runner = BenchmarkRunner()
        result = runner.run(
            name="RAG检索",
            operation=lambda: rag.retrieve(query),
            iterations=100,
            warmup=10
        )
    """

    def __init__(self, warmup: int = 5):
        self.warmup = warmup

    def run(
        self,
        name: str,
        operation: Callable,
        iterations: int = 100,
        warmup: Optional[int] = None,
        async_op: bool = False
    ) -> BenchmarkResult:
        """
        运行基准测试

        Args:
            name: 测试名称
            operation: 要测试的操作
            iterations: 迭代次数
            warmup: 预热次数
            async_op: 是否是异步操作

        Returns:
            BenchmarkResult: 测试结果
        """
        warmup_count = warmup if warmup is not None else self.warmup
        times: List[float] = []

        # 预热
        for _ in range(warmup_count):
            if async_op:
                asyncio.run(operation())
            else:
                operation()

        # 正式测试
        start_time = time.perf_counter()

        for _ in range(iterations):
            iter_start = time.perf_counter()

            if async_op:
                asyncio.run(operation())
            else:
                operation()

            iter_time = time.perf_counter() - iter_start
            times.append(iter_time)

        total_time = time.perf_counter() - start_time

        # 计算统计
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        # 计算百分位数
        sorted_times = sorted(times)
        p50_idx = int(len(sorted_times) * 0.50)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)

        p50 = sorted_times[p50_idx] if sorted_times else 0
        p95 = sorted_times[p95_idx] if sorted_times else 0
        p99 = sorted_times[p99_idx] if sorted_times else 0

        throughput = iterations / total_time if total_time > 0 else 0

        return BenchmarkResult(
            name=name,
            operation=name,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            std_dev=std_dev,
            throughput=throughput,
            p50=p50,
            p95=p95,
            p99=p99
        )

    async def run_async(
        self,
        name: str,
        operation: Callable,
        iterations: int = 100,
        warmup: Optional[int] = None,
        concurrency: int = 1
    ) -> BenchmarkResult:
        """
        运行异步基准测试

        Args:
            name: 测试名称
            operation: 异步操作
            iterations: 迭代次数
            warmup: 预热次数
            concurrency: 并发数

        Returns:
            BenchmarkResult: 测试结果
        """
        warmup_count = warmup if warmup is not None else self.warmup

        # 预热
        for _ in range(warmup_count):
            await operation()

        # 正式测试
        start_time = time.perf_counter()

        if concurrency == 1:
            # 串行
            times = []
            for _ in range(iterations):
                iter_start = time.perf_counter()
                await operation()
                times.append(time.perf_counter() - iter_start)
        else:
            # 并发
            import asyncio

            async def timed_op():
                iter_start = time.perf_counter()
                await operation()
                return time.perf_counter() - iter_start

            # 分批并发
            times = []
            for batch_start in range(0, iterations, concurrency):
                batch_end = min(batch_start + concurrency, iterations)
                batch_times = await asyncio.gather(
                    *[timed_op() for _ in range(batch_end - batch_start)]
                )
                times.extend(batch_times)

        total_time = time.perf_counter() - start_time

        # 计算统计
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        # 百分位数
        sorted_times = sorted(times)
        p50 = sorted_times[int(len(sorted_times) * 0.50)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]

        throughput = iterations / total_time if total_time > 0 else 0

        return BenchmarkResult(
            name=name,
            operation=name,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            std_dev=std_dev,
            throughput=throughput,
            p50=p50,
            p95=p95,
            p99=p99
        )


# ========== 预设基准测试 ==========

class NuanxueBenchmarkSuite:
    """
    暖学帮预设基准测试套件

    测试场景：
    1. 情绪识别延迟
    2. 危机检测延迟
    3. RAG检索延迟
    4. 工具选择延迟
    5. 工作流执行延迟
    6. 记忆读写延迟
    """

    def __init__(self):
        self.runner = BenchmarkRunner(warmup=5)
        self.results: List[BenchmarkResult] = []

    async def run_all(self) -> BenchmarkSuite:
        """运行所有基准测试"""
        suite = BenchmarkSuite(name="暖学帮性能基准测试")

        print("[Benchmark] Starting performance tests...")

        # 1. 情绪识别
        try:
            result = await self._benchmark_emotion_detect()
            suite.add_result(result)
            print(f"  [OK] Emotion Detect: {result.avg_time*1000:.2f}ms avg")
        except Exception as e:
            print(f"  [FAIL] Emotion Detect: {e}")

        # 2. 危机检测
        try:
            result = await self._benchmark_crisis_detect()
            suite.add_result(result)
            print(f"  [OK] Crisis Detect: {result.avg_time*1000:.2f}ms avg")
        except Exception as e:
            print(f"  [FAIL] Crisis Detect: {e}")

        # 3. 意图路由
        try:
            result = await self._benchmark_intent_routing()
            suite.add_result(result)
            print(f"  [OK] Intent Routing: {result.avg_time*1000:.2f}ms avg")
        except Exception as e:
            print(f"  [FAIL] Intent Routing: {e}")

        # 4. 工具选择
        try:
            result = await self._benchmark_tool_selection()
            suite.add_result(result)
            print(f"  [OK] Tool Selection: {result.avg_time*1000:.2f}ms avg")
        except Exception as e:
            print(f"  [FAIL] Tool Selection: {e}")

        # 5. 记忆操作
        try:
            result = await self._benchmark_memory_ops()
            suite.add_result(result)
            print(f"  [OK] Memory Ops: {result.avg_time*1000:.2f}ms avg")
        except Exception as e:
            print(f"  [FAIL] Memory Ops: {e}")

        # 6. 缓存操作
        try:
            result = await self._benchmark_cache()
            suite.add_result(result)
            print(f"  [OK] Cache Ops: {result.avg_time*1000:.2f}ms avg")
        except Exception as e:
            print(f"  [FAIL] Cache Ops: {e}")

        suite.completed_at = time.time()
        self.results = suite.results

        print(f"[Benchmark] Completed {len(suite.results)} tests in {suite.summary()['duration']:.2f}s")

        return suite

    async def _benchmark_emotion_detect(self) -> BenchmarkResult:
        """基准测试：情绪识别"""
        from agent.modules.psychology.emotion import EmotionDetector
        detector = EmotionDetector()
        test_text = "我今天考试考砸了，心情很糟糕，不想说话了"

        return await self.runner.run_async(
            name="Emotion Detection",
            operation=lambda: detector.detect(test_text),
            iterations=50
        )

    async def _benchmark_crisis_detect(self) -> BenchmarkResult:
        """基准测试：危机检测"""
        from agent.modules.psychology.crisis import CrisisDetector
        detector = CrisisDetector()
        test_text = "我觉得活着没意思，不想活了"

        return await self.runner.run_async(
            name="Crisis Detection",
            operation=lambda: detector.check(test_text),
            iterations=50
        )

    async def _benchmark_intent_routing(self) -> BenchmarkResult:
        """基准测试：意图路由"""
        from agent.core.intent_router import IntentRouter
        router = IntentRouter()

        test_messages = [
            "我最近压力很大",
            "今天天气怎么样",
            "帮我查一下勾股定理",
            "我想找个心理咨询师",
        ]

        return await self.runner.run_async(
            name="Intent Routing",
            operation=lambda: router.route(test_messages[0]),
            iterations=50
        )

    async def _benchmark_tool_selection(self) -> BenchmarkResult:
        """基准测试：工具选择"""
        from agent.tools.tool_selector import ToolSelector
        selector = ToolSelector()

        test_message = "我考试没考好，心情很差"

        return await self.runner.run_async(
            name="Tool Selection",
            operation=lambda: selector.select_tools(test_message),
            iterations=50
        )

    async def _benchmark_memory_ops(self) -> BenchmarkResult:
        """基准测试：记忆操作"""
        from agent.memory_store.unified_memory import UnifiedMemoryManager
        memory = UnifiedMemoryManager(persist_dir="data/test/memory")
        user_id = "benchmark_user"
        session_id = "benchmark_session"

        # 写入
        memory.add_dialogue(session_id, "user", "测试消息")
        memory.add_emotion_record(user_id, "neutral", 0.5)

        return await self.runner.run_async(
            name="Memory Operations",
            operation=lambda: (
                memory.add_dialogue(session_id, "user", "测试消息"),
                memory.get_dialogue_history(session_id),
                memory.add_emotion_record(user_id, "neutral", 0.5),
                memory.get_emotion_trends(user_id)
            ),
            iterations=50
        )

    async def _benchmark_cache(self) -> BenchmarkResult:
        """基准测试：缓存操作"""
        from agent.rag.cache_manager import MultiLevelCache
        cache = MultiLevelCache(l3_enabled=False)

        return await self.runner.run_async(
            name="Cache Operations",
            operation=lambda: (
                cache.set(f"key_{time.time()}", "value"),
                cache.get("key_0"),
                cache.delete(f"key_{time.time()}")
            ),
            iterations=100
        )

    def report(self) -> Dict[str, Any]:
        """生成测试报告"""
        if not self.results:
            return {"error": "No benchmark results"}

        report = {
            "title": "暖学帮性能基准测试报告",
            "generated_at": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total_tests": len(self.results),
                "total_throughput": sum(r.throughput for r in self.results),
            }
        }

        for result in self.results:
            report["tests"].append(result.to_dict())

        return report


# ========== 入口点 ==========

async def main():
    """运行基准测试"""
    print("=" * 60)
    print(" 暖学帮性能基准测试 v5.0")
    print("=" * 60)
    print()

    suite_runner = NuanxueBenchmarkSuite()
    suite = await suite_runner.run_all()

    print()
    print("=" * 60)
    print(" 测试报告")
    print("=" * 60)

    report = suite_runner.report()
    print(json.dumps(report, indent=2, ensure_ascii=False))

    # 保存报告
    report_path = "data/benchmark_report.json"
    import os
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n报告已保存到: {report_path}")

    return suite


if __name__ == "__main__":
    asyncio.run(main())
