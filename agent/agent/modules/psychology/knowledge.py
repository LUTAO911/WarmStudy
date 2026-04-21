"""
Psychology Knowledge Base - 心理知识库
RAG检索用的心理知识内容
"""

import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str
    title: str
    category: str
    user_type: str  # student/parent/teacher
    content: str
    keywords: List[str]
    emotions: List[str]  # 关联的情绪类型

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "user_type": self.user_type,
            "content": self.content,
            "keywords": self.keywords,
            "emotions": self.emotions,
        }


# 内置心理知识库（用于演示）
PSYCHOLOGY_KNOWLEDGE = [
    # ============ 考试焦虑类 ============
    KnowledgeEntry(
        id="exam_anxiety_001",
        title="考试焦虑的认知行为疗法（CBT）干预",
        category="考试心理",
        user_type="student",
        content="""考试焦虑是青少年常见的心理困扰。CBT认为，焦虑来自于对考试的负面认知。

试试这个方法：
1. 识别负面想法：如"我一定会考砸"
2. 挑战这些想法：问自己"有什么证据支持这个想法？"
3. 建立更平衡的认知：如"我准备得不错，尽力就好"

另外，深呼吸（4-7-8呼吸法）也很有效：吸气4秒，屏住呼吸7秒，呼气8秒。""",
        keywords=["考试焦虑", "CBT", "深呼吸", "放松", "负面想法", "认知重构"],
        emotions=["anxious", "fearful"]
    ),
    KnowledgeEntry(
        id="exam_anxiety_002",
        title="如何克服考试前的紧张？",
        category="考试心理",
        user_type="student",
        content="""考试前紧张是很正常的反应，但过度紧张会影响发挥。

试试这些方法：
1. 提前熟悉考场环境，减少陌生感
2. 提前准备好考试用品，避免临时慌张
3. 考前做些轻度运动，帮助放松
4. 告诉自己"我准备好了"
5. 考试时先做简单的题，建立信心

记住，考试只是检验学习效果的一种方式，不是衡量你价值的标准。""",
        keywords=["考试紧张", "放松技巧", "考前准备", "自信心"],
        emotions=["anxious", "fearful"]
    ),
    
    # ============ 学习压力类 ============
    KnowledgeEntry(
        id="study_stress_001",
        title="如何合理应对学习压力",
        category="压力管理",
        user_type="student",
        content="""学习压力来自各个方面：作业、考试、家长期望...

应对压力的方法：
1. 分解任务：把大任务分解成小步骤
2. 制定计划：合理安排学习和休息时间
3. 适当运动：运动可以释放压力
4. 充足睡眠：不要熬夜学习，效率反而更高
5. 寻求支持：和父母、老师、朋友聊聊

记住，压力不一定是坏事，适度的压力可以成为动力。""",
        keywords=["学习压力", "时间管理", "放松", "休息", "计划"],
        emotions=["anxious", "sad"]
    ),
    
    # ============ 人际关系类 ============
    KnowledgeEntry(
        id="friendship_001",
        title="和同学闹矛盾了怎么办？",
        category="人际关系",
        user_type="student",
        content="""朋友之间的摩擦是难免的，关键是如何处理。

处理矛盾的步骤：
1. 先冷静下来，不要在情绪激动时处理
2. 试着理解对方的立场
3. 找一个合适的时机，平和地表达你的感受
4. 倾听对方的想法
5. 一起想办法解决问题

如果矛盾无法自己解决，可以寻求老师或家长的帮助。

记住，真正的友谊是经得起考验的。""",
        keywords=["朋友矛盾", "人际冲突", "沟通", "和好"],
        emotions=["sad", "angry"]
    ),
    KnowledgeEntry(
        id="friendship_002",
        title="被同学孤立了怎么办？",
        category="人际关系",
        user_type="student",
        content="""被孤立是一种很痛苦的体验，首先要告诉自己：这不是你的错。

可以尝试：
1. 找到支持你的人，哪怕只有一个
2. 尝试加入新的朋友圈
3. 培养自己的兴趣爱好，让自己变得更自信
4. 如果情况严重，告诉老师或家长

记住，你值得被善待。孤独只是暂时的。""",
        keywords=["被孤立", "人际困扰", "孤独", "自信"],
        emotions=["sad", "fearful", "ashamed"]
    ),
    
    # ============ 家庭关系类 ============
    KnowledgeEntry(
        id="family_001",
        title="家长总是不理解我怎么办？",
        category="亲子沟通",
        user_type="student",
        content="""父母和孩子之间有代沟是很常见的，试试这些方法：

1. 选择合适的时机沟通
2. 用"我觉得..."的表达方式，而不是"你总是..."
3. 试着理解父母的担心
4. 用行动证明你的能力和责任感
5. 给父母写一封信，表达你的真实感受

有时候，父母不是不理解，而是不知道如何表达关心。""",
        keywords=["家长不理解", "代沟", "沟通", "亲子关系"],
        emotions=["sad", "angry"]
    ),
    
    # ============ 情绪管理类 ============
    KnowledgeEntry(
        id="emotion_001",
        title="情绪低落时该怎么办？",
        category="情绪管理",
        user_type="student",
        content="""每个人都会有情绪低落的时刻，这些方法可能有帮助：

1. 允许自己感受情绪，不要压抑
2. 和信任的人聊聊
3. 做些让你开心的事（听音乐、看电影、运动）
4. 写日记记录心情
5. 出去走走，接触大自然
6. 做一些放松练习

如果情绪低落持续很长时间（如两周以上），建议寻求专业帮助。""",
        keywords=["情绪低落", "抑郁情绪", "自我调节", "放松"],
        emotions=["sad", "hopeless"]
    ),
    KnowledgeEntry(
        id="emotion_002",
        title="如何正确表达情绪？",
        category="情绪管理",
        user_type="student",
        content="""情绪没有对错，重要的是如何表达：

1. 识别自己的情绪：现在我感到...
2. 接纳情绪：这是正常的反应
3. 选择合适的表达方式：
   - 和朋友倾诉
   - 写日记
   - 运动发泄
   - 找人谈谈
4. 避免伤害自己或他人的方式

学会表达情绪是成长的重要部分。""",
        keywords=["情绪表达", "情绪管理", "沟通"],
        emotions=["angry", "sad", "anxious"]
    ),
    
    # ============ 自我认知类 ============
    KnowledgeEntry(
        id="self_001",
        title="如何建立自信心？",
        category="自我认知",
        user_type="student",
        content="""自信不是天生的，是可以培养的：

1. 记录自己的成就，无论大小
2. 设定可实现的目标，每完成一个就给自己肯定
3. 停止和别人比较，专注于自己的成长
4. 改变体态：抬头挺胸
5. 用积极的语言和自己对话
6. 接受自己的不完美

记住，你的价值不是由成绩或别人的评价决定的。""",
        keywords=["自信心", "自我认知", "成就", "成长"],
        emotions=["sad", "ashamed", "hopeless"]
    ),
    
    # ============ CBT原理类 ============
    KnowledgeEntry(
        id="cbt_001",
        title="什么是认知行为疗法（CBT）？",
        category="心理学知识",
        user_type="student",
        content="""CBT是一种常用的心理治疗方法，核心观点是：

我们的情绪不是由事件本身引起的，而是由我们对事件的看法引起的。

例如：考试成绩不好
- 负面想法："我真笨，什么都做不好"
- 可能导致：沮丧、自暴自弃

- 平衡想法："这次没考好，但我一直在进步"
- 可能导致：接受现实、继续努力

CBT教我们识别和改变不健康的思维模式。""",
        keywords=["CBT", "认知行为疗法", "思维模式", "心理治疗"],
        emotions=["anxious", "sad", "angry"]
    ),
    
    # ============ 家长专用的 ============
    KnowledgeEntry(
        id="parent_001",
        title="如何与青春期的孩子沟通？",
        category="亲子沟通",
        user_type="parent",
        content="""青春期孩子的大脑还在发育，情绪波动是正常的。

沟通建议：
1. 多倾听，少说教
2. 尊重孩子的隐私
3. 避免使用命令式语言
4. 表达关心时注意方式
5. 保持稳定的亲子关系

青春期的孩子需要的是理解和支持，而不是控制和批评。""",
        keywords=["青春期", "亲子沟通", "家长", "倾听"],
        emotions=["anxious", "angry"]
    ),
    KnowledgeEntry(
        id="parent_002",
        title="如何发现孩子心理问题的预警信号？",
        category="心理健康",
        user_type="parent",
        content="""需要关注的预警信号：
1. 情绪持续低落超过两周
2. 睡眠和食欲明显改变
3. 不想和任何人交流
4. 对以前喜欢的事物失去兴趣
5. 成绩突然大幅下降
6. 提到"没意思"、"不想活"等

发现这些信号时，请和孩子好好谈谈，必要时寻求专业帮助。""",
        keywords=["预警信号", "心理问题", "家长", "抑郁"],
        emotions=["sad", "hopeless"]
    ),
    
    # ============ 教师专用的 ============
    KnowledgeEntry(
        id="teacher_001",
        title="如何识别学生的心理困扰？",
        category="学生心理",
        user_type="teacher",
        content="""教师是学生心理问题的重要防线。

预警信号：
1. 行为突然改变（更内向或更暴躁）
2. 学业表现突然下滑
3. 与同学关系急剧恶化
4. 经常说身体不适（头疼、胃疼等）
5. 注意力不集中，记忆力下降

发现这些情况，可以私下关心学生，必要时建议家长寻求专业帮助。""",
        keywords=["学生心理", "预警信号", "教师", "识别"],
        emotions=["sad", "anxious"]
    ),
]


class PsychologyKnowledgeBase:
    """心理知识库"""
    
    def __init__(self):
        self.knowledge = PSYCHOLOGY_KNOWLEDGE
        self._build_index()
        
    def _build_index(self):
        """构建知识索引"""
        self.category_index: Dict[str, List[KnowledgeEntry]] = {}
        self.user_type_index: Dict[str, List[KnowledgeEntry]] = {}
        self.keyword_index: Dict[str, List[KnowledgeEntry]] = {}
        
        for entry in self.knowledge:
            # 按类别索引
            if entry.category not in self.category_index:
                self.category_index[entry.category] = []
            self.category_index[entry.category].append(entry)
            
            # 按用户类型索引
            if entry.user_type not in self.user_type_index:
                self.user_type_index[entry.user_type] = []
            self.user_type_index[entry.user_type].append(entry)
            
            # 按关键词索引
            for keyword in entry.keywords:
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = []
                self.keyword_index[keyword].append(entry)
    
    def search(
        self,
        query: str,
        user_type: str = "student",
        top_k: int = 3
    ) -> List[KnowledgeEntry]:
        """
        搜索相关知识
        
        Args:
            query: 查询文本
            user_type: 用户类型
            top_k: 返回数量
            
        Returns:
            List[KnowledgeEntry]: 相关知识列表
        """
        # 简单关键词匹配
        query_lower = query.lower()
        scored_entries: Dict[str, float] = {}
        
        for entry in self.knowledge:
            score = 0.0
            
            # 用户类型匹配
            if entry.user_type == user_type or entry.user_type == "student":
                score += 2.0
            
            # 标题匹配
            for keyword in entry.keywords:
                if keyword in query_lower:
                    score += 1.0
            
            # 内容关键词匹配
            for keyword in entry.keywords:
                if keyword in query_lower:
                    if keyword in entry.content:
                        score += 0.5
            
            if score > 0:
                scored_entries[entry.id] = score
        
        # 按分数排序
        sorted_ids = sorted(scored_entries.items(), key=lambda x: x[1], reverse=True)
        
        # 返回top_k
        results = []
        for entry_id, _ in sorted_ids[:top_k]:
            for entry in self.knowledge:
                if entry.id == entry_id:
                    results.append(entry)
                    break
        
        return results
    
    def get_by_category(
        self,
        category: str,
        user_type: str = "student"
    ) -> List[KnowledgeEntry]:
        """获取指定类别的知识"""
        results = []
        for entry in self.knowledge:
            if entry.category == category and (entry.user_type == user_type or entry.user_type == "student"):
                results.append(entry)
        return results
    
    def get_random(self, user_type: str = "student", count: int = 3) -> List[KnowledgeEntry]:
        """获取随机知识"""
        import random
        pool = [e for e in self.knowledge if e.user_type == user_type or e.user_type == "student"]
        return random.sample(pool, min(count, len(pool)))

    def get_categories(self, user_type: str = "student") -> List[str]:
        """获取所有知识分类"""
        categories = set()
        for entry in self.knowledge:
            if entry.user_type == user_type or entry.user_type == "student":
                categories.add(entry.category)
        return sorted(list(categories))


# 全局实例
_knowledge_base = None

def get_psychology_knowledge_base() -> PsychologyKnowledgeBase:
    """获取心理知识库单例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = PsychologyKnowledgeBase()
    return _knowledge_base
