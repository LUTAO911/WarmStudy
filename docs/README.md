# WarmStudy 文档中心

这套文档用于统一项目说明、部署口径、比赛材料和后续维护说明。  
建议按“你要解决什么问题”来阅读，而不是按文件名逐个翻。

---

## 先看哪一份

### 如果你要快速理解整个项目

- [COMPETITION_PROJECT_DESCRIPTION.md](COMPETITION_PROJECT_DESCRIPTION.md)
  - 项目总说明
  - 场景、架构、能力、比赛映射的主说明文档

- [AGENT_AND_PRODUCT_ADVANTAGES.md](AGENT_AND_PRODUCT_ADVANTAGES.md)
  - 产品优势
  - 智能体特别之处
  - 与普通智能体的区别

### 如果你要部署或更新服务器

- [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md)
  - 当前系统部署结构
  - Docker、反向代理、数据库与存储规划

- [SERVER_UPDATE_DEPLOYMENT.md](SERVER_UPDATE_DEPLOYMENT.md)
  - 服务器更新步骤
  - 更新前备份、更新后验证、后台能力验收

### 如果你要准备比赛材料

- [PROJECT_OVERVIEW_FORM.md](PROJECT_OVERVIEW_FORM.md)
  - 作品概要表参考内容

- [COMPETITION_SUBMISSION_CHECKLIST.md](COMPETITION_SUBMISSION_CHECKLIST.md)
  - 提交材料检查清单

### 如果你要看模型和开源说明

- [MODEL_SELECTION.md](MODEL_SELECTION.md)
  - 当前模型路径选择说明

- [MODEL_SOURCE_AND_DEPLOYMENT_NOTE.md](MODEL_SOURCE_AND_DEPLOYMENT_NOTE.md)
  - 模型来源与部署方式说明

- [OPEN_SOURCE_AND_COMPONENTS.md](OPEN_SOURCE_AND_COMPONENTS.md)
  - 开源框架、组件与依赖说明

### 如果你要看最近做了什么优化

- [AGENT_REFINEMENT_UPDATE_2026-04-22.md](AGENT_REFINEMENT_UPDATE_2026-04-22.md)
  - 智能体精修更新说明

---

## 当前推荐保留的文档结构

```text
docs/
├─ README.md
├─ COMPETITION_PROJECT_DESCRIPTION.md
├─ AGENT_AND_PRODUCT_ADVANTAGES.md
├─ AGENT_REFINEMENT_UPDATE_2026-04-22.md
├─ DEPLOYMENT_RUNBOOK.md
├─ SERVER_UPDATE_DEPLOYMENT.md
├─ PROJECT_OVERVIEW_FORM.md
├─ COMPETITION_SUBMISSION_CHECKLIST.md
├─ MODEL_SELECTION.md
├─ MODEL_SOURCE_AND_DEPLOYMENT_NOTE.md
├─ OPEN_SOURCE_AND_COMPONENTS.md
└─ assets/
```

---

## 已做的文档收敛

当前已经对 `docs/` 做了收敛处理：

- 删除了不属于当前责任范围的 PPT / Demo 提纲文档
- 删除了当前阶段非核心的商业化规划文档
- 保留比赛、部署、模型、开源、优势、更新说明等真正需要用到的内容

这样做的目的，是让文档中心更适合：

- 比赛提交
- 服务器部署
- GitHub 展示
- 团队内部协作

---

## 当前工程口径

- 前端工程目录：`WarnStudty`
- 前端形态：基于微信小程序技术实现的 App 应用前端
- 对外唯一后台入口：`8000`
- 内部 Agent / RAG API：`5177`
- 当前对外 Web 只保留统一管理员后台
