"""性能优化模块 - 提升系统响应速度和稳定性"""
import asyncio
import time
import functools
from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic
from functools import lru_cache
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')


class ClientPool(Generic[T]):
    """客户端池化管理"""

    def __init__(self, client_factory: Callable[[], T], pool_size: int = 5):
        """
        初始化客户端池
        
        Args:
            client_factory: 创建客户端实例的函数
            pool_size: 池大小
        """
        self.client_factory = client_factory
        self.pool_size = pool_size
        self.pool = []
        self.semaphore = asyncio.Semaphore(pool_size)
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化客户端池"""
        for _ in range(self.pool_size):
            try:
                client = self.client_factory()
                self.pool.append(client)
            except Exception:
                pass

    async def get_client(self) -> T:
        """获取客户端实例"""
        async with self.semaphore:
            if not self.pool:
                # 如果池为空，创建新实例
                try:
                    return self.client_factory()
                except Exception:
                    raise RuntimeError("无法创建客户端实例")
            return self.pool.pop()

    def release_client(self, client: T):
        """释放客户端实例"""
        if len(self.pool) < self.pool_size:
            self.pool.append(client)


class ResponseCache:
    """响应缓存"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存大小
            ttl: 缓存过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}

    def _generate_key(self, function_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        key_data = {
            "function": function_name,
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, function_name: str, args: tuple, kwargs: dict) -> Optional[Any]:
        """获取缓存"""
        key = self._generate_key(function_name, args, kwargs)
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.ttl:
                # 更新访问时间
                self.access_times[key] = time.time()
                return value
            else:
                # 过期，删除
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
        return None

    def set(self, function_name: str, args: tuple, kwargs: dict, value: Any):
        """设置缓存"""
        key = self._generate_key(function_name, args, kwargs)
        
        # 检查缓存大小
        if len(self.cache) >= self.max_size:
            # 删除最久未使用的
            oldest_key = min(self.access_times, key=lambda k: self.access_times.get(k, 0))
            if oldest_key in self.cache:
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
        
        self.cache[key] = (time.time(), value)
        self.access_times[key] = time.time()

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()


class AsyncExecutor:
    """异步执行器"""

    def __init__(self, max_workers: int = 10):
        """
        初始化执行器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """在线程中执行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, functools.partial(func, *args, **kwargs))

    def shutdown(self):
        """关闭执行器"""
        self.executor.shutdown(wait=True)


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_calls: int, period: int):
        """
        初始化速率限制器
        
        Args:
            max_calls: 周期内最大调用次数
            period: 周期长度（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    async def acquire(self):
        """获取执行权限"""
        now = time.time()
        
        # 清理过期的调用记录
        self.calls = [t for t in self.calls if now - t < self.period]
        
        # 检查是否超过限制
        if len(self.calls) >= self.max_calls:
            # 计算需要等待的时间
            oldest_call = self.calls[0]
            wait_time = self.period - (now - oldest_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        # 记录本次调用
        self.calls.append(time.time())


class CircuitBreaker:
    """熔断器"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "CLOSED"
        self.last_failure_time = 0

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数并处理熔断"""
        if self.state == "OPEN":
            # 检查是否可以恢复
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise RuntimeError("服务暂时不可用")
        
        try:
            result = await func(*args, **kwargs)
            # 执行成功，重置状态
            self.failures = 0
            self.state = "CLOSED"
            return result
        except Exception as e:
            # 执行失败
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.state == "HALF_OPEN" or self.failures >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e


class BatchProcessor:
    """批处理器"""

    def __init__(self, batch_size: int = 10, max_wait_time: float = 0.1):
        """
        初始化批处理器
        
        Args:
            batch_size: 批处理大小
            max_wait_time: 最大等待时间（秒）
        """
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.queue = []
        self.processing = False
        self.lock = asyncio.Lock()
        self.condition = asyncio.Condition(self.lock)

    async def add(self, item: Any) -> Any:
        """添加项目到批处理队列"""
        async with self.lock:
            self.queue.append(item)
            
            # 如果队列达到批处理大小，触发处理
            if len(self.queue) >= self.batch_size:
                self.condition.notify()
            else:
                # 否则等待一段时间
                try:
                    await asyncio.wait_for(self.condition.wait(), timeout=self.max_wait_time)
                except asyncio.TimeoutError:
                    # 超时后触发处理
                    if not self.processing and self.queue:
                        self.condition.notify()

    async def process_batch(self, process_func: Callable[[List[Any]], List[Any]]):
        """处理批次"""
        async with self.lock:
            if self.processing or not self.queue:
                return
            
            self.processing = True
            batch = self.queue[:self.batch_size]
            self.queue = self.queue[self.batch_size:]
            
        try:
            results = await process_func(batch)
            return results
        finally:
            async with self.lock:
                self.processing = False
                if self.queue:
                    self.condition.notify()


# 全局实例
response_cache = ResponseCache()
async_executor = AsyncExecutor()


def cached(func):
    """缓存装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 生成缓存键
        cache_key = response_cache._generate_key(func.__name__, args, kwargs)
        
        # 检查缓存
        cached_result = response_cache.get(func.__name__, args, kwargs)
        if cached_result is not None:
            return cached_result
        
        # 执行函数
        result = await func(*args, **kwargs)
        
        # 缓存结果
        response_cache.set(func.__name__, args, kwargs, result)
        
        return result
    return wrapper


def asyncify(func):
    """将同步函数转换为异步函数"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await async_executor.run_in_thread(func, *args, **kwargs)
    return wrapper


def with_retry(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
            raise last_exception
        return wrapper
    return decorator


def get_response_cache() -> ResponseCache:
    """获取响应缓存实例"""
    return response_cache


def get_async_executor() -> AsyncExecutor:
    """获取异步执行器实例"""
    return async_executor
