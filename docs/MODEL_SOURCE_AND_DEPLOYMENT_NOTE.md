# Model Source And Deployment Note

## 1. Purpose

This note is prepared for competition submission and on-site deployment explanation. It focuses on:

1. which large model is used in the current project
2. whether it is locally deployed or called through API
3. how to configure model access
4. what needs to be prepared for demo and defense

## 2. Current Model Usage In This Project

According to the current codebase, the project currently keeps one model access path:

1. Qwen / Tongyi Qianwen

The implementation is centered on API access rather than bundling local model weights inside the repository.

## 3. Model Source Description

### 3.1 Qwen / Tongyi Qianwen

- Model type: mainstream large language model
- Access method in this project: API invocation through DashScope / Model Studio
- Main use in project: dialogue generation, psychological support reply generation, and RAG-based answer generation
- Local weights included in repository: No
- Required configuration:
  - `DASHSCOPE_API_KEY`
  - `DASHSCOPE_MODEL`

Recommended default setting:

```env
CHAT_MODEL=qwen
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus
```

## 4. Whether Local Model Weights Are Provided

The current competition version of this repository does not package local model weights.

Reason:

1. the current implementation mainly adopts API calling mode
2. local large model deployment has higher hardware requirements and would increase on-site complexity
3. API-based configuration is easier to maintain for competition demo stability

## 5. Whether API-Based Commercial Models Are Used

Yes.

The current system uses API-based model services and should explicitly state:

- the selected provider
- the access method
- environment variable configuration
- network dependency during demo
- fallback plan if the API service becomes unstable

## 6. Required Environment Variables

```env
CHAT_MODEL=qwen
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus
RAG_AGENT_URL=http://localhost:5177
FLASK_ENV=production
LOG_LEVEL=INFO
```

## 7. Recommended Wording For Project Report

Suggested text:

“本项目当前采用 API 方式调用大模型能力，统一接入通义千问（DashScope），不随源代码打包本地模型权重。系统通过环境变量配置 API Key 与模型名称，在比赛演示阶段以 API 调用方式保证部署效率与演示稳定性。”

## 8. Recommended Wording For Defense

Suggested oral explanation:

“我们当前版本优先使用 API 模式接入通义千问，一方面降低本地硬件压力，另一方面提高比赛现场部署效率。当前仓库已经统一为单模型接入路径，方便演示、答辩和后续维护。”
