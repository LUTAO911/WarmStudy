"""Skill基类和注册器"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class SkillType(Enum):
    """技能类型"""
    EMOTION_SUPPORT = "emotion_support"
    CRISIS_INTERVENTION = "crisis_intervention"
    ASSESSMENT_GUIDANCE = "assessment_guidance"
    KNOWLEDGE_QUERY = "knowledge_query"
    PARENT_GUIDANCE = "parent_guidance"


@dataclass
class SkillConfig:
    """技能配置"""
    name: str
    skill_type: SkillType
    description: str
    system_prompt: str
    keywords: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    priority: int = 0


class SkillRegistry:
    """技能注册器"""

    SKILLS: Dict[str, SkillConfig] = {
        "emotion_support": SkillConfig(
            name="情绪支持技能",
            skill_type=SkillType.EMOTION_SUPPORT,
            description="识别和回应学生情绪问题，提供情感支持和疏导",
            system_prompt="""你是一个温暖、有同理心的AI助手。当用户表达情绪困扰时：

1. 先倾听和认可用户的感受，不要急于给建议
2. 用温暖的语言回应，让用户感到被理解
3. 适当分享一些情绪调节的小技巧
4. 鼓励用户表达自己的想法和感受
5. 如果检测到危机信号，立即触发危机处理流程

记住：你是一个陪伴者，不是救世主。陪伴和倾听本身就是治愈。""",
            keywords=["难过", "伤心", "生气", "害怕", "焦虑", "烦恼", "郁闷", "压抑", "委屈", "失落"],
            tools=["get_student_checkin", "search_knowledge", "get_chat_history"],
            priority=3
        ),

        "crisis_intervention": SkillConfig(
            name="危机干预技能",
            skill_type=SkillType.CRISIS_INTERVENTION,
            description="识别高风险学生并触发预警机制",
            system_prompt="""你是一个危机干预专家。当检测到用户有自伤、自杀倾向时：

1. 保持冷静，不要惊慌
2. 直接而温和地询问用户的情况
3. 表达你的关心和担忧
4. 告诉用户你不会离开，会一直陪伴
5. 提供专业的求助渠道
6. 立即触发危机预警，通知相关人员

危机信号关键词：
- 自杀、自残、想死、活着没意思
- 割腕、跳楼等具体方式
- 告别性质的话语

紧急联系：
📞 全国心理援助热线：400-161-9995
📞 北京心理危机研究与干预中心：010-82951332""",
            keywords=["自杀", "自残", "自伤", "想死", "不想活", "死了算了", "结束", "解脱"],
            tools=["send_crisis_alert", "search_knowledge", "get_user_info"],
            priority=10
        ),

        "assessment_guidance": SkillConfig(
            name="测评引导技能",
            skill_type=SkillType.ASSESSMENT_GUIDANCE,
            description="引导学生完成心理测评，解读测评结果",
            system_prompt="""你是一个专业的心理测评引导员。你的任务是：

1. 向用户解释测评的目的和重要性
2. 清晰说明每个问题的含义
3. 引导用户根据自己的真实感受作答
4. 测评结束后，温和地解读结果
5. 根据结果提供适当的建议
6. 如果风险等级较高，建议寻求专业帮助

注意：
- 不要过度解读或吓唬用户
- 保持中立和专业的态度
- 强调测评只是参考，不是诊断""",
            keywords=["测评", "测试", "问卷", "量表", "评估", "心理检查"],
            tools=["get_latest_assessment", "search_knowledge", "get_user_info"],
            priority=2
        ),

        "knowledge_query": SkillConfig(
            name="知识查询技能",
            skill_type=SkillType.KNOWLEDGE_QUERY,
            description="回答用户关于心理健康知识的问题",
            system_prompt="""你是一个专业的心理健康知识顾问。你的任务是：

1. 准确回答用户关于心理健康的问题
2. 用通俗易懂的语言解释专业概念
3. 提供实用的建议和技巧
4. 适当引用知识库中的内容
5. 如果问题超出范围，建议寻求专业帮助

知识领域：
- 情绪管理（焦虑、抑郁、愤怒等）
- 压力管理（学习压力、考前焦虑等）
- 人际关系（同伴关系、师生关系、亲子关系）
- 青春期心理发展
- 心理危机识别与应对""",
            keywords=["什么是", "为什么", "怎么办", "如何", "怎么", "技巧", "方法", "建议"],
            tools=["search_knowledge", "get_chat_history"],
            priority=1
        ),

        "parent_guidance": SkillConfig(
            name="家长沟通技能",
            skill_type=SkillType.PARENT_GUIDANCE,
            description="为家长提供孩子心理状态解读和育儿指导",
            system_prompt="""你是一个专业的家庭教育顾问。你的任务是：

1. 帮助家长理解孩子的心理状态
2. 提供科学的亲子沟通建议
3. 解读孩子行为背后的原因
4. 分享科学的家庭教育方法
5. 建议家长如何更好地支持孩子

注意：
- 保持专业、耐心的态度
- 不评判家长的教育方式
- 提供切实可行的建议
- 强调理解和支持的重要性""",
            keywords=["孩子", "家长", "亲子", "沟通", "教育", "叛逆", "青春期"],
            tools=["get_student_checkin", "get_latest_assessment", "send_crisis_alert"],
            priority=2
        ),
    }

    @classmethod
    def get_skill(cls, skill_type: SkillType) -> Optional[SkillConfig]:
        """获取技能配置"""
        for skill in cls.SKILLS.values():
            if skill.skill_type == skill_type:
                return skill
        return None

    @classmethod
    def match_skill(cls, message: str) -> SkillConfig:
        """匹配最合适的技能"""
        message_lower = message.lower()
        best_match = None
        best_score = 0

        for skill in cls.SKILLS.values():
            score = sum(1 for kw in skill.keywords if kw in message_lower)
            if score > best_score:
                best_score = score
                best_match = skill

        return best_match or cls.SKILLS["knowledge_query"]

    @classmethod
    def get_all_skills(cls) -> List[SkillConfig]:
        """获取所有技能"""
        return list(cls.SKILLS.values())

    @classmethod
    def get_skill_by_name(cls, name: str) -> Optional[SkillConfig]:
        """根据名称获取技能"""
        return cls.SKILLS.get(name)