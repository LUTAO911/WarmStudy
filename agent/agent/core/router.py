# -*- coding: utf-8 -*-
"""
router.py - Agent 路由决策层
职责：分析用户问题，决定使用什么能力（纯判断，零副作用）
与其他层完全解耦，便于独立测试和优化
"""
import os
import re
import hashlib
from dataclasses import dataclass
from typing import Dict, Any

from redis_client import get_redis


@dataclass(frozen=True)
class RouteDecision:
    """路由决策结果"""
    need_rag: bool       # 是否需要知识库检索
    need_tools: bool     # 是否需要工具调用
    need_skills: bool    # 是否需要技能处理
    confidence: float    # 决策置信度 0-1
    reasoning: str       # 简单决策理由


class Router:
    """
    路由决策器：Qwen-Turbo 做判断（便宜 + 快速）
    优先查 Redis 缓存，同一问题不重复调用 LLM
    """

    def __init__(self):
        self._redis = get_redis()
        self._qwen_api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self._cache_ttl = int(os.getenv("REDIS_CACHE_TTL", "300"))

    def decide(self, message: str, session_id: str) -> RouteDecision:
        """
        智能路由判断：
        1. 先查 Redis 缓存
        2. 缓存未命中 → Qwen-Turbo 判断
        3. Qwen 不可用 → 关键词兜底
        """
        # 1. 查缓存
        cached = self._redis.get_cached_answer(f"route:{message}", session_id)
        if cached:
            parts = cached.split("|")
            if len(parts) == 4:
                return RouteDecision(
                    need_rag=parts[0] == "1",
                    need_tools=parts[1] == "1",
                    need_skills=parts[2] == "1",
                    confidence=float(parts[3]),
                    reasoning="[cached]"
                )

        # 2. Qwen 判断
        decision = self._qwen_decide(message)
        self._redis.set_cached_answer(
            f"route:{message}", session_id,
            f"{int(decision.need_rag)}|{int(decision.need_tools)}|"
            f"{int(decision.need_skills)}|{decision.confidence}",
            ttl=self._cache_ttl
        )
        return decision

    def _qwen_decide(self, message: str) -> RouteDecision:
        """用 Qwen-Turbo 做路由判断"""
        prompt = (
            "判断用户问题是否需要以下能力，只需回答是或否：\n"
            f"问题: {message}\n\n"
            "- 需要 RAG（知识库检索）：涉及专业知识、数据、文档、特定领域内容\n"
            "- 需要 Tools（工具调用）：需要实时信息（时间/天气）、计算、搜索网页\n"
            "- 需要 Skills（技能处理）：需要总结、翻译、格式化\n\n"
            "回答格式（仅4个字符）：\n"
            "RAG是/否 | Tools是/否 | Skills是/否 | 置信度(0-1)\n"
            "例如：RAG是 Tools否 Skills否 0.9"
        )
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self._qwen_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            resp = client.chat.completions.create(
                model="qwen-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=64,
                temperature=0.1,
            )
            result = resp.choices[0].message.content or ""

            # 解析响应
            rag = "RAG是" in result or "RAG:是" in result
            tools = "Tools是" in result or "Tools:是" in result
            skills = "Skills是" in result or "Skills:是" in result
            nums = re.findall(r"0\.[0-9]", result)
            conf = float(nums[0]) if nums else 0.7

            if not rag and not tools and not skills:
                return RouteDecision(False, False, False, 0.5, "fallback")
            return RouteDecision(rag, tools, skills, conf, "qwen_turbo")
        except Exception as e:
            return self._fallback_decision(message)

    def _fallback_decision(self, message: str) -> RouteDecision:
        """关键词兜底判断"""
        rag_kw = ["什么", "如何", "怎么", "为什么", "原因", "定义", "概念",
                   "解释", "区别", "哪个", "哪些", "知识", "文档", "规则"]
        tools_kw = ["计算", "时间", "现在", "几点", "日期", "搜索",
                     "查询", "查一下", "帮我找", "天气"]
        skills_kw = ["总结", "摘要", "翻译", "提取", "关键词", "格式化"]

        need_rag = any(k in message for k in rag_kw)
        need_tools = any(k in message for k in tools_kw)
        need_skills = any(k in message for k in skills_kw)

        return RouteDecision(
            need_rag=need_rag,
            need_tools=need_tools,
            need_skills=need_skills,
            confidence=0.5,
            reasoning="keyword_fallback"
        )
