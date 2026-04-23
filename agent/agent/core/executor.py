# -*- coding: utf-8 -*-
"""
executor.py - Agent 执行层
职责：执行具体任务（RAG检索、工具调用、LLM生成）
对结果负责，不做判断
"""
import hashlib
import time
import json
from typing import List, Dict, Any, Optional, Callable

from redis_client import get_redis


class Executor:
    """
    执行器：执行 RAG 检索 + 工具 + LLM 生成
    结果缓存：相同 prompt 的 LLM 响应在 Redis 中缓存 10 分钟
    """

    def __init__(self):
        self._redis = get_redis()

    def retrieve_context(
        self,
        query: str,
        session_id: str,
        n_results: int = 5,
        use_hybrid: bool = True,
        rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """知识库检索（带缓存）"""
        try:
            if use_hybrid:
                from vectorstore import query_with_hybrid_search
                return query_with_hybrid_search(
                    query_text=query,
                    n_results=n_results,
                    rerank=rerank,
                )
            else:
                from vectorstore import query_chroma
                raw = query_chroma(
                    query_text=query,
                    n_results=n_results,
                    persist_dir="data/chroma",
                    collection_name="knowledge_base",
                )
                results = []
                for doc, meta, dist in raw:
                    results.append({
                        "content": doc,
                        "source": str(meta.get("source", "")),
                        "page": meta.get("page", ""),
                        "similarity": round(1 - dist, 4),
                    })
                return results
        except Exception:
            return []

    def execute_tools(
        self,
        message: str,
        tools_registry: Any
    ) -> List[Dict[str, Any]]:
        """执行匹配的工具"""
        results = []
        msg_lower = message.lower()

        tool_map = {
            "get_current_time": ["时间", "现在", "几点", "日期"],
            "calculate": ["计算", "等于", "+/"],
            "search_web": ["搜索", "search", "查一下"],
        }

        for tool_name, keywords in tool_map.items():
            if any(k in msg_lower for k in keywords):
                try:
                    tr = tools_registry.execute(tool_name, query=message)
                    if tr.is_success:
                        results.append({
                            "tool": tool_name,
                            "result": tr.formatted_result,
                            "success": True,
                        })
                except Exception:
                    pass
        return results

    def generate_response(
        self,
        prompt: str,
        model: str = "qwen",
        stream_callback: Optional[Callable] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        LLM 生成（带 Redis 缓存）
        缓存 key = SHA256(prompt)，TTL = 600s
        """
        # 1. 查缓存
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        cached = self._redis.get_llm_cache(prompt_hash)
        if cached:
            return cached.get("answer", "")

        # 2. 生成
        answer = self._generate_dashscope(prompt, temperature, max_tokens)

        # 3. 写缓存
        if answer and not answer.startswith("Error:"):
            self._redis.set_llm_cache(
                prompt_hash,
                {"answer": answer, "model": model, "tokens": len(prompt)},
                ttl=600
            )

        return answer

    def _generate_dashscope(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """DashScope API 调用"""
        import os
        try:
            from openai import OpenAI
            api_key = os.getenv("DASHSCOPE_API_KEY", "")
            client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            resp = client.chat.completions.create(
                model="qwen-max",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"Error: {str(e)}"
