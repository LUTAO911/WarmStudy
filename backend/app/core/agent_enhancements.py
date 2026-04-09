"""智能体增强模块 - 规划和反思机制"""
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.llm import get_qwen_chat
import json

if TYPE_CHECKING:
    from app.core.agent import ConversationContext, AgentState, IntentType


class PlanningModule:
    """智能体规划模块"""

    PLANNING_PROMPT = """你是一个智能规划助手，负责为WarmStudy AI助手制定对话策略。

用户信息：
- 角色：{role}
- 历史对话：{history}
- 当前消息：{current_message}
- 识别的意图：{intent}
- 检测到的情绪：{emotion}
- 检索到的知识：{knowledge}

请基于以上信息，制定一个详细的对话策略，包括：
1. 对话目标（希望达成什么效果）
2. 对话步骤（如何逐步引导对话）
3. 关键要点（需要重点关注的内容）
4. 潜在风险（可能出现的问题及应对方案）
5. 预期结果（希望用户有什么反应）

请以JSON格式输出，键名分别为：
- "goal"
- "steps"
- "key_points"
- "risks"
- "expected_outcome"
"""

    def __init__(self):
        self.llm = get_qwen_chat()

    def generate_plan(self, context: 'ConversationContext', current_message: str, 
                     emotion: Dict[str, float], knowledge: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成对话规划"""
        try:
            # 构建历史对话
            history = []
            for msg in context.messages[-5:]:  # 只取最近5条消息
                if hasattr(msg, 'content'):
                    role = "user" if hasattr(msg, 'type') and msg.type == "human" else "assistant"
                    history.append(f"{role}: {msg.content}")
            history_str = "\n".join(history)

            # 构建知识摘要
            knowledge_str = []
            for item in knowledge[:3]:  # 只取前3条知识
                content = item.get("content", "")
                if content:
                    knowledge_str.append(f"- {content[:100]}...")
            knowledge_str = "\n".join(knowledge_str) if knowledge_str else "无"

            # 构建情绪信息
            emotion_str = ", ".join([f"{k}: {v:.2f}" for k, v in emotion.items()]) if emotion else "无"

            # 构建意图信息
            intent_str = context.intent.value if context.intent else "未知"

            # 构建角色信息
            role_str = "学生" if context.role == "student" else "家长"

            # 生成规划
            prompt = self.PLANNING_PROMPT.format(
                role=role_str,
                history=history_str,
                current_message=current_message,
                intent=intent_str,
                emotion=emotion_str,
                knowledge=knowledge_str
            )

            response = self.llm.invoke([HumanMessage(content=prompt)])
            plan_text = response.content.strip()

            # 解析JSON
            try:
                plan = json.loads(plan_text)
                return plan
            except json.JSONDecodeError:
                # 如果解析失败，返回默认规划
                return self._get_default_plan(context.intent)
        except Exception:
            return self._get_default_plan(context.intent)

    def _get_default_plan(self, intent: Optional['IntentType']) -> Dict[str, Any]:
        """获取默认规划"""
        # 尝试导入IntentType
        try:
            from app.core.agent import IntentType
            default_plans = {
                IntentType.EMOTION_SUPPORT: {
                    "goal": "提供情绪支持和安慰",
                    "steps": ["倾听用户感受", "表达理解和共情", "提供情感支持", "引导积极思考"],
                    "key_points": ["避免评判", "保持耐心", "给予肯定"],
                    "risks": ["用户情绪过于激动", "用户不愿意分享更多"],
                    "expected_outcome": "用户感觉被理解和支持"
                },
                IntentType.KNOWLEDGE_QUERY: {
                    "goal": "提供准确的知识信息",
                    "steps": ["理解问题", "检索相关知识", "整理信息", "清晰解释"],
                    "key_points": ["准确性", "易懂性", "实用性"],
                    "risks": ["信息不足", "用户理解困难"],
                    "expected_outcome": "用户获得所需知识"
                },
                IntentType.ASSESSMENT_GUIDANCE: {
                    "goal": "引导用户完成心理测评",
                    "steps": ["解释测评目的", "指导测评过程", "解读测评结果"],
                    "key_points": ["专业性", "耐心", "保密性"],
                    "risks": ["用户抵触测评", "结果解读困难"],
                    "expected_outcome": "用户完成测评并理解结果"
                },
                IntentType.PARENT_GUIDANCE: {
                    "goal": "提供科学的育儿指导",
                    "steps": ["理解家长困惑", "分析问题原因", "提供具体建议"],
                    "key_points": ["专业性", "实用性", "同理心"],
                    "risks": ["家长焦虑情绪", "建议执行困难"],
                    "expected_outcome": "家长获得有效的育儿方法"
                },
                IntentType.CASUAL_CHAT: {
                    "goal": "建立良好的关系",
                    "steps": ["积极回应", "话题扩展", "保持友好"],
                    "key_points": ["趣味性", "相关性", "尊重"],
                    "risks": ["话题中断", "用户兴趣转移"],
                    "expected_outcome": "对话愉快，关系融洽"
                }
            }
            return default_plans.get(intent, {
                "goal": "提供适当的回应",
                "steps": ["理解用户需求", "提供相关信息"],
                "key_points": ["准确性", "及时性"],
                "risks": ["信息不足"],
                "expected_outcome": "用户得到满意回应"
            })
        except ImportError:
            # 如果导入失败，返回默认规划
            return {
                "goal": "提供适当的回应",
                "steps": ["理解用户需求", "提供相关信息"],
                "key_points": ["准确性", "及时性"],
                "risks": ["信息不足"],
                "expected_outcome": "用户得到满意回应"
            }


class ReflectionModule:
    """智能体反思模块"""

    REFLECTION_PROMPT = """你是一个反思助手，负责评估WarmStudy AI助手的对话表现并提供改进建议。

对话历史：
{conversation_history}

AI回应：
{ai_response}

用户反馈：
{user_feedback}

请从以下维度评估AI的表现：
1. 准确性：信息是否准确可靠
2. 相关性：回应是否与用户需求相关
3. 同理心：是否体现理解和关怀
4. 有效性：是否解决了用户问题
5. 专业性：是否符合专业标准

并提供具体的改进建议。

请以JSON格式输出，键名分别为：
- "accuracy" (1-5分)
- "relevance" (1-5分)
- "empathy" (1-5分)
- "effectiveness" (1-5分)
- "professionalism" (1-5分)
- "improvement_suggestions" (改进建议数组)
"""

    def __init__(self):
        self.llm = get_qwen_chat()
        self.reflection_history: List[Dict[str, Any]] = []

    def reflect_on_conversation(self, conversation_history: List[Dict[str, Any]], 
                               ai_response: str, user_feedback: Optional[str] = None) -> Dict[str, Any]:
        """反思对话表现"""
        try:
            # 构建对话历史
            history_str = []
            for msg in conversation_history[-10:]:  # 只取最近10条消息
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                history_str.append(f"{role}: {content}")
            history_str = "\n".join(history_str)

            # 构建用户反馈
            feedback_str = user_feedback if user_feedback else "无明确反馈"

            # 生成反思
            prompt = self.REFLECTION_PROMPT.format(
                conversation_history=history_str,
                ai_response=ai_response,
                user_feedback=feedback_str
            )

            response = self.llm.invoke([HumanMessage(content=prompt)])
            reflection_text = response.content.strip()

            # 解析JSON
            try:
                reflection = json.loads(reflection_text)
                # 保存反思历史
                reflection["timestamp"] = datetime.now().isoformat()
                self.reflection_history.append(reflection)
                return reflection
            except json.JSONDecodeError:
                # 如果解析失败，返回默认反思
                return self._get_default_reflection()
        except Exception:
            return self._get_default_reflection()

    def _get_default_reflection(self) -> Dict[str, Any]:
        """获取默认反思"""
        return {
            "accuracy": 3,
            "relevance": 3,
            "empathy": 3,
            "effectiveness": 3,
            "professionalism": 3,
            "improvement_suggestions": ["继续保持专业态度", "增强与用户的互动", "提供更个性化的回应"]
        }

    def get_improvement_summary(self, limit: int = 5) -> Dict[str, Any]:
        """获取改进总结"""
        if not self.reflection_history:
            return {
                "average_scores": {
                    "accuracy": 3.0,
                    "relevance": 3.0,
                    "empathy": 3.0,
                    "effectiveness": 3.0,
                    "professionalism": 3.0
                },
                "common_suggestions": ["继续提升服务质量"],
                "strengths": ["基础服务能力良好"],
                "areas_for_improvement": ["个性化服务", "专业深度"]
            }

        recent_reflections = self.reflection_history[-limit:]
        
        # 计算平均分数
        scores = {
            "accuracy": sum(r.get("accuracy", 3) for r in recent_reflections) / len(recent_reflections),
            "relevance": sum(r.get("relevance", 3) for r in recent_reflections) / len(recent_reflections),
            "empathy": sum(r.get("empathy", 3) for r in recent_reflections) / len(recent_reflections),
            "effectiveness": sum(r.get("effectiveness", 3) for r in recent_reflections) / len(recent_reflections),
            "professionalism": sum(r.get("professionalism", 3) for r in recent_reflections) / len(recent_reflections)
        }

        # 提取改进建议
        suggestions = []
        for r in recent_reflections:
            suggestions.extend(r.get("improvement_suggestions", []))

        # 统计建议频率
        suggestion_counts = {}
        for s in suggestions:
            suggestion_counts[s] = suggestion_counts.get(s, 0) + 1

        # 获取常见建议
        common_suggestions = [s for s, c in sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)[:3]]

        # 分析优势和改进空间
        strengths = []
        areas_for_improvement = []

        if scores["empathy"] > 4:
            strengths.append("同理心强")
        elif scores["empathy"] < 3:
            areas_for_improvement.append("增强同理心")

        if scores["accuracy"] > 4:
            strengths.append("信息准确")
        elif scores["accuracy"] < 3:
            areas_for_improvement.append("提高信息准确性")

        if scores["effectiveness"] > 4:
            strengths.append("解决问题能力强")
        elif scores["effectiveness"] < 3:
            areas_for_improvement.append("提高问题解决能力")

        return {
            "average_scores": {k: round(v, 2) for k, v in scores.items()},
            "common_suggestions": common_suggestions,
            "strengths": strengths or ["基础服务能力良好"],
            "areas_for_improvement": areas_for_improvement or ["继续提升服务质量"]
        }


class SelfImprovementModule:
    """智能体自我改进模块"""

    IMPROVEMENT_PROMPT = """你是一个自我改进助手，负责基于反思结果优化WarmStudy AI助手的行为。

反思结果：
{reflection}

改进总结：
{improvement_summary}

请生成具体的改进策略，包括：
1. 短期改进目标（1-2周内可实现）
2. 长期改进方向（1-3个月）
3. 具体的行为调整建议
4. 需要重点关注的场景

请以JSON格式输出，键名分别为：
- "short_term_goals"
- "long_term_directions"
- "behavior_adjustments"
- "focus_scenarios"
"""

    def __init__(self):
        self.llm = get_qwen_chat()
        self.improvement_history: List[Dict[str, Any]] = []

    def generate_improvement_plan(self, reflection: Dict[str, Any], 
                                improvement_summary: Dict[str, Any]) -> Dict[str, Any]:
        """生成改进计划"""
        try:
            prompt = self.IMPROVEMENT_PROMPT.format(
                reflection=json.dumps(reflection, ensure_ascii=False),
                improvement_summary=json.dumps(improvement_summary, ensure_ascii=False)
            )

            response = self.llm.invoke([HumanMessage(content=prompt)])
            plan_text = response.content.strip()

            # 解析JSON
            try:
                plan = json.loads(plan_text)
                # 保存改进历史
                plan["timestamp"] = datetime.now().isoformat()
                self.improvement_history.append(plan)
                return plan
            except json.JSONDecodeError:
                # 如果解析失败，返回默认改进计划
                return self._get_default_improvement_plan()
        except Exception:
            return self._get_default_improvement_plan()

    def _get_default_improvement_plan(self) -> Dict[str, Any]:
        """获取默认改进计划"""
        return {
            "short_term_goals": [
                "提高响应速度",
                "增强同理心表达",
                "优化知识检索准确性"
            ],
            "long_term_directions": [
                "实现个性化服务",
                "扩展专业知识覆盖",
                "提升多模态交互能力"
            ],
            "behavior_adjustments": [
                "更加关注用户情绪变化",
                "提供更具体的建议",
                "保持专业而温暖的语气"
            ],
            "focus_scenarios": [
                "情绪危机处理",
                "复杂问题解答",
                "用户反馈处理"
            ]
        }


# 全局实例
planning_module = PlanningModule()
reflection_module = ReflectionModule()
self_improvement_module = SelfImprovementModule()


def get_planning_module() -> PlanningModule:
    """获取规划模块实例"""
    return planning_module


def get_reflection_module() -> ReflectionModule:
    """获取反思模块实例"""
    return reflection_module


def get_self_improvement_module() -> SelfImprovementModule:
    """获取自我改进模块实例"""
    return self_improvement_module
