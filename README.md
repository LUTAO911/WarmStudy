# WarmStudy（暖学帮）

<div align="center">

![Competition](https://img.shields.io/badge/2026%E5%B9%BF%E4%B8%9C%E7%9C%81%E5%A4%A7%E5%AD%A6%E7%94%9F%E8%AE%A1%E7%AE%97%E6%9C%BA%E8%AE%BE%E8%AE%A1%E5%A4%A7%E8%B5%9B-%E6%95%99%E8%82%B2%E6%96%B9%E5%90%91-blue)
![Scenario](https://img.shields.io/badge/Scene-%E5%8A%A9%E8%82%B2%20%2F%20%E9%9D%92%E5%B0%91%E5%B9%B4%E5%BF%83%E7%90%86%E5%85%B3%E6%80%80-0ea5e9)
![Model](https://img.shields.io/badge/Model-Qwen%20%2F%20DashScope-2563eb)
![Architecture](https://img.shields.io/badge/Architecture-Agent%20%2B%20RAG%20%2B%20Gateway-0f766e)
![Admin](https://img.shields.io/badge/Admin-Unified%20Console-14b8a6)
![CI](https://img.shields.io/badge/CI-tests%20%26%20build-success)

**面向青少年心理关怀与家校协同支持场景的教育智能体原型系统**

</div>

WarmStudy（暖学帮）是一套围绕“学生表达困难、家长理解不足、学校支持有限”这一真实教育问题设计的智能体原型系统。它不是普通聊天机器人，也不是单纯的信息展示应用，而是一套把学生端、家长端、心理知识库、风险提醒、管理员后台、模型配置与部署能力串成闭环的场景化系统。

> 让智能体不只是“回答问题”，而是真正理解角色、年龄、状态与场景，再给出更合适的心理支持与沟通建议。

说明：

- 本项目的前端应用形态建议统一表述为“基于微信小程序技术实现的 App 应用前端”。
- `WarnStudty/` 是该 App 的前端工程载体，不建议简单理解为普通小程序演示项目。

## 文档索引

如果你是第一次看这个仓库，建议按下面顺序进入：

- [项目总说明](docs/COMPETITION_PROJECT_DESCRIPTION.md)
- [智能体优势与特别之处](docs/AGENT_AND_PRODUCT_ADVANTAGES.md)
- [服务器部署与更新](docs/DEPLOYMENT_RUNBOOK.md)
- [比赛演示验收清单](submission/09_比赛演示验收清单.md)
- [文档中心总索引](docs/README.md)

---

## 为什么是 WarmStudy

### 面向比赛要求的完整系统原型

本项目对应 2026 年广东省大学生计算机设计大赛教育方向“助育”场景，重点满足以下要求：

- 有清晰、真实且具体的教育问题场景
- 有大模型能力接入
- 有 RAG 知识增强能力
- 有工具调用或服务编排能力
- 有完整可演示的前后端系统与后台管理能力

### 面向真实问题，而不是泛化问答

WarmStudy 关注的不是“能不能聊天”，而是：

- 学生是否拥有低门槛、可持续的情绪表达入口
- 家长是否能获得温和、结构化、可执行的沟通建议
- 系统是否能将测评、打卡、报告、预警与后台管理连成闭环

### 面向协同支持，而不是单端工具

系统围绕三类角色构建协同能力：

- 学生端：心理测评、情绪打卡、AI 对话、心理知识支持
- 家长端：状态查看、报告解读、预警提醒、AI 沟通建议
- 管理员后台：统一查看用户、登录、模型、知识库、活动流与系统状态

---

## 核心优势

### 1. 不是固定 Prompt，而是状态驱动的智能体

智能体会结合以下信息动态调整输出策略：

- 年龄 / 年级 / 学段
- 近期打卡结果
- 心理测评状态
- 风险变化趋势
- 历史会话上下文

这意味着系统输出不是静态模板，而是更贴近当前用户状态与实际需求。

### 2. 学生端与家长端不是同一套人格

WarmStudy 明确区分两类智能体身份：

- 学生端：更强调接住情绪、适龄表达、降低说教感
- 家长端：更强调结构化建议、观察点和下一步行动

这使它区别于普通“所有用户都共用一套回答方式”的通用智能体。

### 3. RAG 不只是检索，而是和业务状态融合

系统不是简单“查知识再回答”，而是把以下信息共同纳入响应逻辑：

- 用户角色
- 年龄与学段
- 心理状态
- 会话上下文
- 知识库内容

因此它更接近“场景智能体”，而不是“知识问答机器人”。


### 4. 情绪分析与状态识别

WarmStudy 能够实时分析学生的情绪状态，通过情绪词汇的识别和分析，为智能体提供更准确的响应依据。

![情绪分析可视化](docs/assets/readme/emotion-analysis.jpg)

系统会根据情绪分析结果调整智能体的响应策略，确保在不同情绪状态下都能提供合适的支持。

### 5. 管理员后台是系统能力的一部分

管理员后台不是附加页面，而是 WarmStudy 的重要组成部分。当前统一后台可直接：

- 查看用户与登录账号数据
- 查看模型使用情况
- 查看并修改 `chat / RAG / embedding` 模型配置
- 上传、更新、删除、重置知识库
- 进行 RAG 检索与问答
- 查看近期活动流与系统总览

---

## 项目整体核心架构

下图展示了当前系统在智能体层面的核心能力组合，包括意图路由、状态驱动策略、ReAct 机制、混合搜索、线程安全记忆管理与工作流引擎。

![项目整体核心架构](docs/assets/readme/core-architecture.jpg)

这组能力共同支撑了 WarmStudy 的“个性化、可解释、可扩展”特征。

---

## 技术路线与模型链路

WarmStudy 当前采用的核心技术路线：

- 大模型：Qwen / DashScope
- 检索增强：RAG
- 向量库：ChromaDB
- 后端：Python / Flask
- 前端：基于微信小程序技术实现的 App 前端工程
- 管理端：统一网页控制台

下图展示了项目如何将 `langchain`、大模型与 `embedding` 模型组织为完整处理链路。

![技术路线与模型链路](docs/assets/readme/model-design.jpg)

### RAG 的整体流程

WarmStudy 采用完整的 RAG 流程，包括准备部分和回答部分：

#### 准备部分（提问前）

![RAG 的整体流程 - 准备部分](docs/assets/readme/rag-flow-prepare.jpg)

准备部分包括：
1. 心理健康研究报告的处理
2. 文本片段的提取与分割
3. 使用 text-embedding-v3 模型进行向量化
4. 将向量存储到向量数据库中

#### 回答部分（提问后）

![RAG 的整体流程 - 回答部分](docs/assets/readme/rag-flow-answer.jpg)

回答部分包括：
1. 学生提问的向量化处理
2. 在向量数据库中进行相似度搜索
3. 使用 Cross-Encoder 对检索结果进行重排
4. 将问题与相关片段一起输入大模型（qwen-3-max）生成回答

---

## 智能体为什么特别

### 学生端智能体：先陪伴，再支持

学生端强调“先接住情绪，再给出适龄支持”，并根据学段调整语言风格：

- 小学阶段：短句、具体、少抽象词
- 初中阶段：温和、尊重、减少说教感
- 高中阶段：强调自主感、节奏感和成熟表达

系统会根据状态切换响应重点，例如：

- 更偏安抚与陪伴
- 更偏一步式建议
- 更偏鼓励表达
- 更偏缓解学习压力刺激

### 家长端智能体：先理解，再行动

家长端采用独立人格与策略，不复用学生端逻辑，重点强调：

- 结构化表达
- 可观察的状态线索
- 可执行的下一步沟通动作
- 避免责备式、贴标签式、制造焦虑式建议

### 状态联动策略刷新

学生提交打卡、测评或状态变化后，系统会同步刷新策略状态，使智能体输出尽量贴近当前情境，而不是停留在静态设定。

---

## 双端联动设计

WarmStudy 不只是“学生有一个 AI，家长也有一个 AI”，而是让两端形成真正的联动关系。

下图展示了家长端与学生端的绑定关系设计：

![家长端与学生端联动设计](docs/assets/readme/binding-flow.jpg)

当前实现采用真实绑定链路：学生登录后自动生成固定的 9 位孩子 ID；家长首次登录且未绑定孩子时，会先看到绑定引导，输入孩子 ID 后才进入家长数据视图。系统不再默认把家长绑定到演示孩子，家长端状态、综合报告、测评报告、预警和 AI 建议都按当前绑定的孩子 ID 拉取。

这使系统能够形成：

1. 学生表达
2. 家长理解
3. 后台观察
4. 风险提醒

的连续支持闭环。

---

## 报告闭环与价值链路

WarmStudy 不把心理测评停留在“测完就结束”，而是进一步组织成完整的报告与建议推送流程。

![学生心理评测报告推送流程](docs/assets/readme/report-flow.jpg)

完整闭环包括：

1. 学生完成心理测评
2. 系统生成结构化、可理解的 AI 心理报告
3. 家长绑定孩子后同步查看综合报告、测评报告与 AI 建议
4. 达到预警阈值时，家长端同步收到风险提醒

这也是本项目区别于普通问答系统的关键之一：它强调的不只是生成，而是**可理解、可传递、可后续行动**的支持链路。

---

## 当前版本核心能力

### 学生端

- 登录
- 心理测评
- 情绪打卡
- AI 对话
- 心理知识浏览

### 家长端

- 登录
- 首次登录绑定 9 位孩子 ID
- 查看孩子状态、综合报告与测评报告
- 查看预警
- 获取 AI 沟通建议

### 管理员后台

- App 后台总览
- 用户与登录记录
- 模型使用统计
- 模型配置管理
- RAG 知识库上传、更新、删除、重置
- RAG 检索与问答
- 近期活动流与系统概览

---

## 系统架构与部署

### 对外统一入口：`8000`

- 统一网页入口
- API Gateway
- 管理员后台控制台
- 聚合 App 后台、RAG、模型使用与账号数据

### 内部服务：`5177`

- Agent / RAG API 服务
- 负责检索、问答、知识库与模型配置等能力
- 当前版本不再独立对外提供单独 Web UI

### 本地启动

```powershell
cd agent
.\start_all.ps1
```

启动后访问：

- 管理员后台：`http://localhost:8000/`

### Docker 启动

```powershell
docker compose up --build
```

默认对外暴露端口：

- `8000:8000`

### 关键环境变量

```env
CHAT_MODEL=qwen
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus
RAG_DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v3
DASHSCOPE_EMBEDDING_FALLBACK_MODEL=text-embedding-v2
AGENT_API_KEY=your_agent_api_key
RAG_AGENT_URL=http://localhost:5177
FLASK_ENV=production
LOG_LEVEL=INFO
```

---

## 文档索引

### 快速入门

- [📋 项目总说明](docs/COMPETITION_PROJECT_DESCRIPTION.md) - 场景、架构、能力、比赛映射的主说明文档
- [🌟 产品优势与智能体亮点](docs/AGENT_AND_PRODUCT_ADVANTAGES.md) - 智能体特别之处与产品优势
- [📚 文档索引中心](docs/README.md) - 完整文档导航与使用指南

### 部署与运维

- [🚀 服务器更新部署步骤](docs/SERVER_UPDATE_DEPLOYMENT.md) - 服务器更新、备份与验证流程
- [📦 部署运行手册](docs/DEPLOYMENT_RUNBOOK.md) - 当前系统部署结构与Docker配置

### 技术细节

- [🤖 更新说明](docs/AGENT_REFINEMENT_UPDATE_2026-04-22.md) - 智能体精修更新记录
- [🔧 开源组件与依赖说明](docs/OPEN_SOURCE_AND_COMPONENTS.md) - 开源框架、组件与依赖
- [🎯 模型选择说明](docs/MODEL_SELECTION.md) - 当前模型路径选择说明
- [📊 模型来源与部署方式](docs/MODEL_SOURCE_AND_DEPLOYMENT_NOTE.md) - 模型来源与部署说明

### 比赛材料

- [📝 项目概要表](docs/PROJECT_OVERVIEW_FORM.md) - 作品概要表参考内容
- [✅ 提交材料检查清单](docs/COMPETITION_SUBMISSION_CHECKLIST.md) - 比赛提交材料检查清单

---

## 仓库结构

```text
WarmStudy-main/
├─ WarnStudty/          # 基于微信小程序技术实现的 App 前端工程
├─ agent/               # API Gateway、Agent、RAG、管理员后台
├─ docs/                # 项目说明与部署文档
├─ docs/assets/readme/  # README 展示图片资源
├─ submission/          # 比赛提交材料
├─ docker-compose.yml   # 根目录 Docker 编排
└─ 2026年广东省大学生计算机设计大赛-本科赛道赛题说明.pdf
```

---

## 参赛团队信息

### 队伍名称

| 项目 | 内容 |
| --- | --- |
| 队伍名称 | 灵感加载中 |

### 队员与导师

| 角色 | 姓名 | 分工 |
| --- | --- | --- |
| 队长 | 卢涛 | 项目统筹、方案设计、答辩组织 |
| 队员 | 涂凯莉 | 前端实现与交互联调 |
| 队员 | 吴楚阳 | 后端接口与数据流转 |
| 队员 | 黎悦濠 | 智能体策略与 RAG 能力实现 |
| 队员 | 陈希曼 | 文档整理、材料整合与测试验证 |
| 指导教师 | 翁诗阳 | 项目指导与技术把关 |

---

## 项目说明

当前仓库以 App 前端工程、Agent / RAG 服务与统一管理员后台为核心，适合用于比赛展示、原型验证与后续功能扩展。  
如果还要继续增强 GitHub 首页展示效果，下一步还可以补：

- 管理员后台截图
- 学生端 / 家长端界面截图
- Release 下载入口
- Demo 视频入口
