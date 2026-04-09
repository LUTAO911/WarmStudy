"""
对话API - 基于LangChain Agent

提供学生端和家长端的AI对话功能，支持流式响应和对话记忆管理。
"""
from fastapi import APIRouter, HTTPException, status
from app.api.schemas import ChatRequest, ChatResponse, BaseResponse
from app.core.agent import get_agent, reset_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    通用对话接口

    - 根据session_id判断角色类型，默认为学生
    - 支持上下文记忆
    """
    try:
        role = request.session_id or "student"
        agent = get_agent(user_id=request.user_id, role=role)
        result = agent.chat(user_id=request.user_id, message=request.message)
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求参数错误: {str(e)}"
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI响应超时，请稍后重试"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.post("/student/chat", response_model=ChatResponse)
async def student_chat(request: ChatRequest) -> ChatResponse:
    """
    学生端对话接口

    专门为学生提供心理陪伴和情感支持服务。
    支持传入child_info用于个性化回复。
    """
    try:
        if not request.user_id:
            raise ValueError("user_id不能为空")

        agent = get_agent(user_id=request.user_id, role="student")
        result = agent.chat(
            user_id=request.user_id,
            message=request.message,
            child_info=request.child_info
        )
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求参数错误: {str(e)}"
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI响应超时，请稍后重试"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.post("/parent/chat", response_model=ChatResponse)
async def parent_chat(request: ChatRequest) -> ChatResponse:
    """
    家长端对话接口

    专门为家长提供家庭教育建议和亲子沟通指导。
    """
    try:
        if not request.user_id:
            raise ValueError("user_id不能为空")

        agent = get_agent(user_id=request.user_id, role="parent")
        result = agent.chat(user_id=request.user_id, message=request.message)
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求参数错误: {str(e)}"
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI响应超时，请稍后重试"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.post("/chat/reset", response_model=BaseResponse)
async def reset_chat(request: ChatRequest) -> BaseResponse:
    """
    重置对话记忆

    清除指定用户的对话历史记录，重新开始新对话。
    """
    try:
        if not request.user_id:
            raise ValueError("user_id不能为空")

        role = request.session_id or "student"
        result = reset_agent(request.user_id, role=role)
        return BaseResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请求参数错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )