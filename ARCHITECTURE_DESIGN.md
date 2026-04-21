# 暖学帮 - 青少年心理关怀AI 技术架构设计文档

**版本**: v4.0
**架构师**: 沫汐 🌸
**日期**: 2026-04-12
**参赛赛事**: 2026广东省大学生计算机设计大赛 · 本科赛道 · 人工智能应用

---

## 一、架构设计目标

### 1.1 赛事要求对照

| 评分维度 | 权重 | 架构设计重点 |
|---------|:----:|-------------|
| **方案创新性与实用性** | 50% | 心理关怀蓝海定位、CBT原理共情 |
| **系统功能与架构** | 30% | RAG检索、工具调用、系统稳定性 |
| **文档与演示** | 20% | 完整文档、流畅演示 |

### 1.2 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| **LLM Core** | 通义千问 (qwen-max) | 开源可用，效果好 |
| **RAG框架** | LangChain + ChromaDB | 赛事推荐 |
| **嵌入模型** | text-embedding-v3 | 高质量向量 |
| **工具框架** | LangChain Tool Calling | 赛事推荐 |
| **后端框架** | FastAPI (主) + Flask | 高性能 |
| **前端** | WeChat MiniApp | 微信生态 |
| **缓存** | Redis | 高性能 |
| **部署** | Docker + venv | 容器化+灵活 |

---

## 二、系统整体架构

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户交互层 (WeChat MiniApp)                       │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│   │ 学生端   │  │ 家长端   │  │ 教师端   │  │ 学校管理 │  │ AI伙伴(暖暖)   │ │
│   │ 心理陪伴  │  │ 知识+监测 │  │ 班级看板  │  │ 数据总览  │  │ 情感可视化     │ │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘ │
└────────┼───────────┼────────────┼────────────┼─────────────────┼───────────┘
         │           │            │            │                 │
         └───────────┴────────────┴────────────┴─────────────────┘
                                    │
                           ┌────────▼────────┐
                           │   API Gateway   │
                           │   (FastAPI)     │
                           │  • 认证鉴权     │
                           │  • 限流熔断     │
                           └────────┬────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────────────┐
│                          LangChain Agent 核心层                             │
│                          ┌────────▼────────┐                              │
│                          │  Intent Router  │                              │
│                          │  • 意图分类     │                              │
│                          │  • 情绪识别     │                              │
│                          └────────┬────────┘                              │
│                                    │                                        │
│  ┌────────────────────────────────┼─────────────────────────────────────┐│
│  │                    LangChain LCEL 编排                                  ││
│  │                                                                         ││
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               ││
│  │   │ 心理支持链   │  │  工具调用链  │  │ 知识检索链   │               ││
│  │   │ (共情生成)   │  │ (预警/报告)  │  │ (RAG搜索)    │               ││
│  │   └──────────────┘  └──────────────┘  └──────────────┘               ││
│  │                                                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                        │
│  ┌─────────────────────────────────┴────────────────────────────────────────┐│
│  │                          RAG + 知识库层                                    ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ││
│  │  │ 心理知识库   │  │ 案例对话库   │  │ 术语词典    │  │ 用户档案库 │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  ││
│  └──────────────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                           ┌────────▼────────┐
                           │   通义千问API    │
                           │  (开源模型核心)  │
                           └─────────────────┘
```

---

## 三、LangChain集成实现

### 3.1 心理支持Agent（LCEL编排）

```python
# ============================================================
# 暖学帮心理支持 Agent - LangChain LCEL 编排
# 赛事要求：必须使用LangChain等应用开发框架
# ============================================================

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import tool
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# 1. 心理支持Prompt
PSYCHOLOGY_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content="""你是暖学帮的心理支持AI助手"暖暖"。
    
    核心原则：
    1. 共情优先：首先理解和认可用户的感受
    2. 循证方法：运用认知行为疗法(CBT)等心理学原理
    3. 安全边界：识别危机信号，及时引导专业帮助
    4. 积极导向：帮助用户发现自身优势和应对能力
    
    对话风格：
    - 温暖如沐春风，语言亲切自然
    - 避免说教，用启发式提问引导思考
    - 适当使用emoji传递情感
    - 根据情绪状态调整回应强度
    """),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessage(content="{user_input}"),
])

# 2. 向量存储初始化（心理知识库）
embeddings = HuggingFaceEmbeddings(model_name="text-embedding-v3")
psychology_vectorstore = Chroma(
    collection_name="psychology_knowledge",
    embedding_function=embeddings,
    persist_directory="./data/chroma/psychology"
)

# 3. RAG检索器
retriever = psychology_vectorstore.as_retriever(
    search_kwargs={"k": 5}
)

# 4. 完整RAG链
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | ChatPromptTemplate.from_template("""基于以下心理知识，回答用户问题。
    
    心理知识：
    {context}
    
    用户问题：{question}
    
    请用温暖、共情的语气回答：""")
    | llm  # 通义千问
    | StrOutputParser()
)

# 5. 带记忆的对话Agent
from agent.memory import MemoryManager

class PsychologyAgent:
    def __init__(self):
        self.memory = MemoryManager()
        self.llm = llm
        self.prompt = PSYCHOLOGY_PROMPT
    
    def chat(self, user_input: str, session_id: str) -> str:
        # 获取对话历史
        chat_history = self.memory.get_history(session_id)
        
        # RAG检索
        context = retriever.invoke(user_input)
        
        # 生成响应
        response = (
            self.prompt.format_messages(
                user_input=user_input,
                chat_history=chat_history,
                context=context
            )
            | self.llm
            | StrOutputParser()
        )
        
        # 保存记忆
        self.memory.add_message(session_id, "user", user_input)
        self.memory.add_message(session_id, "assistant", response)
        
        return response
```

### 3.2 工具调用实现

```python
# ============================================================
# 心理支持工具集 - LangChain Tools
# 赛事要求：必须实现工具调用
# ============================================================

from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field
from typing import Optional

# --- 工具1: 心理知识检索 ---
class PsychologySearchInput(BaseModel):
    query: str = Field(description="心理相关查询")
    user_type: str = Field(default="student", description="用户类型")

@tool("search_psychology_knowledge", args_schema=PsychologySearchInput)
def search_psychology_knowledge(query: str, user_type: str = "student") -> str:
    """检索心理知识库，用于回答心理健康相关问题。"""
    results = psychology_vectorstore.similarity_search(query, k=5)
    return "\n\n".join([f"【{doc.metadata['title']}】\n{doc.page_content}" for doc in results])

# --- 工具2: 情绪识别 ---
class EmotionDetectInput(BaseModel):
    text: str = Field(description="用户输入文本")

@tool("detect_emotion", args_schema=EmotionDetectInput)
def detect_emotion(text: str) -> dict:
    """识别用户情绪状态"""
    emotion_labels = {
        "happy": {"label": "开心", "score": 0.9, "icon": "😊"},
        "sad": {"label": "难过", "score": 0.85, "icon": "😢"},
        "anxious": {"label": "焦虑", "score": 0.8, "icon": "😰"},
        "neutral": {"label": "平静", "score": 0.6, "icon": "😌"},
    }
    detected = emotion_classifier.predict(text)
    return emotion_labels.get(detected, emotion_labels["neutral"])

# --- 工具3: 危机检测 ---
class CrisisCheckInput(BaseModel):
    text: str = Field(description="用户输入文本")

@tool("check_crisis", args_schema=CrisisCheckInput)
def check_crisis(text: str) -> dict:
    """检测危机信号（自杀倾向、自伤等）"""
    crisis_keywords = {
        "self_harm": ["自残", "割腕", "想死", "不想活"],
        "suicide": ["自杀", "轻生", "结束生命"],
    }
    
    detected_signals = []
    for category, keywords in crisis_keywords.items():
        for keyword in keywords:
            if keyword in text:
                detected_signals.append({"category": category, "keyword": keyword})
    
    return {
        "risk_level": "critical" if detected_signals else "low",
        "signals": detected_signals,
        "action": "immediate_intervention" if detected_signals else "normal_conversation"
    }

# --- 工具4: 心理报告生成 ---
class ReportGenerateInput(BaseModel):
    student_id: str = Field(description="学生ID")
    period: str = Field(default="weekly", description="报告周期")

@tool("generate_psychology_report", args_schema=ReportGenerateInput)
def generate_psychology_report(student_id: str, period: str = "weekly") -> str:
    """生成学生心理状态报告"""
    emotion_history = emotion_tracker.get_history(student_id, period=period)
    return llm.invoke(f"基于以下情绪数据生成报告：{emotion_history}")

# --- 工具5: 预警通知 ---
class NotifyGuardianInput(BaseModel):
    student_id: str = Field(description="学生ID")
    alert_type: str = Field(description="预警类型")
    urgency: str = Field(default="normal", description="紧急程度")

@tool("notify_guardian", args_schema=NotifyGuardianInput)
def notify_guardian(student_id: str, alert_type: str, urgency: str = "normal") -> dict:
    """向家长/教师发送预警通知"""
    guardian_info = user_db.get_guardian(student_id)
    notification_service.send(guardian_info["id"], alert_type, urgency)
    return {"status": "sent"}

# 工具注册
psychology_tools = [
    search_psychology_knowledge,
    detect_emotion,
    check_crisis,
    generate_psychology_report,
    notify_guardian,
]

# Agent绑定工具
agent_with_tools = (
    PSYCHOLOGY_PROMPT
    | llm.bind_tools(psychology_tools)
    | StrOutputParser()
)
```

---

## 四、RAG检索架构

### 4.1 心理知识库分类

```
┌─────────────────────────────────────────────────────────────────┐
│                      心理知识库 (Psychology KB)                    │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │ 学生心理知识     │  │ 家长心理学       │  │ 教师心理学   │  │
│  │ • 自我认知      │  │ • 亲子沟通      │  │ • 学生发展   │  │
│  │ • 情绪管理      │  │ • 青春期理解    │  │ • 识别问题   │  │
│  │ • 人际关系      │  │ • 支持技巧      │  │ • 课堂环境   │  │
│  │ • 学习压力      │  │ • 预警信号      │  │ • 沟通技巧   │  │
│  │ • 考试焦虑      │  │ • 心理健康     │  │ • 特殊关怀   │  │
│  └────────┬────────┘  └────────┬────────┘  └───────┬───────┘  │
│           └─────────────────────┴─────────────────────┘          │
│                              │                                    │
│                     ┌────────▼────────┐                          │
│                     │   ChromaDB      │                          │
│                     │   向量存储       │                          │
│                     └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 混合搜索实现

```python
# ============================================================
# 混合搜索 - 向量 + BM25 + 情绪权重
# 赛事要求：RAG检索准确率优化
# ============================================================

from langchain.retrievers import EnsembleRetriever
from langchain.retrievers.bm25 import BM25Retriever

class EmotionWeightedHybridRetriever:
    """情绪感知的混合检索器"""
    
    def __init__(self, vector_weight=0.6, bm25_weight=0.25, emotion_weight=0.15):
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.emotion_weight = emotion_weight
        self.vector_retriever = vectorstore.as_retriever()
        self.bm25_retriever = BM25Retriever.from_texts(texts)
    
    def invoke(self, query, emotion_state=None):
        # 1. 并行检索
        vector_results = self.vector_retriever.get_relevant_documents(query)
        bm25_results = self.bm25_retriever.get_relevant_documents(query)
        
        # 2. 情绪权重提升
        if emotion_state:
            for doc in vector_results:
                if emotion_state in doc.metadata.get("emotions", []):
                    doc.score *= (1 + self.emotion_weight)
        
        # 3. RRF融合
        fused = self._reciprocal_rank_fusion([vector_results, bm25_results])
        return fused[:5]
    
    def _reciprocal_rank_fusion(self, result_lists, k=60):
        scores = {}
        for docs in result_lists:
            for rank, doc in enumerate(docs):
                key = doc.page_content[:100]
                scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        # 返回融合后的排序结果
        ...
```

---

## 五、心理支持对话流程

### 5.1 完整对话流程

```
用户输入 → 危机检测 → 情绪识别 → RAG检索 → 响应生成 → 输出

示例：
用户: "最近感觉好累，学习压力大..."
    ↓
危机检测: risk_level="low" → 正常对话
    ↓
情绪识别: emotion="anxious", intensity=0.75
    ↓
RAG检索: 检索"焦虑应对"相关心理知识
    ↓
响应生成:
  "听到你说最近学习压力很大，我能理解那种喘不过气的感觉... 🌸
   
   你愿意和我聊聊，是什么让你特别感到累吗？"
```

### 5.2 危机干预流程

```
检测到敏感内容 → 危机评估 → ┬→ 低风险 → 正常对话
                            ├→ 中风险 → 增加关注
                            └→ 高风险 → 立即干预 ⭐
                                      1. 稳定情绪: "我在这里陪你"
                                      2. 表达关心: "你很重要"
                                      3. 专业转介: 心理援助热线
```

---

## 六、部署架构

### 6.1 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: ./agent
    ports:
      - "8000:8000"
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
    volumes:
      - ./agent/data:/app/data
    depends_on:
      - redis
      - chroma

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  chroma:
    image: ghcr.io/chroma-core/chroma:0.4.22
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
```

### 6.2 本地venv部署

```bash
# start_venv.bat
cd agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

---

## 七、评分对照

| 评分维度 | 权重 | 暖学帮实现 | 得分预估 |
|---------|:----:|-----------|:--------:|
| **方案创新性** | 25% | 心理蓝海定位+CBT共情 | 22-24 |
| **实用性** | 25% | 学生-家长-教师闭环 | 20-23 |
| **系统架构** | 15% | LangChain+RAG+工具调用 | 13-14 |
| **RAG功能** | 10% | 混合搜索+情绪权重 | 8-9 |
| **工具调用** | 10% | 5+专业工具 | 8-9 |
| **系统稳定性** | 5% | Docker部署+监控 | 4-5 |
| **文档完整性** | 10% | README+架构+评估+部署 | 8-9 |
| **总分** | 100% | | **83-93** |

---

## 八、架构总结

### 8.1 技术指标

| 指标 | 目标值 |
|------|--------|
| RAG检索准确率 | >88% |
| 情绪识别准确率 | >85% |
| 共情响应满意度 | >80% |
| 危机检测召回率 | >95% |
| 平均响应时间 | <2s |

### 8.2 核心创新点

| 创新点 | 说明 |
|--------|------|
| **心理核心架构** | 以心理健康为核心的系统设计 |
| **情绪感知RAG** | 根据情绪状态动态调整检索权重 |
| **共情对话引擎** | 基于CBT原理的心理支持响应 |
| **三级预警体系** | 低/中/危急分级干预 |

---

**文档结束**

*架构设计：沫汐 🌸*
*版本：v4.0*
*日期：2026-04-12*
