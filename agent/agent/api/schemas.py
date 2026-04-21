"""
API Schemas - Pydantic 请求/响应模型定义
版本: v5.0
规范化 API 数据结构，提供完整的类型提示和验证
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

# ========== 枚举类型 ==========

class UserType(str, Enum):
    """用户类型"""
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"

class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ConversationMode(str, Enum):
    """对话模式"""
    CHAT = "chat"
    PSYCHOLOGY = "psychology"
    EDUCATION = "education"
    CRISIS = "crisis"

class ResponseStatus(str, Enum):
    """响应状态"""
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"

# ========== 请求模型 ==========

class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID，不提供则自动创建")
    user_id: Optional[str] = Field(None, description="用户ID")
    user_type: UserType = Field(UserType.STUDENT, description="用户类型")
    use_rag: bool = Field(True, description="是否使用知识库检索")
    use_tools: bool = Field(True, description="是否使用工具调用")
    agent_id: Optional[str] = Field(None, description="指定Agent ID")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "最近学习压力好大，晚上都睡不好觉",
                "session_id": "sess_abc123",
                "user_type": "student"
            }
        }


class PsychologyRequest(BaseModel):
    """心理学模式请求"""
    message: str = Field(..., min_length=1, max_length=2000)
    user_type: UserType = Field(UserType.STUDENT)
    include_knowledge: bool = Field(True, description="是否包含心理知识检索")


class EmotionCheckRequest(BaseModel):
    """情绪检测请求"""
    text: str = Field(..., min_length=1, max_length=1000, description="待检测文本")


class CrisisCheckRequest(BaseModel):
    """危机检测请求"""
    text: str = Field(..., min_length=1, max_length=1000, description="待检测文本")


# ========== 响应模型 ==========

class EmotionInfo(BaseModel):
    """情绪信息"""
    emotion: str = Field(..., description="情绪类型: happy/sad/anxious/angry/fearful/neutral")
    intensity: float = Field(..., ge=0.0, le=1.0, description="强度值 0-1")
    icon: str = Field(..., description="情绪图标 emoji")
    keywords: List[str] = Field(default_factory=list, description="触发关键词")


class CrisisInfo(BaseModel):
    """危机信息"""
    level: str = Field(..., description="危机等级: safe/low/medium/high/critical")
    signals: List[Dict[str, Any]] = Field(default_factory=list, description="检测到的信号")
    message: str = Field(..., description="危机回应消息")
    action: str = Field(..., description="建议行动")
    hotlines: List[str] = Field(default_factory=list, description="危机热线")


class SourceInfo(BaseModel):
    """来源信息"""
    content: str = Field(..., description="内容摘要")
    source: str = Field(..., description="来源")
    page: Optional[str] = Field(None, description="页码")
    similarity: float = Field(..., description="相似度")


class ToolCallInfo(BaseModel):
    """工具调用信息"""
    tool_name: str
    status: str
    execution_time: float
    result: Optional[Any] = None


class ChatResponse(BaseModel):
    """对话响应"""
    answer: str = Field(..., description="AI回复内容")
    mode: str = Field(..., description="处理模式: chat/psychology/education/crisis")

    emotion: Optional[Dict[str, Any]] = Field(None, description="情绪信息")
    crisis_level: Optional[str] = Field(None, description="危机等级")

    sources: List[Dict[str, Any]] = Field(default_factory=list, description="知识来源")
    tool_results: List[Dict[str, Any]] = Field(default_factory=list, description="工具调用结果")

    session_id: str = Field(..., description="会话ID")
    execution_time: float = Field(..., description="执行时间(秒)")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "听到你说学习压力大，我能理解这种感受...",
                "mode": "psychology",
                "emotion": {
                    "emotion": "anxious",
                    "intensity": 0.65,
                    "icon": "😰"
                },
                "session_id": "sess_abc123",
                "execution_time": 1.23
            }
        }


class EmotionResponse(BaseModel):
    """情绪检测响应"""
    emotion: str = Field(..., description="情绪类型")
    intensity: float = Field(..., ge=0.0, le=1.0, description="强度")
    icon: str = Field(..., description="情绪图标")
    suggestion: str = Field(..., description="建议的回应方式")
    keywords: List[str] = Field(default_factory=list)


class CrisisResponse(BaseModel):
    """危机检测响应"""
    level: str = Field(..., description="危机等级")
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    message: str = Field(..., description="回应消息")
    action: str = Field(..., description="建议行动")
    hotlines: List[str] = Field(default_factory=list)
    requires_intervention: bool = Field(..., description="是否需要干预")


# ========== 错误模型 ==========

class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    field: Optional[str] = Field(None, description="出错的字段")
    details: Optional[Dict[str, Any]] = Field(None, description="额外详情")


class APIResponse(BaseModel):
    """通用API响应包装"""
    status: ResponseStatus
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
    request_id: str = Field(..., description="请求ID，用于追踪")
    timestamp: datetime = Field(default_factory=datetime.now)

    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS
