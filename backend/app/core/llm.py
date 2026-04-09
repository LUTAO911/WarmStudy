"""LangChain LLM封装模块 - 支持Qwen和MiniMax"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from app.config import get_settings
from app.core.performance_optimization import ClientPool, cached, with_retry, asyncify

settings = get_settings()


class QwenChatModel:
    """通义千问聊天模型封装"""

    def __init__(self):
        self.model_name = settings.QWEN_MODEL
        self.temperature = 0.7
        self.max_tokens = 2048
        self.api_key = settings.QWEN_API_KEY
        self.base_url = settings.QWEN_BASE_URL
        # 初始化客户端池
        def client_factory():
            from openai import OpenAI
            return OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        self.client_pool = ClientPool(client_factory, pool_size=3)

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """将LangChain消息格式转换为API格式"""
        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                result.append({"role": "system", "content": msg.content})
        return result

    @with_retry(max_retries=3, delay=1.0)
    def invoke(self, messages: List[BaseMessage]) -> AIMessage:
        """同步调用通义千问"""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        api_messages = self._convert_messages(messages)

        response = client.chat.completions.create(
            model=self.model_name,
            messages=api_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return AIMessage(content=response.choices[0].message.content)

    @with_retry(max_retries=3, delay=1.0)
    async def ainvoke(self, messages: List[BaseMessage]) -> AIMessage:
        """异步调用通义千问"""
        client = await self.client_pool.get_client()
        try:
            api_messages = self._convert_messages(messages)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=api_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return AIMessage(content=response.choices[0].message.content)
        finally:
            self.client_pool.release_client(client)

    def __call__(self, messages: List[BaseMessage]) -> AIMessage:
        return self.invoke(messages)


class QwenEmbedding:
    """通义千问Embedding模型封装"""

    def __init__(self):
        self.model_name = settings.QWEN_EMBEDDING_MODEL
        self.api_key = settings.QWEN_API_KEY
        self.base_url = settings.QWEN_BASE_URL
        # 初始化客户端池
        def client_factory():
            from openai import OpenAI
            return OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        self.client_pool = ClientPool(client_factory, pool_size=3)

    @with_retry(max_retries=3, delay=1.0)
    def embed_query(self, text: str) -> List[float]:
        """单条文本向量化"""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        response = client.embeddings.create(
            model=self.model_name,
            input=text,
        )

        return response.data[0].embedding

    @with_retry(max_retries=3, delay=1.0)
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量文本向量化"""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        response = client.embeddings.create(
            model=self.model_name,
            input=texts,
        )

        return [item.embedding for item in response.data]

    @with_retry(max_retries=3, delay=1.0)
    async def aembed_query(self, text: str) -> List[float]:
        """异步单条文本向量化"""
        client = await self.client_pool.get_client()
        try:
            response = client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            return response.data[0].embedding
        finally:
            self.client_pool.release_client(client)

    @with_retry(max_retries=3, delay=1.0)
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步批量文本向量化"""
        client = await self.client_pool.get_client()
        try:
            response = client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            return [item.embedding for item in response.data]
        finally:
            self.client_pool.release_client(client)

    def embed_query_with_retry(self, text: str, max_retries: int = 3) -> List[float]:
        """带重试的向量化"""
        return self.embed_query(text)


class MiniMaxChatModel:
    """MiniMax M2.7聊天模型封装"""

    def __init__(self):
        self.model_name = settings.MINIMAX_MODEL
        self.temperature = 0.7
        self.max_tokens = 2048
        self.api_key = settings.MINIMAX_API_KEY
        self.base_url = settings.MINIMAX_BASE_URL
        # 初始化客户端池
        def client_factory():
            from openai import OpenAI
            return OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        self.client_pool = ClientPool(client_factory, pool_size=3)

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """将LangChain消息格式转换为API格式"""
        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                result.append({"role": "system", "content": msg.content})
        return result

    @with_retry(max_retries=3, delay=1.0)
    def invoke(self, messages: List[BaseMessage]) -> AIMessage:
        """同步调用MiniMax"""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        api_messages = self._convert_messages(messages)

        response = client.chat.completions.create(
            model=self.model_name,
            messages=api_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return AIMessage(content=response.choices[0].message.content)

    @with_retry(max_retries=3, delay=1.0)
    async def ainvoke(self, messages: List[BaseMessage]) -> AIMessage:
        """异步调用MiniMax"""
        client = await self.client_pool.get_client()
        try:
            api_messages = self._convert_messages(messages)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=api_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return AIMessage(content=response.choices[0].message.content)
        finally:
            self.client_pool.release_client(client)

    def __call__(self, messages: List[BaseMessage]) -> AIMessage:
        return self.invoke(messages)


_llm_instances = {}


def get_qwen_chat() -> QwenChatModel:
    """获取通义千问聊天模型实例"""
    if "qwen_chat" not in _llm_instances:
        _llm_instances["qwen_chat"] = QwenChatModel()
    return _llm_instances["qwen_chat"]


def get_qwen_embedding() -> QwenEmbedding:
    """获取通义千问Embedding模型实例"""
    if "qwen_embedding" not in _llm_instances:
        _llm_instances["qwen_embedding"] = QwenEmbedding()
    return _llm_instances["qwen_embedding"]


def get_minimax_chat() -> MiniMaxChatModel:
    """获取MiniMax聊天模型实例"""
    if "minimax_chat" not in _llm_instances:
        _llm_instances["minimax_chat"] = MiniMaxChatModel()
    return _llm_instances["minimax_chat"]