"""
RAG Engine - 检索增强生成引擎
统一检索接口、混合搜索、查询缓存、重排优化
版本: v5.0
"""
import time
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from vectorstore import HybridSearchEngine, VectorStoreManager

# ========== 数据模型 ==========

@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    source: str           # 来源标识
    score: float          # 相关度得分
    metadata: Dict[str, Any] = field(default_factory=dict)
    reranked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "score": self.score,
            "metadata": self.metadata,
            "reranked": self.reranked
        }


@dataclass
class RAGQuery:
    """RAG查询"""
    query_text: str
    n_results: int = 5
    search_type: str = "hybrid"  # vector/hybrid/keyword
    filters: Optional[Dict[str, Any]] = None
    rerank: bool = True
    expand_query: bool = True


@dataclass
class RAGResult:
    """RAG结果"""
    query: str
    results: List[RetrievalResult]
    total_retrieved: int
    retrieval_time: float
    rerank_time: float = 0.0
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_retrieved": self.total_retrieved,
            "retrieval_time": self.retrieval_time,
            "rerank_time": self.rerank_time,
            "cached": self.cached
        }


# ========== RAG引擎 ==========

class RAGEngine:
    """
    RAG引擎 - 统一检索接口

    功能：
    1. 统一检索接口 - 封装vectorstore的复杂API
    2. 混合搜索 - 向量 + BM25 融合
    3. 查询缓存 - 避免重复检索
    4. 查询扩展 - 提升召回率
    5. 重排优化 - 基于重排模型优化结果
    6. 多路召回 - 支持多种检索策略并行
    """

    def __init__(
        self,
        vectorstore_manager: Optional["VectorStoreManager"] = None,
        hybrid_search: Optional["HybridSearchEngine"] = None,
        cache_enabled: bool = True,
        rerank_enabled: bool = True,
        default_top_k: int = 5,
    ):
        self._vstore = vectorstore_manager
        self._hybrid = hybrid_search
        self._cache_enabled = cache_enabled
        self._rerank_enabled = rerank_enabled
        self._default_top_k = default_top_k

        # 查询缓存
        self._query_cache: Dict[str, RAGResult] = {}
        self._cache_max_size = 500
        self._cache_ttl = 3600  # 1小时

        # 查询扩展词
        self._query_expanders: Dict[str, List[str]] = {
            "心理": ["心理健康", "心理咨询", "情绪调节", "压力管理"],
            "焦虑": ["焦虑症", "焦虑情绪", "如何缓解焦虑", "焦虑怎么办"],
            "抑郁": ["抑郁症", "抑郁情绪", "如何走出抑郁", "抑郁倾向"],
            "学习": ["学习方法", "学习技巧", "如何学习", "高效学习"],
            "压力": ["压力管理", "缓解压力", "压力过大", "压力调节"],
            "人际关系": ["人际交往", "社交技巧", "如何与人相处", "人际关系处理"],
            "考试": ["考试技巧", "考试焦虑", "如何应对考试", "考试压力"],
            "亲子": ["亲子关系", "父母沟通", "家庭教育", "亲子沟通"],
        }

        # 评分权重
        self._vector_weight = 0.7
        self._bm25_weight = 0.3

    def _get_cache_key(self, query: RAGQuery) -> str:
        """生成缓存键"""
        key_data = f"{query.query_text}:{query.n_results}:{query.search_type}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_cache_valid(self, result: RAGResult) -> bool:
        """检查缓存是否有效"""
        if result.cached:
            age = time.time() - (result.results[0].metadata.get("_cached_at", 0) if result.results else 0)
            return age < self._cache_ttl
        return False

    def _expand_query(self, query_text: str) -> str:
        """查询扩展"""
        expanded = query_text

        for keyword, expansions in self._query_expanders.items():
            if keyword in query_text:
                # 保留原查询，添加同义词/相关词
                expansions_str = " ".join(expansions[:2])
                expanded = f"{query_text} {expansions_str}"

        return expanded

    async def retrieve(self, query: RAGQuery) -> RAGResult:
        """
        执行检索

        Args:
            query: RAG查询

        Returns:
            RAGResult: 检索结果
        """
        start_time = time.time()
        cached = False

        # 1. 尝试缓存
        if self._cache_enabled:
            cache_key = self._get_cache_key(query)
            if cache_key in self._query_cache:
                cached_result = self._query_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    cached_result.cached = True
                    return cached_result

        # 2. 查询扩展
        search_query = query.query_text
        if query.expand_query:
            search_query = self._expand_query(query.query_text)

        # 3. 执行检索
        results: List[RetrievalResult] = []

        try:
            if query.search_type == "vector":
                results = await self._vector_search(search_query, query.n_results, query.filters)
            elif query.search_type == "keyword":
                results = await self._keyword_search(search_query, query.n_results, query.filters)
            else:  # hybrid
                results = await self._hybrid_search(search_query, query.n_results, query.filters)

        except Exception as e:
            # 降级处理
            results = await self._fallback_search(query.query_text, query.n_results)

        # 4. 重排
        rerank_time = 0.0
        if query.rerank and self._rerank_enabled and results:
            rerank_start = time.time()
            results = self._rerank_results(results, query.query_text)
            rerank_time = time.time() - rerank_start

        # 5. 构建结果
        retrieval_time = time.time() - start_time
        result = RAGResult(
            query=query.query_text,
            results=results[:query.n_results],
            total_retrieved=len(results),
            retrieval_time=retrieval_time,
            rerank_time=rerank_time,
            cached=cached
        )

        # 6. 缓存结果
        if self._cache_enabled and not cached:
            cache_key = self._get_cache_key(query)
            if len(self._query_cache) >= self._cache_max_size:
                # 删除最老的缓存
                oldest_key = next(iter(self._query_cache))
                del self._query_cache[oldest_key]
            self._query_cache[cache_key] = result

        return result

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[RetrievalResult]:
        """向量检索"""
        if not self._vstore:
            return []

        try:
            results = self._vstore.query(
                query_texts=[query],
                n_results=top_k,
                where=filters,
            )

            return self._parse_vstore_results(results)

        except Exception:
            return []

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[RetrievalResult]:
        """关键词检索（BM25）"""
        if not self._hybrid:
            return []

        try:
            # 使用BM25
            scores = self._hybrid.bm25.search(query, top_k)
            results = []

            for idx, score in scores:
                # 需要从vstore获取内容
                if self._vstore:
                    doc = self._vstore.get_by_idx(idx)
                    if doc:
                        results.append(RetrievalResult(
                            content=doc.get("content", ""),
                            source=doc.get("source", "unknown"),
                            score=score,
                            metadata=doc.get("metadata", {}),
                            reranked=False
                        ))

            return results

        except Exception:
            return []

    async def _hybrid_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[RetrievalResult]:
        """混合检索"""
        if not self._vstore:
            return []

        try:
            # 并行执行向量和BM25
            vector_results = await self._vector_search(query, top_k * 2, filters)
            keyword_results = await self._keyword_search(query, top_k * 2, filters)

            # 合并结果
            merged: Dict[str, RetrievalResult] = {}

            for r in vector_results:
                r.score = r.score * self._vector_weight
                merged[r.content[:100]] = r

            for r in keyword_results:
                key = r.content[:100]
                if key in merged:
                    merged[key].score += r.score * self._bm25_weight
                else:
                    r.score = r.score * self._bm25_weight
                    merged[key] = r

            # 按得分排序
            sorted_results = sorted(merged.values(), key=lambda x: x.score, reverse=True)

            return sorted_results[:top_k]

        except Exception:
            return []

    async def _fallback_search(
        self,
        query: str,
        top_k: int
    ) -> List[RetrievalResult]:
        """降级检索"""
        # 简单的关键词匹配降级
        if self._vstore:
            try:
                results = self._vstore.query(
                    query_texts=[query],
                    n_results=top_k,
                )
                return self._parse_vstore_results(results)
            except Exception:
                pass

        return []

    def _parse_vstore_results(self, results: Any) -> List[RetrievalResult]:
        """解析vectorstore结果"""
        parsed = []

        try:
            if hasattr(results, "documents"):
                docs = results.documents
                if docs and len(docs) > 0:
                    for i, doc in enumerate(docs[0]):
                        meta = {}
                        if hasattr(results, "metadatas") and results.metadatas:
                            meta = results.metadatas[0].get(i, {})

                        score = 0.0
                        if hasattr(results, "distances") and results.distances:
                            # ChromaDB距离转相似度
                            dist = results.distances[0].get(i, 1.0)
                            score = 1.0 - min(dist, 1.0)

                        parsed.append(RetrievalResult(
                            content=doc,
                            source=meta.get("source", "unknown"),
                            score=score,
                            metadata=meta,
                            reranked=False
                        ))

        except Exception:
            pass

        return parsed

    def _rerank_results(
        self,
        results: List[RetrievalResult],
        original_query: str
    ) -> List[RetrievalResult]:
        """结果重排"""
        if not results:
            return results

        query_terms = set(original_query.lower().split())

        def rerank_score(result: RetrievalResult) -> float:
            content_lower = result.content.lower()
            content_terms = set(content_lower.split())

            # 1. 原始相似度
            score = result.score

            # 2. 关键词命中奖励
            overlap = len(query_terms & content_terms)
            if overlap > 0:
                score += overlap * 0.1

            # 3. 位置奖励（前面内容更重要）
            first_pos = content_lower.find(original_query.lower())
            if first_pos >= 0 and first_pos < 100:
                score += 0.1

            # 4. 长度惩罚（太长或太短都减分）
            content_len = len(result.content)
            if content_len < 50:
                score -= 0.05
            elif content_len > 2000:
                score -= 0.05

            return score

        # 重排
        reranked = [(r, rerank_score(r)) for r in results]
        reranked.sort(key=lambda x: x[1], reverse=True)

        final_results = []
        for r, _ in reranked:
            r.reranked = True
            final_results.append(r)

        return final_results

    def clear_cache(self) -> int:
        """清除缓存，返回清除数量"""
        count = len(self._query_cache)
        self._query_cache.clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取RAG引擎统计"""
        return {
            "cache_enabled": self._cache_enabled,
            "cache_size": len(self._query_cache),
            "cache_max_size": self._cache_max_size,
            "rerank_enabled": self._rerank_enabled,
            "vector_weight": self._vector_weight,
            "bm25_weight": self._bm25_weight,
            "default_top_k": self._default_top_k,
        }


# ========== 便捷函数 ==========

async def query_rag(
    query_text: str,
    n_results: int = 5,
    search_type: str = "hybrid"
) -> RAGResult:
    """
    便捷RAG查询函数

    Args:
        query_text: 查询文本
        n_results: 返回数量
        search_type: 搜索类型

    Returns:
        RAGResult: RAG结果
    """
    query = RAGQuery(
        query_text=query_text,
        n_results=n_results,
        search_type=search_type
    )

    engine = RAGEngine()
    return await engine.retrieve(query)
