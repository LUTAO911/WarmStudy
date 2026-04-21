# Model Source And Deployment Note

## 1. Purpose

This note is prepared for competition submission and on-site deployment explanation. It focuses on:

1. which large models are used in the current project
2. whether they are locally deployed or called through APIs
3. how to configure model access
4. what needs to be prepared for demo and defense

## 2. Current Model Usage In This Project

According to the current codebase, the project mainly supports two model access paths:

1. Qwen / Tongyi Qianwen
2. MiniMax

The current implementation is centered on API access rather than bundling local model weights inside the repository.

## 3. Model Source Description

### 3.1 Qwen / Tongyi Qianwen

- Model type: mainstream large language model
- Access method in this project: API invocation through DashScope / Model Studio
- Main use in project: dialogue generation, response generation in psychological support scenarios, and RAG-based answer generation
- Local weights included in repository: No
- Required configuration:
  - `DASHSCOPE_API_KEY`
  - `DASHSCOPE_MODEL`

Recommended default setting in current project:

```env
CHAT_MODEL=qwen
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus
```

### 3.2 MiniMax

- Model type: third-party commercial large model service
- Access method in this project: HTTP API invocation
- Main use in project: optional dialogue generation path and alternative model provider
- Local weights included in repository: No
- Required configuration:
  - `MINIMAX_API_KEY`

## 4. Whether Local Model Weights Are Provided

The current competition version of this repository does not package local model weights.

Reason:

1. the current implementation mainly adopts API calling mode
2. local large model deployment has higher hardware requirements and would increase the complexity of on-site demo
3. for competition demo stability, API-based configuration is easier to maintain under time constraints

## 5. Whether API-Based Commercial Models Are Used

Yes.

The current system uses API-based commercial model services. This should be explicitly stated in the competition report and defense, including:

- the selected provider
- the access method
- environment variable configuration
- network dependency during demo
- fallback plan if API service is unstable

## 6. Deployment Mode Description

### 6.1 Current Recommended Demo Mode

Recommended for competition and short-cycle demo:

- backend runs on local machine or cloud server
- model access is completed through API
- frontend connects to backend gateway for interaction

Advantages:

- lower local hardware requirement
- simpler deployment process
- faster preparation for on-site presentation

### 6.2 Future Optional Local Deployment Mode

The architecture keeps space for future local model deployment or additional provider integration, but this is not the main path of the current repository.

If the team later adopts local weights, the final submission should additionally include:

- model name
- download source
- weight acquisition link
- hardware requirement
- inference framework
- acceleration or quantization method

## 7. Required Environment Variables

Current model-related environment variables:

```env
CHAT_MODEL=qwen
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus
MINIMAX_API_KEY=your_minimax_api_key
RAG_AGENT_URL=http://localhost:5177
FLASK_ENV=production
LOG_LEVEL=INFO
```

## 8. On-Site Competition Preparation Suggestion

For on-site deployment or defense, it is recommended to prepare the following in advance:

1. an available API key for the selected model provider
2. a stable network environment
3. a backup demo video in case of network instability
4. a fallback model path or pre-recorded core workflow
5. a clear written note that the current project uses API-based model access

## 9. Recommended Wording For Project Report

Suggested text:

“本项目当前采用 API 方式调用大模型能力，主要接入通义千问（DashScope）与 MiniMax 两类模型服务，不随源代码打包本地模型权重。系统通过环境变量配置 API Key 与模型名称，在比赛演示阶段以 API 调用方式保证部署效率与演示稳定性。”

## 10. Recommended Wording For Defense

Suggested oral explanation:

“我们当前版本优先使用 API 模式接入大模型，一方面降低本地硬件压力，另一方面提高比赛现场的部署效率。系统代码已经预留了后续扩展更多模型提供商或本地部署模型的空间。”
