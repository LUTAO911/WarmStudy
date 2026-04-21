"""
教育功能工具集 - Teaching Education Tools
版本: 1.0
功能: 助教、助学、助评、助管、助育
"""
import time
import json
import re
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    UNKNOWN = "unknown"


class QuestionType(Enum):
    CHOICE = "choice"
    BLANK = "blank"
    ESSAY = "essay"
    CODE = "code"
    CALCULATION = "calculation"


@dataclass
class Question:
    question_id: str
    type: QuestionType
    content: str
    answer: str
    difficulty: Difficulty
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "type": self.type.value,
            "content": self.content,
            "answer": self.answer,
            "difficulty": self.difficulty.value,
            "explanation": self.explanation,
            "metadata": self.metadata
        }


@dataclass
class EvaluationResult:
    score: float
    max_score: float
    feedback: str
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "max_score": self.max_score,
            "score_percent": round(self.score / max(self.max_score, 1) * 100, 1),
            "feedback": self.feedback,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions
        }


@dataclass
class LearningPath:
    student_id: str
    current_level: str
    goal: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_hours: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "current_level": self.current_level,
            "goal": self.goal,
            "steps": self.steps,
            "estimated_hours": self.estimated_hours
        }


class TeachingAssistant:
    """助教模块 - 辅助教师完成教学工作"""

    def __init__(self):
        self._question_templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        return {
            "math": {
                "choice": ["选择题模板"],
                "blank": ["填空题模板"],
                "calculation": ["计算题模板"]
            },
            "programming": {
                "code": ["编程题模板"],
                "choice": ["概念选择题模板"]
            },
            "general": {
                "essay": ["简答题模板"]
            }
        }

    def generate_homework(
        self,
        topic: str,
        difficulty: str = "medium",
        count: int = 5,
        question_types: Optional[List[str]] = None
    ) -> List[Question]:
        """生成作业题目"""
        questions = []
        diff = Difficulty(difficulty) if difficulty in [d.value for d in Difficulty] else Difficulty.MEDIUM

        types = question_types or ["choice", "blank", "essay"]

        for i in range(count):
            q_type = types[i % len(types)]
            q = Question(
                question_id=f"hw_{int(time.time())}_{i}",
                type=QuestionType(q_type),
                content=self._generate_question_content(topic, q_type, diff),
                answer=self._generate_answer(topic, q_type),
                difficulty=diff,
                explanation=self._generate_explanation(topic, q_type)
            )
            questions.append(q)

        return questions

    def _generate_question_content(self, topic: str, q_type: str, difficulty: Difficulty) -> str:
        templates = {
            "choice": f"关于{topic}的说法，以下哪一项是正确的？\nA. 正确选项\nB. 错误选项\nC. 错误选项\nD. 错误选项",
            "blank": f"请填写下划线空白处：\n{topic}的核心理念是___，它解决了什么问题？",
            "essay": f"请简述{topic}的主要特点及其应用场景（不少于200字）",
            "calculation": f"计算题：已知条件A={random.randint(1,10)}，条件B={random.randint(1,10)}，求{topic}的结果",
            "code": f"编程题：实现一个函数，输入参数为{topic}，输出相应结果"
        }
        return templates.get(q_type, f"请回答关于{topic}的问题")

    def _generate_answer(self, topic: str, q_type: str) -> str:
        answers = {
            "choice": "A",
            "blank": "核心理念是解决实际问题",
            "essay": "主要特点：1. 创新性 2. 实用性 3. 可扩展性。应用场景：教育、医疗、金融等",
            "calculation": str(random.randint(10, 100)),
            "code": "def solution(param):\n    return result"
        }
        return answers.get(q_type, f"关于{topic}的标准答案")

    def _generate_explanation(self, topic: str, q_type: str) -> str:
        return f"本题考察{topic}相关知识点，理解{topic}的核心概念即可作答"

    def grade_homework(
        self,
        questions: List[Dict],
        student_answers: List[str]
    ) -> EvaluationResult:
        """批改作业"""
        if len(questions) != len(student_answers):
            raise ValueError("题目数量与学生答案数量不匹配")

        total_score = 0
        max_score = len(questions) * 10
        strengths = []
        weaknesses = []
        feedbacks = []

        for i, (q, answer) in enumerate(zip(questions, student_answers)):
            is_correct = self._check_answer(q.get("answer", ""), answer)
            if is_correct:
                total_score += 10
                strengths.append(f"第{i+1}题回答正确")
            else:
                weaknesses.append(f"第{i+1}题需要加强")
                feedbacks.append(f"第{i+1}题标准答案：{q.get('answer', '')}")

        score_percent = total_score / max(max_score, 1) * 100
        if score_percent >= 90:
            feedback = "优秀！继续保持"
        elif score_percent >= 70:
            feedback = "良好，还有提升空间"
        else:
            feedback = "需要加强学习，建议复习相关内容"

        return EvaluationResult(
            score=total_score,
            max_score=max_score,
            feedback=feedback,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=[f"建议复习{', '.join(weaknesses[:2])}"]
        )

    def _check_answer(self, correct: str, student: str) -> bool:
        correct_clean = re.sub(r'\s+', '', correct.lower())
        student_clean = re.sub(r'\s+', '', student.lower())
        return correct_clean == student_clean or correct_clean in student_clean

    def generate_lecture_notes(self, topic: str, include_examples: bool = True) -> Dict[str, Any]:
        """生成课件/讲义"""
        return {
            "title": f"{topic} 教学讲义",
            "duration": "45分钟",
            "objectives": [
                f"理解{topic}的基本概念",
                f"掌握{topic}的核心原理",
                f"能够应用{topic}解决实际问题"
            ],
            "outline": [
                {"section": "1. 引入", "time": "5分钟", "content": f"通过{topic}的实际应用场景引入"},
                {"section": "2. 概念讲解", "time": "15分钟", "content": f"详细讲解{topic}的定义和特点"},
                {"section": "3. 原理解析", "time": "15分钟", "content": f"深入分析{topic}的工作原理"},
                {"section": "4. 实践演示", "time": "5分钟", "content": "实际案例演示" if include_examples else "理论说明"},
                {"section": "5. 总结", "time": "5分钟", "content": "回顾重点、布置作业"}
            ],
            "key_points": [f"{topic}的核心要点1", f"{topic}的核心要点2", f"{topic}的核心要点3"],
            "homework": f"完成关于{topic}的练习题"
        }


class LearningSupport:
    """助学模块 - 支持学生学习"""

    def __init__(self):
        self._concepts_db = {}

    def assess_student_level(self, student_id: str, answers: List[Dict]) -> str:
        """评估学生水平"""
        if not answers:
            return "beginner"

        correct_count = sum(1 for a in answers if a.get("correct", False))
        accuracy = correct_count / max(len(answers), 1)

        if accuracy >= 0.9:
            return "advanced"
        elif accuracy >= 0.7:
            return "intermediate"
        elif accuracy >= 0.5:
            return "elementary"
        else:
            return "beginner"

    def plan_learning_path(
        self,
        student_level: str,
        goal: str,
        available_hours: float = 10.0
    ) -> LearningPath:
        """规划学习路径"""
        levels = {
            "beginner": ["基础概念", "入门知识", "初级应用"],
            "elementary": ["核心概念", "基本原理", "简单实践"],
            "intermediate": ["深入原理", "高级特性", "项目实践"],
            "advanced": ["高级应用", "最佳实践", "项目实战"]
        }

        steps = []
        current_hours = 0.0
        step_hours = available_hours / 4

        for i, topic in enumerate(levels.get(student_level, levels["beginner"])):
            steps.append({
                "step": i + 1,
                "topic": topic,
                "description": f"学习{topic}相关内容",
                "hours": step_hours,
                "resources": [
                    f"{topic}讲义",
                    f"{topic}练习题",
                    f"{topic}视频教程"
                ]
            })
            current_hours += step_hours

        return LearningPath(
            student_id=student_level,
            current_level=student_level,
            goal=goal,
            steps=steps,
            estimated_hours=current_hours
        )

    def explain_concept(self, concept: str, level: str = "intermediate") -> Dict[str, Any]:
        """讲解知识点"""
        explanations = {
            "beginner": f"{concept}是一个非常基础的概念。简单来说，它就像是... (通俗易懂的解释)",
            "intermediate": f"{concept}是{concept}领域的核心概念之一。它的主要特点是... (中等深度的解释)",
            "advanced": f"从更深层次来看，{concept}涉及到... (深入专业的解释)"
        }

        return {
            "concept": concept,
            "level": level,
            "definition": explanations.get(level, explanations["intermediate"]),
            "examples": [
                {"scenario": "例1", "explanation": f"在{concept}中，第一个例子是..."},
                {"scenario": "例2", "explanation": f"在{concept}中，第二个例子是..."}
            ],
            "related_concepts": [f"{concept}相关概念1", f"{concept}相关概念2"],
            "practice_tips": [
                "多做练习加深理解",
                "结合实际案例学习",
                "及时复习巩固"
            ]
        }

    def generate_practice(
        self,
        topic: str,
        count: int = 5,
        difficulty: str = "medium"
    ) -> List[Question]:
        """生成练习题"""
        assistant = TeachingAssistant()
        return assistant.generate_homework(topic, difficulty, count)


class AssessmentSystem:
    """助评模块 - 评价与反馈"""

    def evaluate_answer(
        self,
        question: str,
        correct_answer: str,
        student_answer: str,
        rubric: Optional[Dict] = None
    ) -> EvaluationResult:
        """评价学生答案"""
        correct_clean = re.sub(r'\s+', '', correct_answer.lower())
        student_clean = re.sub(r'\s+', '', student_answer.lower())

        similarity = self._calculate_similarity(correct_clean, student_clean)

        if similarity >= 0.9:
            score = 100
            feedback = "完美！答案完全正确"
            strengths = ["准确理解题意", "答案完整"]
            weaknesses = []
        elif similarity >= 0.7:
            score = 85
            feedback = "很好！答案基本正确"
            strengths = ["理解正确", "思路清晰"]
            weaknesses = ["细节需要完善"]
        elif similarity >= 0.5:
            score = 70
            feedback = "良好，有一定理解"
            strengths = ["基本概念正确"]
            weaknesses = ["答案不够完整", "需要补充细节"]
        elif similarity >= 0.3:
            score = 50
            feedback = "需要加强学习"
            strengths = []
            weaknesses = ["概念理解有偏差", "需要重新复习"]
        else:
            score = 30
            feedback = "理解有误，建议重新学习相关内容"
            strengths = []
            weaknesses = ["答案偏离主题", "需要系统学习"]

        return EvaluationResult(
            score=score,
            max_score=100,
            feedback=feedback,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=self._generate_suggestions(similarity, question)
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0

        set1 = set(text1)
        set2 = set(text2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / max(union, 1)

    def _generate_suggestions(self, similarity: float, question: str) -> List[str]:
        if similarity >= 0.9:
            return ["可以挑战更高难度的问题"]
        elif similarity >= 0.7:
            return ["注意检查细节", "确保答案完整"]
        elif similarity >= 0.5:
            return ["建议复习相关知识点", "多做练习巩固"]
        else:
            return ["重新学习相关内容", "寻求老师帮助", "观看教学视频"]

    def generate_report(
        self,
        student_id: str,
        evaluations: List[EvaluationResult],
        period: str = "week"
    ) -> Dict[str, Any]:
        """生成评价报告"""
        if not evaluations:
            return {"error": "暂无评价数据"}

        avg_score = sum(e.score for e in evaluations) / len(evaluations)

        all_strengths = []
        all_weaknesses = []
        for e in evaluations:
            all_strengths.extend(e.strengths)
            all_weaknesses.extend(e.weaknesses)

        return {
            "student_id": student_id,
            "period": period,
            "summary": {
                "total_questions": len(evaluations),
                "average_score": round(avg_score, 1),
                "score_percent": round(avg_score, 1)
            },
            "strengths": list(set(all_strengths))[:3],
            "areas_for_improvement": list(set(all_weaknesses))[:3],
            "recommendations": [
                "继续保持当前的学习节奏",
                "针对薄弱环节加强练习",
                "定期复习巩固已学知识"
            ],
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def track_progress(self, student_id: str, history: List[Dict]) -> List[Dict[str, Any]]:
        """追踪学习进度"""
        if not history:
            return []

        progress = []
        for i, record in enumerate(history):
            progress.append({
                "date": record.get("date", ""),
                "topic": record.get("topic", ""),
                "score": record.get("score", 0),
                "trend": "up" if i > 0 and record.get("score", 0) > history[i-1].get("score", 0) else "stable"
            })

        return progress

    def provide_feedback(self, evaluation: EvaluationResult) -> str:
        """生成改进建议"""
        suggestions = evaluation.suggestions or []

        feedback = f"""
📊 学习评价报告
━━━━━━━━━━━━━━━━━━
得分: {evaluation.score}/{evaluation.max_score} ({evaluation.score_percent}%)

✅ 优点:
{chr(10).join(f"  • {s}" for s in evaluation.strengths) if evaluation.strengths else "  • 暂无明显优点"}

⚠️ 需要改进:
{chr(10).join(f"  • {w}" for w in evaluation.weaknesses) if evaluation.weaknesses else "  • 暂无明显不足"}

💡 改进建议:
{chr(10).join(f"  • {s}" for s in suggestions) if suggestions else "  • 建议多做练习"}
━━━━━━━━━━━━━━━━━━
"""
        return feedback


class TeachingManager:
    """助管模块 - 教学管理"""

    def __init__(self):
        self._courses = {}
        self._students = {}

    def list_courses(self, teacher_id: str) -> List[Dict[str, Any]]:
        """课程列表"""
        return list(self._courses.values())

    def get_materials(self, course_id: str) -> List[Dict[str, Any]]:
        """获取课程资料"""
        course = self._courses.get(course_id, {})
        return course.get("materials", [])

    def manage_students(
        self,
        operation: str,
        student_id: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """学生信息管理"""
        if operation == "add":
            self._students[student_id] = data or {}
            return {"success": True, "message": f"学生 {student_id} 已添加"}
        elif operation == "update":
            if student_id in self._students:
                self._students[student_id].update(data or {})
                return {"success": True, "message": f"学生 {student_id} 已更新"}
            return {"success": False, "message": f"学生 {student_id} 不存在"}
        elif operation == "delete":
            if student_id in self._students:
                del self._students[student_id]
                return {"success": True, "message": f"学生 {student_id} 已删除"}
            return {"success": False, "message": f"学生 {student_id} 不存在"}
        elif operation == "query":
            return {"success": True, "student": self._students.get(student_id, {})}
        else:
            return {"success": False, "message": f"未知操作: {operation}"}

    def add_course(self, course_id: str, course_data: Dict) -> bool:
        """添加课程"""
        self._courses[course_id] = course_data
        return True


class MoralEducation:
    """助育模块 - 育人辅助"""

    def assess_mental_health(self, answers: List[str]) -> Dict[str, Any]:
        """心理健康评估"""
        if not answers:
            return {"status": "unknown", "score": 0, "suggestions": []}

        positive_count = sum(1 for a in answers if any(
            kw in a.lower() for kw in ["好", "开心", "积极", "满意", "希望"]
        ))

        score = (positive_count / max(len(answers), 1)) * 100

        if score >= 80:
            status = "healthy"
            suggestions = ["继续保持积极心态"]
        elif score >= 60:
            status = "good"
            suggestions = ["偶尔情绪低落是正常的，注意调节"]
        elif score >= 40:
            status = "attention"
            suggestions = ["建议多与朋友交流", "适当参加户外活动"]
        else:
            status = "concern"
            suggestions = ["建议寻求专业心理咨询", "多与家人沟通"]

        return {
            "status": status,
            "score": round(score, 1),
            "analysis": f"本次评估共{len(answers)}题，积极回答{positive_count}题",
            "suggestions": suggestions
        }

    def recommend_activities(self, student_profile: Dict) -> List[str]:
        """推荐素质培养活动"""
        interests = student_profile.get("interests", [])
        level = student_profile.get("level", "beginner")

        activities = {
            "academic": ["学术讲座", "科研项目", "学科竞赛"],
            "sports": ["体育锻炼", "运动会", "健身活动"],
            "art": ["艺术工作坊", "音乐会", "绘画展览"],
            "social": ["志愿服务", "社团活动", "社会实践"]
        }

        recommended = []
        for interest in interests:
            if interest in activities:
                recommended.extend(activities[interest][:2])

        if not recommended:
            recommended = ["志愿服务", "社团活动", "体育锻炼"]

        return list(set(recommended))[:5]

    def generate_growth_report(self, student_id: str, records: List[Dict]) -> Dict[str, Any]:
        """生成成长报告"""
        if not records:
            return {"message": "暂无成长记录"}

        total_score = sum(r.get("score", 0) for r in records)
        avg_score = total_score / max(len(records), 1)

        return {
            "student_id": student_id,
            "period": records[0].get("date", "") + " 至 " + records[-1].get("date", ""),
            "total_activities": len(records),
            "average_performance": round(avg_score, 1),
            "highlights": [
                "在团队合作方面表现突出",
                "创新思维能力强"
            ],
            "development_areas": [
                "时间管理能力可提升",
                "抗压能力需要加强"
            ],
            "overall_assessment": "该学生整体表现良好，具有较大发展潜力",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }


def get_education_tools():
    return {
        "TeachingAssistant": TeachingAssistant(),
        "LearningSupport": LearningSupport(),
        "AssessmentSystem": AssessmentSystem(),
        "TeachingManager": TeachingManager(),
        "MoralEducation": MoralEducation()
    }
