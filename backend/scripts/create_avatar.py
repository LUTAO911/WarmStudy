"""创建默认头像PNG文件"""
from PIL import Image, ImageDraw
import os

def create_avatar():
    """创建一个简单的默认头像"""
    # 创建100x100的图像
    size = 100
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 背景圆形 - 浅蓝色
    bg_color = (182, 227, 244, 255)  # #b6e3f4
    draw.ellipse([5, 5, 95, 95], fill=bg_color)
    
    # 左眼
    draw.ellipse([27, 32, 43, 48], fill=(51, 51, 51, 255))  # #333
    draw.ellipse([30, 35, 37, 41], fill=(255, 255, 255, 255))  # 高光
    
    # 右眼
    draw.ellipse([57, 32, 73, 48], fill=(51, 51, 51, 255))  # #333
    draw.ellipse([60, 35, 67, 41], fill=(255, 255, 255, 255))  # 高光
    
    # 腮红
    draw.ellipse([20, 45, 30, 55], fill=(255, 182, 193, 150))  # 左腮红
    draw.ellipse([70, 45, 80, 55], fill=(255, 182, 193, 150))  # 右腮红
    
    # 嘴巴（微笑）
    draw.arc([35, 55, 65, 75], start=0, end=180, fill=(51, 51, 51, 255), width=3)
    
    # 保存图像
    avatar_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                              "assets", "avatar", "pet")
    os.makedirs(avatar_dir, exist_ok=True)
    
    avatar_path = os.path.join(avatar_dir, "avatar.png")
    img.save(avatar_path, "PNG")
    print(f"头像已创建: {avatar_path}")
    return avatar_path

if __name__ == "__main__":
    create_avatar()
