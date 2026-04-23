# WarmStudy Backend

`agent/` 目录包含 WarmStudy 的后端服务、RAG 能力、管理页面和部署文件。

## 服务说明

- `app.py`
  启动 Agent / RAG 服务，并提供 `5177` 管理页面与相关接口。
- `api_gateway.py`
  提供 `8000` 网关接口，服务微信小程序与演示页面。
- `templates/index.html`
  RAG 知识库管理与 Agent 控制台。

## 本地启动

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

或使用：

```powershell
.\start_all.ps1
```

## 环境变量

常用环境变量如下：

- `CHAT_MODEL`
- `DASHSCOPE_API_KEY`
- `DASHSCOPE_MODEL`
- `AGENT_API_KEY`
- `FLASK_ENV`
- `LOG_LEVEL`
- `RAG_AGENT_URL`

生产环境请显式配置 `AGENT_API_KEY`，不要依赖开发默认值。

## 测试

```powershell
.\.venv\Scripts\python -m pytest tests -q
```

当前已验证结果：

- `309 passed`
- `16 skipped`

## 默认端口

- `5177`：Agent / RAG 服务
- `8000`：API 网关
