"""API路由注册"""
from fastapi import APIRouter
from app.api import auth, chat, knowledge, student, static

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(student.router, tags=["学生"])
api_router.include_router(chat.router, tags=["对话"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(static.router, tags=["静态文件"])