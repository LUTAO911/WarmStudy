"""WarmStudy AI Backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from app.config import get_settings
from app.api import api_router
from app.db.sync import init_sync_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    init_sync_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="""
## WarmStudy AI API

基于LangChain的智能心理陪伴助手后端服务。

### 主要功能

- **学生端**: AI心理辅导对话、每日打卡、心理测评
- **家长端**: 家庭教育助手、孩子状态监控、预警提醒
- **RAG知识库**: 基于向量检索的精准回答

### 认证方式

API使用Bearer Token认证，格式：
```
Authorization: Bearer <token>
```

### 文档说明

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 挂载静态文件目录 - 用于微信小程序直接访问
base_dir = os.path.dirname(os.path.abspath(__file__))
assets_dir = os.path.normpath(os.path.join(base_dir, "..", "assets"))
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    print(f"Static files mounted at: {assets_dir}")
else:
    print(f"Assets directory not found: {assets_dir}")

# 挂载前端目录
frontend_dir = os.path.normpath(os.path.join(base_dir, "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")
    print(f"Frontend files mounted at: {frontend_dir}")
else:
    print(f"Frontend directory not found: {frontend_dir}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)