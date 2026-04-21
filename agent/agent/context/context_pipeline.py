"""
Context Pipeline - 上下文处理流水线
标准化上下文数据的处理流程
"""
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Awaitable
from enum import Enum

from .context_lifecycle import ContextEntry, ContextScope, ContextTTL

class PipelineStage(Enum):
    """流水线阶段"""
    EXTRACTION = "extraction"
    TRANSFORMATION = "transformation"
    ENRICHMENT = "enrichment"
    FILTERING = "filtering"
    RANKING = "ranking"
    AGGREGATION = "aggregation"

@dataclass
class PipelineResult:
    """流水线处理结果"""
    entries: List[ContextEntry]
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0

@dataclass
class ProcessedEntry:
    """处理后的上下文条目"""
    content: str
    entry_type: str
    relevance_score: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class ContextPipeline:
    """
    上下文处理流水线
    
    处理流程：
    1. 提取 - 从各数据源提取上下文
    2. 转换 - 格式转换、类型转换
    3. 增强 - 添加额外信息、关联数据
    4. 过滤 - 去除低质量、无关上下文
    5. 排序 - 按相关性、重要度排序
    6. 聚合 - 合并相似上下文
    """

    def __init__(self):
        self._stages: Dict[PipelineStage, List[Callable]] = {
            stage: [] for stage in PipelineStage
        }

    def register_stage(self, stage: PipelineStage, processor: Callable) -> None:
        """注册处理阶段"""
        self._stages[stage].append(processor)

    async def process(
        self,
        raw_contexts: List[Dict[str, Any]],
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PipelineResult:
        """
        执行流水线处理
        
        Args:
            raw_contexts: 原始上下文列表
            query: 当前查询
            metadata: 额外元数据
            
        Returns:
            PipelineResult: 处理结果
        """
        start_time = time.time()

        # 转换为内部格式
        entries = self._to_entries(raw_contexts)

        # 1. 提取阶段
        for processor in self._stages[PipelineStage.EXTRACTION]:
            if self._is_async_processor(processor):
                entries = await processor(entries, query, metadata)
            else:
                entries = processor(entries, query, metadata)

        # 2. 转换阶段
        for processor in self._stages[PipelineStage.TRANSFORMATION]:
            if self._is_async_processor(processor):
                entries = await processor(entries, query, metadata)
            else:
                entries = processor(entries, query, metadata)

        # 3. 增强阶段
        for processor in self._stages[PipelineStage.ENRICHMENT]:
            if self._is_async_processor(processor):
                entries = await processor(entries, query, metadata)
            else:
                entries = processor(entries, query, metadata)

        # 4. 过滤阶段
        for processor in self._stages[PipelineStage.FILTERING]:
            if self._is_async_processor(processor):
                entries = await processor(entries, query, metadata)
            else:
                entries = processor(entries, query, metadata)

        # 5. 排序阶段
        for processor in self._stages[PipelineStage.RANKING]:
            if self._is_async_processor(processor):
                entries = await processor(entries, query, metadata)
            else:
                entries = processor(entries, query, metadata)

        # 6. 聚合阶段
        for processor in self._stages[PipelineStage.AGGREGATION]:
            if self._is_async_processor(processor):
                entries = await processor(entries, query, metadata)
            else:
                entries = processor(entries, query, metadata)

        return PipelineResult(
            entries=entries,
            metadata=metadata or {},
            processing_time=time.time() - start_time
        )

    def _to_entries(self, raw_contexts: List[Dict[str, Any]]) -> List[ContextEntry]:
        """将原始上下文转换为ContextEntry"""
        entries = []
        for ctx in raw_contexts:
            entry = ContextEntry(
                id=ctx.get("id", str(hash(str(ctx)))),
                key=ctx.get("key", ""),
                value=ctx.get("value", ctx.get("content", "")),
                scope=ContextScope.SESSION,
                ttl=ContextTTL.SHORT,
                created_at=ctx.get("timestamp", time.time()),
                last_accessed=ctx.get("timestamp", time.time()),
                metadata=ctx.get("metadata", {})
            )
            entries.append(entry)
        return entries

    def _is_async_processor(self, processor: Callable) -> bool:
        """检查处理器是否是异步的"""
        import asyncio
        return asyncio.iscoroutinefunction(processor)

    # ========== 内置处理器 ==========

    @staticmethod
    def extract_by_type(
        entries: List[ContextEntry],
        query: str,
        metadata: Optional[Dict[str, Any]]
    ) -> List[ContextEntry]:
        """按类型提取上下文"""
        target_types = metadata.get("entry_types", []) if metadata else []
        if not target_types:
            return entries
        return [e for e in entries if e.metadata.get("type") in target_types]

    @staticmethod
    def filter_by_relevance(
        entries: List[ContextEntry],
        query: str,
        metadata: Optional[Dict[str, Any]]
    ) -> List[ContextEntry]:
        """按相关性过滤"""
        min_relevance = metadata.get("min_relevance", 0.3) if metadata else 0.3
        query_lower = query.lower()
        filtered = []
        for e in entries:
            content = str(e.value).lower()
            if query_lower in content:
                filtered.append(e)
            elif any(kw in content for kw in query_lower.split()[:3]):
                filtered.append(e)
        return filtered

    @staticmethod
    def rank_by_recency(
        entries: List[ContextEntry],
        query: str,
        metadata: Optional[Dict[str, Any]]
    ) -> List[ContextEntry]:
        """按时间排序"""
        return sorted(entries, key=lambda e: e.last_accessed, reverse=True)

    @staticmethod
    def rank_by_importance(
        entries: List[ContextEntry],
        query: str,
        metadata: Optional[Dict[str, Any]]
    ) -> List[ContextEntry]:
        """按重要度排序"""
        return sorted(
            entries,
            key=lambda e: e.metadata.get("importance", 0.5),
            reverse=True
        )

    @staticmethod
    def deduplicate(
        entries: List[ContextEntry],
        query: str,
        metadata: Optional[Dict[str, Any]]
    ) -> List[ContextEntry]:
        """去重"""
        seen = set()
        unique = []
        for e in entries:
            key = str(e.value)[:100]
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique
