"""
向量数据库 - ChromaDB + Qwen Embedding
版本: 3.0
优化: 混合搜索、查询扩展、LRU缓存、高级重排、BM25备选、增量更新
"""
import os
import time
import uuid
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from threading import Lock, RLock
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from collections import OrderedDict
import re

import chromadb
from chromadb.config import Settings
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownTextSplitter, PythonCodeTextSplitter

from embeddings import get_embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryCache:
    max_size: int = 1000
    _cache: OrderedDict = field(default_factory=OrderedDict)
    _lock: Lock = field(default_factory=Lock)

    def get(self, key: str) -> Optional[List]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def set(self, key: str, value: List) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class BM25Indexer:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: Dict[str, int] = {}
        self.avgdl: float = 0.0
        self.doc_lengths: List[int] = []
        self.doc_texts: List[List[str]] = []
        self._initialized = False

    def index(self, documents: List[str]) -> None:
        self.doc_texts = [self._tokenize(doc) for doc in documents]
        self.doc_lengths = [len(tokens) for tokens in self.doc_texts]
        self.avgdl = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)

        self.doc_freqs.clear()
        for tokens in self.doc_texts:
            for token in set(tokens):
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self._initialized = True

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '他', '吗', '什么', '为'}
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    def score(self, query: str, doc_idx: int) -> float:
        if not self._initialized:
            return 0.0

        query_tokens = self._tokenize(query)
        doc_tokens = self.doc_texts[doc_idx]
        doc_len = self.doc_lengths[doc_idx]

        score = 0.0
        for q_term in query_tokens:
            if q_term not in self.doc_freqs:
                continue

            tf = doc_tokens.count(q_term)
            df = self.doc_freqs[q_term]
            n = len(self.doc_texts)

            idf = max(0.0, (n - df + 0.5) / (df + 0.5))
            tf_component = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))

            score += idf * tf_component

        return score

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        if not self._initialized:
            return []

        scores = [(i, self.score(query, i)) for i in range(len(self.doc_texts))]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


@dataclass
class IndexStats:
    total_documents: int
    total_chunks: int
    collection_name: str
    persist_dir: str
    embedding_model: str
    last_updated: float
    hybrid_search_enabled: bool
    cache_size: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "collection_name": self.collection_name,
            "persist_dir": self.persist_dir,
            "embedding_model": self.embedding_model,
            "last_updated": self.last_updated,
            "hybrid_search_enabled": self.hybrid_search_enabled,
            "cache_size": self.cache_size
        }


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}")
            logger.error(f"All retries failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


class HybridSearchEngine:
    def __init__(self, vector_weight: float = 0.7, bm25_weight: float = 0.3):
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.bm25 = BM25Indexer()
        self._bm25_built = False

    def build_bm25_index(self, documents: List[str]) -> None:
        if documents:
            self.bm25.index(documents)
            self._bm25_built = True

    def search(
        self,
        query: str,
        vector_results: List[Tuple[str, Dict, float]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if not self._bm25_built or not vector_results:
            return [
                {"content": doc, "metadata": meta, "similarity": vec_sim, "combined_score": vec_sim}
                for doc, meta, vec_sim in vector_results[:top_k]
            ]

        bm25_results = self.bm25.search(query, top_k * 2)

        doc_to_bm25 = {idx: score for idx, score in bm25_results}
        doc_to_vec_sim = {i: (1 - vec_dist) for i, (doc, meta, vec_dist) in enumerate(vector_results)}

        max_vec_sim = max(doc_to_vec_sim.values()) if doc_to_vec_sim else 1.0
        max_bm25 = max(doc_to_bm25.values()) if doc_to_bm25 else 1.0

        combined_scores = []
        for i, (doc, meta, vec_dist) in enumerate(vector_results):
            vec_sim = 1 - vec_dist
            norm_vec = vec_sim / max_vec_sim if max_vec_sim > 0 else 0

            bm25_score = doc_to_bm25.get(i, 0)
            norm_bm25 = bm25_score / max_bm25 if max_bm25 > 0 else 0

            combined = self.vector_weight * norm_vec + self.bm25_weight * norm_bm25

            combined_scores.append({
                "content": doc,
                "metadata": meta,
                "similarity": round(vec_sim, 4),
                "bm25_score": round(bm25_score, 4),
                "combined_score": round(combined, 4)
            })

        combined_scores.sort(key=lambda x: x["combined_score"], reverse=True)
        return combined_scores[:top_k]


class QueryExpander:
    def __init__(self):
        self.synonym_map: Dict[str, List[str]] = {
            "学习": ["学", "掌握", "了解", "熟悉"],
            "问题": ["疑问", "困惑", "难点", "question"],
            "帮助": ["协助", "帮忙", "support", "help"],
            "知识": ["knowledge", "信息", "资料"],
            "查询": ["搜索", "查找", "检索", "search"],
            "计算": ["计算", "运算", "算", "calculate"],
            "时间": ["时刻", "日期", "时间点", "time"],
            "学生": ["学员", "learner", "studuent"],
            "老师": ["教师", "导师", "tutor", "teacher"],
        }

    def expand(self, query: str, max_expansions: int = 3) -> List[str]:
        expansions = [query]
        query_lower = query.lower()

        for term, synonyms in self.synonym_map.items():
            if term in query_lower:
                for syn in synonyms[:max_expansions]:
                    expanded = query_lower.replace(term, syn)
                    if expanded not in expansions:
                        expansions.append(expanded)

        if len(expansions) < 2:
            variations = [
                query,
                query + "是什么",
                "如何" + query,
                query + "的方法",
            ]
            expansions.extend([v for v in variations if v not in expansions][:2])

        return expansions[:5]

    def extract_keywords(self, query: str, max_keywords: int = 5) -> List[str]:
        tokens = re.findall(r'\b[\w\u4e00-\u9fff]{2,}\b', query.lower())
        freq: Dict[str, int] = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1

        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '他', '什么', '为', '如何', '怎么', '怎样'}
        filtered = [t for t in tokens if t not in stop_words and len(t) > 1]

        keyword_freq = {t: freq[t] for t in filtered}
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)

        return [kw for kw, _ in sorted_keywords[:max_keywords]]


class Reranker:
    def __init__(self, alpha: float = 0.6):
        self.alpha = alpha

    def rerank(
        self,
        results: List[Dict[str, Any]],
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if not results:
            return []

        keywords = QueryExpander().extract_keywords(query)

        for result in results:
            content = result.get("content", "").lower()
            metadata = result.get("metadata", {})
            meta_text = str(metadata).lower()

            keyword_score = sum(1 for kw in keywords if kw in content or kw in meta_text)
            keyword_score = keyword_score / max(len(keywords), 1)

            position_score = 1.0 / (1.0 + results.index(result) * 0.05)

            original_sim = result.get("similarity", 0)
            combined = (self.alpha * original_sim + (1 - self.alpha) * keyword_score * position_score)

            result["rerank_score"] = round(combined, 4)
            result["keyword_match"] = keyword_score

        results.sort(key=lambda x: x["rerank_score"], reverse=True)
        return results[:top_k]


class VectorStoreManager:
    _instance = None
    _lock = RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._client = None
        self._collections: Dict[str, Any] = {}
        self._embedder = None
        self._client_lock = RLock()
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._cache = QueryCache(max_size=500)
        self._hybrid_engine = HybridSearchEngine()
        self._bm25_docs: Dict[str, List[str]] = {}
        self._query_expander = QueryExpander()
        self._reranker = Reranker()

    def _get_client(self, persist_dir: str) -> chromadb.PersistentClient:
        with self._client_lock:
            if self._client is None:
                self._client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )
            return self._client

    def _get_embedder(self, model: str, dimension: int):
        if self._embedder is None:
            self._embedder = get_embedder(model=model, dimension=dimension)
        return self._embedder

    def _build_cache_key(self, query: str, n_results: int, collection_name: str) -> str:
        key_str = f"{query}:{n_results}:{collection_name}"
        return hashlib.md5(key_str.encode()).hexdigest()

    @retry_on_failure(max_retries=3, delay=0.5)
    def get_collection(
        self,
        persist_dir: str = "data/chroma",
        collection_name: str = "knowledge_base",
        model: str = "text-embedding-v3",
        dimension: int = 1024,
    ) -> Tuple[Any, Any]:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        client = self._get_client(persist_dir)
        embedder = self._get_embedder(model, dimension)

        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self._update_bm25_index(collection)

        return collection, embedder

    def _update_bm25_index(self, collection) -> None:
        try:
            if collection.count() > 0:
                results = collection.get(limit=min(collection.count(), 5000), include=["documents"])
                docs = results.get("documents", [])
                if docs:
                    self._hybrid_engine.build_bm25_index(docs)
        except Exception as e:
            logger.warning(f"Failed to update BM25 index: {e}")

    def get_stats(
        self,
        persist_dir: str = "data/chroma",
        collection_name: str = "knowledge_base"
    ) -> IndexStats:
        collection, _ = self.get_collection(persist_dir, collection_name)
        return IndexStats(
            total_documents=0,
            total_chunks=collection.count(),
            collection_name=collection_name,
            persist_dir=persist_dir,
            embedding_model="text-embedding-v3",
            last_updated=time.time(),
            hybrid_search_enabled=True,
            cache_size=self._cache.size()
        )

    def invalidate_cache(self, collection_name: str = "knowledge_base") -> None:
        self._cache.clear()
        logger.info(f"Cache invalidated for collection: {collection_name}")


def get_vectorstore(
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
    model: str = "text-embedding-v3",
    dimension: int = 1024,
):
    manager = VectorStoreManager()
    return manager.get_collection(persist_dir, collection_name, model, dimension)


class SmartTextSplitter:
    @staticmethod
    def get_splitter(file_type: str, chunk_size: int = 500, chunk_overlap: int = 50):
        if file_type == "md":
            return MarkdownTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        elif file_type in ("py", "python"):
            return PythonCodeTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        else:
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                add_start_index=True,
            )

    @staticmethod
    def split(documents: List[Any], file_type: str = "txt", chunk_size: int = 500, chunk_overlap: int = 50) -> List[Any]:
        splitter = SmartTextSplitter.get_splitter(file_type, chunk_size, chunk_overlap)

        if hasattr(documents[0], 'metadata') and 'type' in documents[0].metadata:
            file_type = documents[0].metadata.get('type', file_type)

        chunks = splitter.split_documents(documents)
        return chunks


def split_documents(docs, chunk_size: int = 500, chunk_overlap: int = 50, file_type: str = "txt"):
    if not docs:
        return []

    text_splitter = SmartTextSplitter.get_splitter(file_type, chunk_size, chunk_overlap)

    lc_docs = []
    for d in docs:
        if hasattr(d, 'page_content'):
            lc_docs.append(LCDocument(page_content=d.page_content, metadata=d.metadata))
        else:
            lc_docs.append(d)

    chunks = text_splitter.split_documents(lc_docs)
    return chunks


def ingest_to_chroma(
    docs,
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    batch_size: int = 20,
    progress_callback: Optional[callable] = None,
    update_existing: bool = False,
) -> Dict[str, Any]:
    if not docs:
        logger.warning("没有文档可索引")
        return {"success": False, "error": "没有文档可索引", "chunks": 0}

    start_time = time.time()

    file_type = docs[0].metadata.get('type', 'txt') if docs else 'txt'
    chunks = split_documents(docs, chunk_size, chunk_overlap, file_type)
    logger.info(f"分块完成: {len(chunks)} 个块")

    if update_existing:
        source = docs[0].metadata.get('source', '') if docs else ''
        if source:
            deleted = delete_by_source(source, persist_dir, collection_name)
            logger.info(f"已删除旧文档: {deleted} 个块")

    collection, embedder = get_vectorstore(
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    VectorStoreManager().invalidate_cache(collection_name)

    success_count = 0
    error_count = 0
    batch_size = min(batch_size, 50)

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c.page_content for c in batch]
        metadatas = [c.metadata for c in batch]
        ids = [f"doc_{uuid.uuid4().hex[:12]}" for _ in batch]

        try:
            vectors = embedder.embed_documents(texts)

            collection.add(
                embeddings=vectors,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            success_count += len(batch)

        except Exception as e:
            logger.error(f"批次 {i//batch_size + 1} 向量化失败: {e}")
            error_count += len(batch)

        if progress_callback:
            progress_callback(i + len(batch), len(chunks))

        logger.info(f"  向量化中... {min(i + batch_size, len(chunks))}/{len(chunks)}")

    elapsed = time.time() - start_time
    final_count = collection.count()

    logger.info(f"[OK] Indexed {success_count} chunks in {elapsed:.2f}s, total: {final_count}")

    return {
        "success": True,
        "chunks": len(chunks),
        "indexed": success_count,
        "errors": error_count,
        "total": final_count,
        "elapsed_time": round(elapsed, 2)
    }


def query_chroma(
    query_text: str,
    n_results: int = 5,
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
    model: str = "text-embedding-v3",
    dimension: int = 1024,
    filters: Optional[Dict[str, Any]] = None,
    where: Optional[Dict[str, Any]] = None,
    use_cache: bool = True,
    expand_query: bool = True,
) -> List[Tuple[str, Dict[str, Any], float]]:
    cache_key = None
    if use_cache:
        manager = VectorStoreManager()
        cache_key = manager._build_cache_key(query_text, n_results, collection_name)
        cached = manager._cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for query: {query_text[:50]}...")
            return cached

    start_time = time.time()

    collection, embedder = get_vectorstore(
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    expanded_queries = [query_text]
    if expand_query:
        manager = VectorStoreManager()
        expanded_queries = manager._query_expander.expand(query_text)

    all_results: List[Tuple[str, Dict[str, Any], float]] = []

    for q in expanded_queries[:3]:
        try:
            vector = embedder.embed_query(q)

            query_params = {
                "query_embeddings": [vector],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"],
            }

            if where:
                query_params["where"] = where

            results = collection.query(**query_params)

            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]

            for doc, meta, dist in zip(docs, metas, dists):
                all_results.append((doc, meta, dist))

        except Exception as e:
            logger.warning(f"Query expansion failed for '{q}': {e}")

    seen = set()
    unique_results = []
    for doc, meta, dist in all_results:
        key = (doc[:100], meta.get("source", ""))
        if key not in seen:
            seen.add(key)
            unique_results.append((doc, meta, dist))

    unique_results.sort(key=lambda x: x[2])

    if filters:
        filtered_results = []
        for doc, meta, dist in unique_results:
            if all(meta.get(k) == v for k, v in filters.items()):
                filtered_results.append((doc, meta, dist))
        unique_results = filtered_results

    final_results = unique_results[:n_results]

    if use_cache and cache_key:
        manager = VectorStoreManager()
        manager._cache.set(cache_key, final_results)

    elapsed = time.time() - start_time
    logger.debug(f"Query completed in {elapsed:.3f}s (expanded: {len(expanded_queries)} queries)")

    return final_results


def query_with_hybrid_search(
    query_text: str,
    n_results: int = 10,
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
    vector_weight: float = 0.7,
    bm25_weight: float = 0.3,
    rerank: bool = True,
) -> List[Dict[str, Any]]:
    manager = VectorStoreManager()
    manager._hybrid_engine.vector_weight = vector_weight
    manager._hybrid_engine.bm25_weight = bm25_weight

    vector_results = query_chroma(
        query_text=query_text,
        n_results=n_results * 2,
        persist_dir=persist_dir,
        collection_name=collection_name,
        use_cache=False,
        expand_query=False
    )

    hybrid_results = manager._hybrid_engine.search(query_text, vector_results, top_k=n_results)

    if rerank:
        hybrid_results = manager._reranker.rerank(hybrid_results, query_text, top_k=n_results)

    return hybrid_results


def query_with_rerank(
    query_text: str,
    n_results: int = 10,
    rerank_top: int = 5,
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
) -> List[Dict[str, Any]]:
    initial_results = query_chroma(
        query_text=query_text,
        n_results=n_results,
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    if not initial_results:
        return []

    manager = VectorStoreManager()
    reranked = []
    for doc, meta, dist in initial_results:
        similarity = 1 - dist
        reranked.append({
            "content": doc,
            "metadata": meta,
            "similarity": round(similarity, 4),
            "distance": round(dist, 4)
        })

    reranked = manager._reranker.rerank(reranked, query_text, top_k=rerank_top)

    return reranked


def delete_by_source(
    source: str,
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
) -> int:
    collection, _ = get_vectorstore(persist_dir, collection_name)

    try:
        result = collection.get(where={"source": source})
        if result and result.get("ids"):
            collection.delete(ids=result["ids"])
            VectorStoreManager().invalidate_cache(collection_name)
            return len(result["ids"])
    except Exception as e:
        logger.error(f"删除失败: {e}")
    return 0


def reset_collection(
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
) -> bool:
    try:
        client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        client.delete_collection(name=collection_name)
        VectorStoreManager().invalidate_cache(collection_name)
        logger.info(f"Collection {collection_name} deleted")
        return True
    except Exception as e:
        logger.error(f"重置失败: {e}")
        return False


def get_index_info(
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
) -> Dict[str, Any]:
    try:
        collection, _ = get_vectorstore(persist_dir, collection_name)
        stats = VectorStoreManager().get_stats(persist_dir, collection_name)
        return {
            "total_chunks": collection.count(),
            "collection_name": collection_name,
            "persist_dir": persist_dir,
            "hybrid_search_enabled": stats.hybrid_search_enabled,
            "cache_size": stats.cache_size,
        }
    except Exception as e:
        logger.error(f"获取索引信息失败: {e}")
        return {"error": str(e)}


def update_document(
    source: str,
    docs,
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> Dict[str, Any]:
    delete_by_source(source, persist_dir, collection_name)
    return ingest_to_chroma(
        docs,
        persist_dir=persist_dir,
        collection_name=collection_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        update_existing=False
    )
