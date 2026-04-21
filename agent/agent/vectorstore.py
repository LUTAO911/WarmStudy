"""
VectorStore - 简化的向量存储实现
用于测试和演示目的
"""
from typing import Any, Dict, List, Optional


class VectorStore:
    """简单的内存向量存储"""

    def __init__(self) -> None:
        self.vectors: Dict[str, List[float]] = {}

    def insert_vector(self, doc_id: str, vector: List[float]) -> None:
        """插入向量"""
        self.vectors[doc_id] = vector

    def retrieve_vector(self, doc_id: str) -> Optional[List[float]]:
        """检索向量"""
        return self.vectors.get(doc_id)

    def delete_vector(self, doc_id: str) -> bool:
        """删除向量"""
        if doc_id in self.vectors:
            del self.vectors[doc_id]
            return True
        return False

    def search_similar(
        self, query_vector: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """搜索相似向量（简单余弦相似度）"""
        results: List[Dict[str, Any]] = []
        for doc_id, vec in self.vectors.items():
            similarity = self._cosine_similarity(query_vector, vec)
            results.append({"doc_id": doc_id, "vector": vec, "similarity": similarity})
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        if len(a) != len(b):
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
