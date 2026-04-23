"""
Embedding 模型 - 支持多模型、备选机制、批处理优化
版本: 2.0
优化: 多模型支持、自动备选、重试机制、异步批处理
"""
import os
import time
import asyncio
from typing import List, Optional, Dict, Any, Callable
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import dashscope
from dashscope import TextEmbedding
from langchain_core.embeddings import Embeddings

def _get_dashscope_key():
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent / ".env")
    return os.getenv("DASHSCOPE_API_KEY", "")


@dataclass
class EmbeddingResult:
    embedding: List[float]
    model: str
    tokens_used: int
    latency: float


class EmbeddingModelBase(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        raise NotImplementedError


class QwenEmbeddings(EmbeddingModelBase):
    def __init__(
        self,
        model: str = "text-embedding-v3",
        dimension: int = 1024,
        batch_size: int = 10,
        max_retries: int = 3,
        timeout: float = 30.0
    ):
        self.model = model
        self.dimension = dimension
        self.batch_size = min(batch_size, 10)
        self.max_retries = max_retries
        self.timeout = timeout
        self._executor = ThreadPoolExecutor(max_workers=4)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            retry_count = 0

            while retry_count < self.max_retries:
                try:
                    resp = TextEmbedding.call(
                        model=self.model,
                        input=batch,
                        api_key=_get_dashscope_key()
                    )

                    if resp.status_code == 200:
                        embeddings.extend([e["embedding"] for e in resp.output["embeddings"]])
                        break
                    elif resp.status_code == 429:
                        retry_count += 1
                        time.sleep(min(2 ** retry_count, 8))
                    else:
                        raise RuntimeError(f"Embedding失败: {resp.message}")

                except Exception as e:
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        raise RuntimeError(f"Embedding失败 after {self.max_retries} retries: {e}")
                    time.sleep(min(2 ** retry_count, 8))

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                resp = TextEmbedding.call(
                    model=self.model,
                    input=[text],
                    api_key=_get_dashscope_key()
                )

                if resp.status_code == 200:
                    return resp.output["embeddings"][0]["embedding"]
                elif resp.status_code == 429:
                    retry_count += 1
                    time.sleep(min(2 ** retry_count, 8))
                else:
                    raise RuntimeError(f"Embedding失败: {resp.message}")

            except Exception as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    raise RuntimeError(f"Embedding查询失败 after {self.max_retries} retries: {e}")
                time.sleep(min(2 ** retry_count, 8))

        return [0.0] * self.dimension

    def embed_image(self, image_path: str) -> List[float]:
        return [0.0] * self.dimension


class MultiModelEmbeddings(EmbeddingModelBase):
    def __init__(
        self,
        primary_model: str = "text-embedding-v3",
        fallback_model: str = "text-embedding-v2",
        dimension: int = 1024,
        batch_size: int = 10
    ):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.dimension = dimension
        self.batch_size = min(batch_size, 10)
        self._primary = QwenEmbeddings(primary_model, dimension, batch_size)
        self._fallback = QwenEmbeddings(fallback_model, dimension, batch_size)
        self._current_model = primary_model
        self._model_lock = Lock()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        try:
            return self._primary.embed_documents(texts)
        except Exception as e:
            print(f"Primary model {self._primary_model} failed: {e}, trying fallback")
            try:
                with self._model_lock:
                    self._current_model = self.fallback_model
                return self._fallback.embed_documents(texts)
            except Exception as e2:
                print(f"Fallback model {self._fallback_model} also failed: {e2}")
                return [[0.0] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        try:
            return self._primary.embed_query(text)
        except Exception as e:
            print(f"Primary model query failed: {e}, trying fallback")
            try:
                with self._model_lock:
                    self._current_model = self.fallback_model
                return self._fallback.embed_query(text)
            except Exception as e2:
                print(f"Fallback model query also failed: {e2}")
                return [0.0] * self.dimension

    def embed_image(self, image_path: str) -> List[float]:
        return [0.0] * self.dimension

    @property
    def current_model(self) -> str:
        with self._model_lock:
            return self._current_model

    @property
    def model(self) -> str:
        return self.current_model


class AsyncBatchEmbeddings:
    def __init__(
        self,
        embedder: QwenEmbeddings,
        max_concurrent_batches: int = 3
    ):
        self.embedder = embedder
        self.max_concurrent_batches = max_concurrent_batches
        self._semaphore = None

    async def embed_documents_async(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        self._semaphore = asyncio.Semaphore(self.max_concurrent_batches)

        async def embed_batch_with_semaphore(batch: List[str]) -> List[List[float]]:
            async with self._semaphore:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    self.embedder._executor,
                    self.embedder.embed_documents,
                    batch
                )

        batches = [
            texts[i:i + self.embedder.batch_size]
            for i in range(0, len(texts), self.embedder.batch_size)
        ]

        results = await asyncio.gather(*[embed_batch_with_semaphore(b) for b in batches])

        embeddings = []
        for batch_result in results:
            embeddings.extend(batch_result)

        return embeddings

    async def embed_query_async(self, text: str) -> List[float]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.embedder._executor,
            self.embedder.embed_query,
            text
        )


class EmbeddingCache:
    def __init__(self, max_size: int = 2000):
        self._cache: Dict[str, List[float]] = {}
        self._lock = Lock()
        self._max_size = max_size

    def _make_key(self, text: str, model: str) -> str:
        return f"{model}:{hash(text)}"

    def get(self, text: str, model: str) -> Optional[List[float]]:
        key = self._make_key(text, model)
        with self._lock:
            return self._cache.get(key)

    def set(self, text: str, model: str, embedding: List[float]) -> None:
        key = self._make_key(text, model)
        with self._lock:
            if len(self._cache) >= self._max_size:
                first_key = next(iter(self._cache))
                del self._cache[first_key]
            self._cache[key] = embedding

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class CachedEmbeddings(EmbeddingModelBase):
    def __init__(
        self,
        embedder: QwenEmbeddings,
        cache_size: int = 2000
    ):
        self.embedder = embedder
        self.dimension = embedder.dimension
        self._cache = EmbeddingCache(cache_size)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            cached = self._cache.get(text, self.embedder.model)
            if cached is not None:
                results.append((i, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        if uncached_texts:
            embeddings = self.embedder.embed_documents(uncached_texts)
            for text, emb in zip(uncached_texts, embeddings):
                self._cache.set(text, self.embedder.model, emb)

            for idx, emb in zip(uncached_indices, embeddings):
                results.append((idx, emb))

        results.sort(key=lambda x: x[0])
        return [emb for _, emb in results]

    def embed_query(self, text: str) -> List[float]:
        cached = self._cache.get(text, self.embedder.model)
        if cached is not None:
            return cached

        embedding = self.embedder.embed_query(text)
        self._cache.set(text, self.embedder.model, embedding)
        return embedding

    def embed_image(self, image_path: str) -> List[float]:
        return self.embedder.embed_image(image_path)


def get_embedder(
    model: str = None,
    dimension: int = 1024,
    use_cache: bool = True,
    use_fallback: bool = True,
    batch_size: int = 10
) -> EmbeddingModelBase:
    model = model or os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3")
    api_key = _get_dashscope_key()
    if not api_key:
        raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量")

    if use_fallback:
        base_embedder = MultiModelEmbeddings(
            primary_model=model,
            fallback_model=os.getenv("DASHSCOPE_EMBEDDING_FALLBACK_MODEL", "text-embedding-v2"),
            dimension=dimension,
            batch_size=batch_size
        )
    else:
        base_embedder = QwenEmbeddings(
            model=model,
            dimension=dimension,
            batch_size=batch_size
        )

    if use_cache:
        return CachedEmbeddings(base_embedder, cache_size=2000)

    return base_embedder


def get_async_embedder(
    model: str = None,
    dimension: int = 1024,
    max_concurrent: int = 3
) -> AsyncBatchEmbeddings:
    model = model or os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3")
    base_embedder = QwenEmbeddings(model=model, dimension=dimension)
    return AsyncBatchEmbeddings(base_embedder, max_concurrent_batches=max_concurrent)
