"""认证API"""
from fastapi import APIRouter, HTTPException
from app.api.schemas import LoginRequest, LoginResponse
from datetime import datetime, timedelta
import jwt
from app.config import get_settings

settings = get_settings()

router = APIRouter()


def create_access_token(data: dict) -> str:
    """创建JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """登录接口"""
    try:
        phone = request.phone
        role = request.role

        user_id = f"user_{phone}_{role}"

        token = create_access_token({"user_id": user_id, "role": role})

        return LoginResponse(
            success=True,
            token=token,
            user_id=user_id,
            role=role,
            message="登录成功"
        )
    except Exception as e:
        return LoginResponse(
            success=False,
            message=str(e)
        )


@router.post("/register", response_model=LoginResponse)
async def register(request: LoginRequest):
    """注册接口"""
    return LoginResponse(
        success=True,
        token="mock_token",
        user_id=f"user_{request.phone}_{request.role}",
        role=request.role,
        message="注册成功"
    )


@router.get("/verify")
async def verify_token(token: str):
    """验证Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return {"success": True, "data": payload}
    except jwt.ExpiredSignatureError:
        return {"success": False, "message": "Token已过期"}
    except jwt.InvalidTokenError:
        return {"success": False, "message": "Token无效"}
    except Exception:
        return {"success": False, "message": "Token验证失败"}