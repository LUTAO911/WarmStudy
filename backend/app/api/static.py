"""静态文件服务"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/static", tags=["静态文件"])

# 静态文件目录 - 指向项目根目录的assets
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "assets")

@router.get("/avatar/pet/avatar.png")
async def get_avatar():
    """获取头像 - 支持PNG和SVG格式"""
    # 首先尝试查找PNG格式
    avatar_png_path = os.path.join(STATIC_DIR, "avatar", "pet", "avatar.png")
    if os.path.exists(avatar_png_path):
        return FileResponse(avatar_png_path, media_type="image/png")
    
    # 如果没有PNG，返回SVG格式（微信小程序可能不支持）
    avatar_svg_path = os.path.join(STATIC_DIR, "avatar", "pet", "avatar.svg")
    if os.path.exists(avatar_svg_path):
        return FileResponse(avatar_svg_path, media_type="image/svg+xml")
    
    # 如果都不存在，返回404错误
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Avatar not found")
