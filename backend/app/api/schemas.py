"""API Schemas

定义API请求和响应的数据模型，提供Pydantic验证和数据转换。
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """对话请求模型"""
    user_id: str = Field(..., min_length=1, description="用户ID")
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")
    session_id: Optional[str] = Field(default=None, description="会话ID，用于区分不同对话")
    child_info: Optional[Dict[str, Any]] = Field(default=None, description="孩子信息")

    @field_validator('message')
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        """验证消息不为空或仅包含空白字符"""
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip()


class ChatResponse(BaseModel):
    """对话响应模型"""
    success: bool
    response: str = Field(default="", description="AI回复内容")
    crisis_detected: bool = Field(default=False, description="是否检测到心理危机")
    crisis_level: str = Field(default="none", description="危机等级: none/low/medium/high/critical")
    intent: Optional[str] = Field(default=None, description="用户意图识别结果")
    state: Optional[str] = Field(default=None, description="当前对话状态")
    ai_name: str = Field(default="暖暖", description="AI助手名称")
    retrieved_knowledge_count: int = Field(default=0, description="检索到的知识库条目数")


class LoginRequest(BaseModel):
    """登录请求模型"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    code: Optional[str] = Field(default=None, description="验证码")
    role: str = Field(default="student", description="角色: student/parent")

    @field_validator('phone')
    @classmethod
    def phone_format(cls, v: str) -> str:
        """验证手机号格式"""
        if not v.isdigit():
            raise ValueError('手机号必须为数字')
        if len(v) != 11:
            raise ValueError('手机号必须为11位')
        return v


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool
    token: Optional[str] = Field(default=None, description="JWT令牌")
    user_id: Optional[str] = Field(default=None, description="用户ID")
    role: Optional[str] = Field(default=None, description="用户角色")
    message: str = Field(default="", description="响应消息")


class CheckinRequest(BaseModel):
    """每日打卡请求模型"""
    user_id: str = Field(..., min_length=1, description="用户ID")
    emotion_score: int = Field(..., ge=1, le=5, description="情绪评分1-5")
    sleep_hours: float = Field(..., ge=0, le=24, description="睡眠时长")
    study_hours: float = Field(..., ge=0, le=24, description="学习时长")
    social_score: int = Field(..., ge=1, le=5, description="社交评分1-5")
    note: Optional[str] = Field(default=None, max_length=500, description="备注")


class BaseResponse(BaseModel):
    """通用响应模型"""
    success: bool = True
    message: str = Field(default="", description="响应消息")
    data: Optional[Any] = Field(default=None, description="附加数据")


class KnowledgeDoc(BaseModel):
    """知识库文档模型"""
    title: str = Field(..., min_length=1, description="文档标题")
    content: str = Field(..., min_length=1, description="文档内容")
    category: str = Field(default="general", description="文档分类")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")


class AssessmentRequest(BaseModel):
    """心理测评请求模型"""
    user_id: str = Field(..., min_length=1, description="用户ID")
    assessment_type: str = Field(..., description="测评类型")
    answers: List[int] = Field(..., min_length=1, description="答案列表")

    @field_validator('answers')
    @classmethod
    def answers_not_empty(cls, v: List[int]) -> List[int]:
        """验证答案列表不为空"""
        if not v:
            raise ValueError('答案列表不能为空')
        return v
