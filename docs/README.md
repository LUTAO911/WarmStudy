# WarmStudy 文档索引

这套文档用于统一项目说明、部署口径和比赛提交材料。

## 优先阅读

1. [COMPETITION_PROJECT_DESCRIPTION.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/COMPETITION_PROJECT_DESCRIPTION.md)
   项目总说明，适合作为项目报告和答辩口径母版。
2. [DEPLOYMENT_RUNBOOK.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/DEPLOYMENT_RUNBOOK.md)
   服务器部署、Docker、反向代理、唯一管理员后台的运行说明。
3. [PROJECT_OVERVIEW_FORM.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/PROJECT_OVERVIEW_FORM.md)
   作品信息概要表参考文本。
4. [PPT_AND_DEMO_OUTLINE.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/PPT_AND_DEMO_OUTLINE.md)
   答辩 PPT 和演示视频提纲。
5. [COMPETITION_SUBMISSION_CHECKLIST.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/COMPETITION_SUBMISSION_CHECKLIST.md)
   提交材料核对清单。

## 配套文档

- [MODEL_SELECTION.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/MODEL_SELECTION.md)
- [MODEL_SOURCE_AND_DEPLOYMENT_NOTE.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/MODEL_SOURCE_AND_DEPLOYMENT_NOTE.md)
- [OPEN_SOURCE_AND_COMPONENTS.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/OPEN_SOURCE_AND_COMPONENTS.md)
- [COMMERCIALIZATION_PLAN.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/COMMERCIALIZATION_PLAN.md)

## 当前工程状态

- 前端目录：`WarnStudty`
- 后端目录：`agent`
- 对外唯一后台入口：`8000`
- 内部 RAG / Agent API：`5177`
- 当前对外 Web 只保留一个管理员后台，不再单独暴露 `5177` 页面

## 当前部署原则

- 浏览器与管理员只访问 `8000`
- `5177` 只作为内网或容器内服务
- Docker 生产部署默认只映射 `8000`

## 最近更新

- [AGENT_REFINEMENT_UPDATE_2026-04-22.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/AGENT_REFINEMENT_UPDATE_2026-04-22.md)
- [AGENT_AND_PRODUCT_ADVANTAGES.md](/C:/Users/34206/OneDrive/Desktop/WarmStudy-main/docs/AGENT_AND_PRODUCT_ADVANTAGES.md)
