"""RAG模块"""
from app.rag.knowledge_base import KnowledgeBase, get_knowledge_base, initialize_knowledge_base

__all__ = [
    "KnowledgeBase",
    "get_knowledge_base",
    "initialize_knowledge_base",
]