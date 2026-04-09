"""LangChain Tools 工具实现"""
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, tool
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from app.config import get_settings
from app.db.base import get_db
from app.models import User, DailyCheckin, PsychAssessment

settings = get_settings()


class CheckinInput(BaseModel):
    user_id: str = Field(description="用户ID")
    days: int = Field(default=7, description="查询天数")


class KnowledgeInput(BaseModel):
    query: str = Field(description="搜索查询内容")
    top_k: int = Field(default=3, description="返回结果数量")


class AlertInput(BaseModel):
    user_id: str = Field(description="用户ID")
    alert_type: str = Field(description="预警类型: crisis, emotion, behavior")
    content: str = Field(description="预警内容")


class AssessmentInput(BaseModel):
    user_id: str = Field(description="用户ID")


class UserInfoInput(BaseModel):
    user_id: str = Field(description="用户ID")


def get_student_checkin(user_id: str, days: int = 7) -> Dict[str, Any]:
    """查询学生打卡数据"""
    db = get_db()
    try:
        from datetime import datetime, timedelta

        start_date = datetime.now() - timedelta(days=days)

        checkins = (
            db.query(DailyCheckin)
            .filter(
                DailyCheckin.user_id == user_id,
                DailyCheckin.checkin_date >= start_date
            )
            .order_by(DailyCheckin.checkin_date.desc())
            .all()
        )

        if not checkins:
            return {
                "success": True,
                "data": [],
                "message": "暂无打卡记录"
            }

        return {
            "success": True,
            "data": [
                {
                    "date": c.checkin_date.isoformat() if c.checkin_date else None,
                    "emotion": c.emotion_score,
                    "sleep": c.sleep_hours,
                    "study": c.study_hours,
                    "social": c.social_score,
                    "note": c.note
                }
                for c in checkins
            ],
            "count": len(checkins)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def search_knowledge_base(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """搜索知识库"""
    from app.rag.knowledge_base import get_knowledge_base
    try:
        kb = get_knowledge_base()
        results = kb.search(query, top_k)
        return results
    except Exception as e:
        return [{"error": str(e), "content": "知识库检索失败"}]


def send_crisis_alert(user_id: str, alert_type: str, content: str) -> Dict[str, Any]:
    """发送危机预警"""
    from app.models import CrisisAlert
    from datetime import datetime

    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "用户不存在"}

        alert = CrisisAlert(
            user_id=user_id,
            alert_type=alert_type,
            content=content,
            is_read=False,
            created_at=datetime.now()
        )
        db.add(alert)
        db.commit()

        return {
            "success": True,
            "message": "预警已发送",
            "alert_id": alert.id
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_latest_assessment(user_id: str) -> Dict[str, Any]:
    """获取最近一次测评"""
    db = get_db()
    try:
        assessment = (
            db.query(PsychAssessment)
            .filter(PsychAssessment.user_id == user_id)
            .order_by(PsychAssessment.created_at.desc())
            .first()
        )

        if not assessment:
            return {
                "success": True,
                "data": None,
                "message": "暂无测评记录"
            }

        return {
            "success": True,
            "data": {
                "id": assessment.id,
                "score": assessment.total_score,
                "risk_level": assessment.risk_level,
                "result": assessment.result,
                "created_at": assessment.created_at.isoformat() if assessment.created_at else None
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_user_info(user_id: str) -> Dict[str, Any]:
    """获取用户信息"""
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "用户不存在"}

        return {
            "success": True,
            "data": {
                "id": user.id,
                "name": user.name,
                "role": user.role,
                "phone": user.phone,
                "grade": user.grade if hasattr(user, 'grade') else None
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_chat_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """获取聊天历史"""
    db = get_db()
    try:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "role": "user" if not m.is_ai else "ai",
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in reversed(messages)
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


class GetUserInfoTool(BaseTool):
    """获取用户信息工具"""

    name: str = "get_user_info"
    description: str = "获取用户的基本信息，包括姓名、角色、手机号等。当需要了解用户背景时使用。"

    def _run(self, user_id: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        return get_user_info(user_id)

    async def _arun(self, user_id: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        return get_user_info(user_id)


class GetStudentCheckinTool(BaseTool):
    """学生打卡查询工具"""

    name: str = "get_student_checkin"
    description: str = "查询学生的每日打卡记录，包括情绪、睡眠、学习、社交评分。当用户询问自己的日常状态或历史记录时使用。"

    def _run(self, user_id: str, days: int = 7, run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        return get_student_checkin(user_id, days)

    async def _arun(self, user_id: str, days: int = 7, run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        return get_student_checkin(user_id, days)


class GetLatestAssessmentTool(BaseTool):
    """获取最近测评工具"""

    name: str = "get_latest_assessment"
    description: str = "获取用户最近一次心理测评的结果，包括评分、风险等级和建议。"

    def _run(self, user_id: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        return get_latest_assessment(user_id)

    async def _arun(self, user_id: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        return get_latest_assessment(user_id)


class GetChatHistoryTool(BaseTool):
    """获取聊天历史工具"""

    name: str = "get_chat_history"
    description: str = "获取用户与AI的历史对话记录，用于上下文理解和连续对话。"

    def _run(self, user_id: str, limit: int = 20, run_manager: Optional[CallbackManagerForToolRun] = None) -> List[Dict[str, Any]]:
        return get_chat_history(user_id, limit)

    async def _arun(self, user_id: str, limit: int = 20, run_manager: Optional[CallbackManagerForToolRun] = None) -> List[Dict[str, Any]]:
        return get_chat_history(user_id, limit)


class SearchKnowledgeTool(BaseTool):
    """知识库检索工具"""

    name: str = "search_knowledge"
    description: str = "搜索心理健康相关的知识库内容。当用户询问心理知识、情绪调节方法、压力管理技巧等问题时使用。"

    def _run(self, query: str, top_k: int = 3, run_manager: Optional[CallbackManagerForToolRun] = None) -> List[Dict[str, Any]]:
        return search_knowledge_base(query, top_k)

    async def _arun(self, query: str, top_k: int = 3, run_manager: Optional[CallbackManagerForToolRun] = None) -> List[Dict[str, Any]]:
        return search_knowledge_base(query, top_k)


class SendCrisisAlertTool(BaseTool):
    """危机预警通知工具"""

    name: str = "send_crisis_alert"
    description: str = "当识别到用户有自伤、自杀倾向或严重心理危机时，发送预警通知给家长和老师。这是最重要的安全工具。"

    def _run(self, user_id: str, alert_type: str = "crisis", content: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        return send_crisis_alert(user_id, alert_type, content)

    async def _arun(self, user_id: str, alert_type: str = "crisis", content: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        return send_crisis_alert(user_id, alert_type, content)


TOOLS = [
    GetUserInfoTool(),
    GetStudentCheckinTool(),
    GetLatestAssessmentTool(),
    GetChatHistoryTool(),
    SearchKnowledgeTool(),
    SendCrisisAlertTool(),
]


def get_all_tools() -> List[BaseTool]:
    """获取所有工具列表"""
    return TOOLS


def get_tools_dict() -> Dict[str, BaseTool]:
    """获取工具字典"""
    return {tool.name: tool for tool in TOOLS}