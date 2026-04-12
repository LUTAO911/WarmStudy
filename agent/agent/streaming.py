"""
Streaming 模块 - Server-Sent Events (SSE) 流式响应支持
版本: 1.0
支持: Flask流式输出、异步生成、进度追踪
"""
import json
import time
import asyncio
from typing import AsyncGenerator, Generator, Callable, Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread
from functools import wraps


class StreamEventType(Enum):
    START = "start"
    TOKEN = "token"
    SOURCE = "source"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SKILL_CALL = "skill_call"
    SKILL_RESULT = "skill_result"
    ERROR = "error"
    COMPLETE = "complete"
    PROGRESS = "progress"


@dataclass
class StreamEvent:
    event_type: StreamEventType
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_sse_format(self) -> str:
        event_data = {
            "type": self.event_type.value,
            "data": self.data,
            **self.metadata
        }
        return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "data": self.data,
            "metadata": self.metadata
        }


class SSEFormatter:
    @staticmethod
    def format_event(event_type: str, data: Any, metadata: Optional[Dict] = None) -> str:
        event_data = {
            "type": event_type,
            "data": data
        }
        if metadata:
            event_data.update(metadata)
        return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

    @staticmethod
    def format_token(token: str, token_index: int = 0) -> str:
        return SSEFormatter.format_event("token", {
            "token": token,
            "index": token_index
        })

    @staticmethod
    def format_source(source: Dict[str, Any], index: int) -> str:
        return SSEFormatter.format_event("source", source, {"index": index})

    @staticmethod
    def format_error(error: str, error_code: str = "UNKNOWN") -> str:
        return SSEFormatter.format_event("error", {
            "message": error,
            "code": error_code
        })

    @staticmethod
    def format_complete(execution_time: float, tokens_count: int) -> str:
        return SSEFormatter.format_event("complete", {
            "execution_time": round(execution_time, 3),
            "tokens_count": tokens_count
        })

    @staticmethod
    def format_progress(current: int, total: int, message: str = "") -> str:
        return SSEFormatter.format_event("progress", {
            "current": current,
            "total": total,
            "percent": round(current / max(total, 1) * 100, 1),
            "message": message
        })


class StreamingTextGenerator:
    def __init__(
        self,
        chunk_size: int = 10,
        delay_per_chunk: float = 0.02
    ):
        self.chunk_size = chunk_size
        self.delay_per_chunk = delay_per_chunk

    def generate(
        self,
        text: str,
        callback: Optional[Callable[[str], None]] = None
    ) -> Generator[str, None, None]:
        for i in range(0, len(text), self.chunk_size):
            chunk = text[i:i + self.chunk_size]
            if callback:
                callback(chunk)
            yield chunk
            if self.delay_per_chunk > 0 and i + self.chunk_size < len(text):
                time.sleep(self.delay_per_chunk)

    def generate_words(
        self,
        text: str,
        callback: Optional[Callable[[str], None]] = None
    ) -> Generator[str, None, None]:
        words = text.split()
        for i, word in enumerate(words):
            if callback:
                callback(word + " ")
            yield word + " "
            if self.delay_per_chunk > 0 and i < len(words) - 1:
                time.sleep(self.delay_per_chunk)


class AsyncStreamingTextGenerator:
    def __init__(
        self,
        chunk_size: int = 10,
        delay_per_chunk: float = 0.02
    ):
        self.chunk_size = chunk_size
        self.delay_per_chunk = delay_per_chunk

    async def generate(
        self,
        text: str,
        callback: Optional[Callable[[str], None]] = None
    ) -> AsyncGenerator[str, None]:
        for i in range(0, len(text), self.chunk_size):
            chunk = text[i:i + self.chunk_size]
            if callback:
                callback(chunk)
            yield chunk
            if self.delay_per_chunk > 0 and i + self.chunk_size < len(text):
                await asyncio.sleep(self.delay_per_chunk)

    async def generate_words(
        self,
        text: str,
        callback: Optional[Callable[[str], None]] = None
    ) -> AsyncGenerator[str, None]:
        words = text.split()
        for i, word in enumerate(words):
            if callback:
                callback(word + " ")
            yield word + " "
            if self.delay_per_chunk > 0 and i < len(words) - 1:
                await asyncio.sleep(self.delay_per_chunk)


class StreamResponseBuilder:
    def __init__(self):
        self.events: List[StreamEvent] = []
        self._start_time: float = 0.0

    def start(self, session_id: str = "") -> "StreamResponseBuilder":
        self._start_time = time.time()
        self.events.append(StreamEvent(
            event_type=StreamEventType.START,
            data={"session_id": session_id},
            metadata={"timestamp": time.time()}
        ))
        return self

    def add_token(self, token: str, index: int = 0) -> "StreamResponseBuilder":
        self.events.append(StreamEvent(
            event_type=StreamEventType.TOKEN,
            data={"token": token, "index": index}
        ))
        return self

    def add_source(self, source: Dict[str, Any], index: int) -> "StreamResponseBuilder":
        self.events.append(StreamEvent(
            event_type=StreamEventType.SOURCE,
            data=source,
            metadata={"index": index}
        ))
        return self

    def add_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> "StreamResponseBuilder":
        self.events.append(StreamEvent(
            event_type=StreamEventType.TOOL_CALL,
            data={"tool_name": tool_name, "parameters": parameters}
        ))
        return self

    def add_tool_result(
        self,
        tool_name: str,
        result: Any,
        execution_time: float
    ) -> "StreamResponseBuilder":
        self.events.append(StreamEvent(
            event_type=StreamEventType.TOOL_RESULT,
            data={"tool_name": tool_name, "result": result},
            metadata={"execution_time": round(execution_time, 3)}
        ))
        return self

    def add_error(self, error: str, error_code: str = "UNKNOWN") -> "StreamResponseBuilder":
        self.events.append(StreamEvent(
            event_type=StreamEventType.ERROR,
            data={"message": error, "code": error_code}
        ))
        return self

    def add_progress(
        self,
        current: int,
        total: int,
        message: str = ""
    ) -> "StreamResponseBuilder":
        self.events.append(StreamEvent(
            event_type=StreamEventType.PROGRESS,
            data={
                "current": current,
                "total": total,
                "percent": round(current / max(total, 1) * 100, 1),
                "message": message
            }
        ))
        return self

    def complete(self) -> "StreamResponseBuilder":
        execution_time = time.time() - self._start_time
        self.events.append(StreamEvent(
            event_type=StreamEventType.COMPLETE,
            data={
                "execution_time": round(execution_time, 3),
                "total_events": len(self.events)
            }
        ))
        return self

    def to_sse_response(self) -> Generator[str, None, None]:
        for event in self.events:
            yield event.to_sse_format()
        yield "data: [DONE]\n\n"

    def to_list(self) -> List[Dict[str, Any]]:
        return [event.to_dict() for event in self.events]


def stream_generator(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        generator = func(*args, **kwargs)
        for chunk in generator:
            yield chunk
    return wrapper


def async_stream_generator(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async for chunk in func(*args, **kwargs):
            yield chunk
    return wrapper


class ChunkedTextIterator:
    def __init__(self, text: str, chunk_size: int = 10):
        self.text = text
        self.chunk_size = chunk_size
        self.position = 0

    def __iter__(self):
        return self

    def __next__(self) -> str:
        if self.position >= len(self.text):
            raise StopIteration

        chunk = self.text[self.position:self.position + self.chunk_size]
        self.position += self.chunk_size
        return chunk


def create_sse_response(
    event_type: str,
    data: Any,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    return SSEFormatter.format_event(event_type, data, metadata)


def create_token_sse(token: str, index: int = 0) -> str:
    return SSEFormatter.format_token(token, index)


def create_error_sse(error: str, error_code: str = "UNKNOWN") -> str:
    return SSEFormatter.format_error(error, error_code)


def create_complete_sse(execution_time: float, tokens_count: int) -> str:
    return SSEFormatter.format_complete(execution_time, tokens_count)


def create_progress_sse(current: int, total: int, message: str = "") -> str:
    return SSEFormatter.format_progress(current, total, message)
