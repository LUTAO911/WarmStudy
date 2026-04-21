"""
Empathic Response Generator - 共情回应生成器
基于CBT原理的温暖共情对话生成
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from .emotion import EmotionType, EmotionDetector, get_emotion_detector


@dataclass
class EmpathicResponse:
    """共情回应"""
    response: str
    emotion_type: EmotionType
    use_rag: bool  # 是否使用了RAG知识库
    knowledge_used: List[str]  # 使用的知识库内容摘要


# 共情模板
EMPATHIC_TEMPLATES = {
    EmotionType.HAPPY: [
        "听到你这么开心，我也为你高兴呢！🌸 {specific}",
        "太棒了！你的努力有回报了呢！{specific}",
        "哇，听起来真的很棒！继续保持这份好心情！✨ {specific}",
    ],
    EmotionType.SAD: [
        "我能感受到你现在很难过，这种感觉真的很不好受... 🤍 {specific}",
        "听到你这么说，我有点心疼你。{specific}",
        "难过的时候不需要硬撑，说出来已经是很勇敢的事了。{specific}",
    ],
    EmotionType.ANXIOUS: [
        "我能理解你现在的紧张和担心，这种感觉确实让人不舒服... 🌸 {specific}",
        "压力大会让人喘不过气，你不是一个人。{specific}",
        "先深呼吸，我们慢慢来。{specific}",
    ],
    EmotionType.ANGRY: [
        "我能感觉到你现在很生气，换做是我可能也会这样。{specific}",
        "愤怒说明你在乎某些事情，我们可以聊聊。{specific}",
        "先冷静一下，我在这里听你说。{specific}",
    ],
    EmotionType.FEARFUL: [
        "听到你害怕，我有点担心你。别怕，我在这里陪着你。{specific}",
        "恐惧是很正常的反应，我们可以一起面对。{specific}",
        "不管发生什么，你都不是一个人。{specific}",
    ],
    EmotionType.ASHAMED: [
        "我能理解你的尴尬和不好意思，其实每个人都会有这样的时刻。{specific}",
        "不要太责怪自己，你已经做得很好了。{specific}",
        "这些都不代表什么，你依然很棒。{specific}",
    ],
    EmotionType.HOPEFUL: [
        "太好了！保持这份希望，一切都会好起来的！🌟 {specific}",
        "有希望就有力量，继续加油！{specific}",
        "这才是该有的样子！{specific}",
    ],
    EmotionType.HOPELESS: [
        "我知道你现在感到很绝望，但请相信，这只是暂时的。{specific}",
        "即使现在看不到光，也请不要放弃。{specific}",
        "让我陪着你，一起度过这个难关。{specific}",
    ],
    EmotionType.NEUTRAL: [
        "嗯，我听着呢。继续说吧。{specific}",
        "谢谢你分享。{specific}",
        "我在这里，你想说什么都可以。{specific}",
    ],
}

# 情绪特定回应
EMOTION_SPECIFIC = {
    EmotionType.HAPPY: [
        "能和我分享是什么让你这么开心吗？",
        "有什么特别的事情发生了吗？",
        "你的努力有回报了呢！",
    ],
    EmotionType.SAD: [
        "愿意告诉我发生了什么吗？",
        "是什么让你觉得难过呢？",
        "我在这里认真听你说。",
    ],
    EmotionType.ANXIOUS: [
        "是什么让你感到压力大呢？",
        "能说说具体是什么事情让你担心吗？",
        "深呼吸，我们一起想想办法。",
    ],
    EmotionType.ANGRY: [
        "是什么让你这么生气呢？",
        "愿意说说发生了什么事吗？",
        "我理解你的感受。",
    ],
    EmotionType.FEARFUL: [
        "是什么让你感到害怕呢？",
        "能告诉我你在担心什么吗？",
        "有我在，别害怕。",
    ],
    EmotionType.ASHAMED: [
        "能告诉我发生了什么吗？",
        "不要太责怪自己。",
        "每个人都会犯错，这很正常。",
    ],
    EmotionType.HOPEFUL: [
        "继续保持这份信心！",
        "你一定可以的！",
        "这很好！",
    ],
    EmotionType.HOPELESS: [
        "即使现在看不到希望，也请坚持下去。",
        "你对我来说很重要。",
        "让我陪着你。",
    ],
    EmotionType.NEUTRAL: [
        "嗯嗯，我在听。",
        "然后呢？",
        "你想聊什么呢？",
    ],
}


class EmpathicGenerator:
    """共情回应生成器"""
    
    def __init__(self):
        self.emotion_detector = get_emotion_detector()
        self.templates = EMPATHIC_TEMPLATES
        self.specific = EMOTION_SPECIFIC
        
    def generate(
        self,
        user_message: str,
        emotion_result=None,
        knowledge: List[str] = None
    ) -> EmpathicResponse:
        """
        生成共情回应
        
        Args:
            user_message: 用户消息
            emotion_result: 情绪识别结果（可选）
            knowledge: RAG检索到的知识（可选）
            
        Returns:
            EmpathicResponse: 共情回应
        """
        # 如果没有传入情绪结果，先检测
        if emotion_result is None:
            emotion_result = self.emotion_detector.detect(user_message)
        
        emotion = emotion_result.emotion
        
        # 选择回应模板
        import random
        template = random.choice(self.templates.get(emotion, self.templates[EmotionType.NEUTRAL]))
        specific = random.choice(self.specific.get(emotion, self.specific[EmotionType.NEUTRAL]))
        
        # 如果有RAG知识，融入回答
        use_rag = knowledge is not None and len(knowledge) > 0
        knowledge_used = []
        
        if use_rag:
            # 取最相关的一条知识
            main_knowledge = knowledge[0]
            knowledge_used.append(main_knowledge[:50] + "...")
            
            # 在回答中加入知识
            response = template.format(specific=f"\n\n{main_knowledge}\n\n{specific}")
        else:
            response = template.format(specific=f"\n\n{specific}")
        
        return EmpathicResponse(
            response=response,
            emotion_type=emotion,
            use_rag=use_rag,
            knowledge_used=knowledge_used
        )
    
    def generate_follow_up(
        self,
        emotion: EmotionType,
        topic: str = None
    ) -> str:
        """生成追问"""
        import random
        
        follow_ups = {
            EmotionType.SAD: [
                "愿意多说说吗？",
                "我在这里陪着你。",
                "发生了什么让你这么难过？",
            ],
            EmotionType.ANXIOUS: [
                "具体是什么事情让你担心呢？",
                "我们一起想想有什么办法。",
                "有什么我能帮到你的吗？",
            ],
            EmotionType.ANGRY: [
                "能说说是什么让你这么生气吗？",
                "我理解你的感受。",
                "说说会好受一些。",
            ],
            EmotionType.HOPELESS: [
                "我想帮你。你愿意告诉我更多吗？",
                "不管怎样，我都在这里。",
                "我们一起想办法。",
            ],
        }
        
        base = follow_ups.get(emotion, ["嗯嗯，我听着。"])
        return random.choice(base)


# 全局实例
_generator = None

def get_empathic_generator() -> EmpathicGenerator:
    """获取共情生成器单例"""
    global _generator
    if _generator is None:
        _generator = EmpathicGenerator()
    return _generator
