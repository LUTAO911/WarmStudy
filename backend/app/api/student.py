"""学生相关API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os

router = APIRouter(prefix="/student", tags=["学生"])

# 模拟数据存储
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 模型定义
class CheckinRequest(BaseModel):
    user_id: str
    emotion: Optional[str] = None
    sleep: Optional[str] = None
    study: Optional[str] = None
    social: Optional[str] = None

class PsychTestRequest(BaseModel):
    user_id: str
    answers: Dict[str, Any]
    test_type: str = "weekly"

class PsychStatusResponse(BaseModel):
    user_id: str
    checkin: Dict[str, str]
    test_status: Dict[str, bool]
    last_checkin: str

# 工具函数
def get_user_data(user_id: str) -> Dict[str, Any]:
    """获取用户数据"""
    data_file = os.path.join(DATA_DIR, f"{user_id}.json")
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "user_id": user_id,
        "checkin": {},
        "test_status": {
            "weekly": False,
            "pressure": False,
            "communication": False
        },
        "last_checkin": ""
    }

def save_user_data(user_id: str, data: Dict[str, Any]):
    """保存用户数据"""
    data_file = os.path.join(DATA_DIR, f"{user_id}.json")
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# API端点
@router.post("/checkin")
async def submit_checkin(request: CheckinRequest):
    """提交心理状态打卡"""
    data = get_user_data(request.user_id)
    
    # 更新打卡数据
    if request.emotion:
        data["checkin"]["emotion"] = request.emotion
    if request.sleep:
        data["checkin"]["sleep"] = request.sleep
    if request.study:
        data["checkin"]["study"] = request.study
    if request.social:
        data["checkin"]["social"] = request.social
    
    # 更新最后打卡时间
    from datetime import datetime
    data["last_checkin"] = datetime.now().isoformat()
    
    save_user_data(request.user_id, data)
    
    return {"success": True, "message": "打卡成功"}

@router.post("/psych/test")
async def submit_psych_test(request: PsychTestRequest):
    """提交心理测试"""
    data = get_user_data(request.user_id)
    
    # 更新测试状态
    data["test_status"][request.test_type] = True
    
    save_user_data(request.user_id, data)
    
    return {"success": True, "message": "测试提交成功"}

@router.get("/psych/status/{user_id}")
async def get_psych_status(user_id: str):
    """获取心理状态"""
    data = get_user_data(user_id)
    
    return PsychStatusResponse(
        user_id=user_id,
        checkin=data["checkin"],
        test_status=data["test_status"],
        last_checkin=data["last_checkin"]
    )
