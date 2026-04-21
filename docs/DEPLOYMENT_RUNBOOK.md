# WarmStudy Deployment Runbook

## 1. 适用范围

本手册面向当前仓库结构编写，目标是让接手者能完成以下三件事：

1. 在本地把后端服务跑起来
2. 在云服务器上完成可演示部署
3. 明确当前代码与生产级部署之间还差哪些工作

## 2. 当前项目结构

```text
WarmStudy-MOXI-fresh/
|- WarnStudty/              # 微信小程序前端
|- agent/                   # Python 后端
|  |- app.py                # RAG / Agent 主服务，默认 5177
|  |- api_gateway.py        # API 网关，默认 8000
|  |- docker-compose.yml    # 当前更接近可用的容器配置
|  |- requirements.txt
|  |- pyproject.toml
|- docs/
```

## 3. 运行架构说明

当前代码是“双服务”结构：

- `5177`：Agent / RAG 服务
  - 负责知识库、心理对话、部分 v5 API
- `8000`：API Gateway
  - 负责给前端提供统一接口
  - 会把学生/家长对话代理到 `5177`

前端默认访问：

- `http://localhost:8000`

后端内部依赖：

- `RAG_AGENT_URL=http://localhost:5177`

## 4. 环境要求

### 开发环境

- Windows 10/11 或 Linux
- Python `3.10+`
- 建议内存 `8GB+`
- 外网可访问模型服务商 API

### 演示/试点服务器建议

- 2 vCPU / 4 GB 内存：仅内部演示，低并发
- 4 vCPU / 8 GB 内存：校内试点起步配置
- 80 GB SSD：存放日志、知识库、向量索引与备份

## 5. 必要环境变量

在 `agent/.env` 中至少配置以下变量：

```env
# 模型选择
CHAT_MODEL=qwen

# 通义千问
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus

# 若切换 MiniMax
MINIMAX_API_KEY=your_minimax_api_key

# 网关到 Agent 的内部地址
RAG_AGENT_URL=http://localhost:5177

# 日志与运行环境
FLASK_ENV=production
LOG_LEVEL=INFO
```

说明：

- 当前代码里的 `CHAT_MODEL` 主要用于在 `qwen` 和 `minimax` 之间切换。
- 如果使用 Qwen，建议先用 `qwen-plus` 作为默认模型。
- 如果使用 MiniMax，建议先在受控测试环境验证回复风格与安全边界。

## 6. 本地最小可运行方案

### 6.1 安装依赖

在仓库根目录执行：

```powershell
cd C:\Users\34206\OneDrive\Desktop\项目\WarmStudy\WarmStudy-MOXI-fresh\agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果需要跑测试，再额外安装：

```powershell
.\.venv\Scripts\python.exe -m pip install pytest pytest-cov pytest-asyncio
```

### 6.2 启动后端

方式一：分两个终端启动

```powershell
# 终端 A
cd C:\Users\34206\OneDrive\Desktop\项目\WarmStudy\WarmStudy-MOXI-fresh\agent
.\.venv\Scripts\python.exe app.py
```

```powershell
# 终端 B
cd C:\Users\34206\OneDrive\Desktop\项目\WarmStudy\WarmStudy-MOXI-fresh\agent
.\.venv\Scripts\python.exe api_gateway.py
```

方式二：用 `app.py` 内部拉起双服务

```powershell
cd C:\Users\34206\OneDrive\Desktop\项目\WarmStudy\WarmStudy-MOXI-fresh\agent
.\.venv\Scripts\python.exe app.py
```

说明：

- 当前仓库里 `app.py` 包含启动网关线程的逻辑，因此单独执行 `app.py` 时，通常会同时提供 `5177` 与 `8000`。
- 但为了排错更清晰，调试阶段仍建议双终端分别启动。

### 6.3 启动前端

当前前端是微信小程序工程，不是标准 Web SPA。

建议流程：

1. 打开微信开发者工具
2. 导入目录：`WarnStudty`
3. 在 `app.ts` 或开发者工具配置中确认 API 地址为 `http://localhost:8000`
4. 使用真机/模拟器验证登录、聊天、家长端页面

## 7. 服务器部署建议

## 7.1 单机演示部署

适合比赛现场、校内答辩、老师验收。

推荐方式：

1. 一台 Linux 云服务器
2. Python venv 部署
3. `systemd` 守护进程
4. `Nginx` 做反向代理

推荐暴露方式：

- `https://your-domain/api-gateway/*` -> `localhost:8000`
- `https://your-domain/agent/*` -> `localhost:5177`

不建议直接把两个 Flask 端口裸露到公网。

## 7.2 建议的生产拓扑

```text
Client / Mini Program
        |
     Nginx / WAF
        |
   API Gateway (8000)
        |
   Agent Service (5177)
        |
  Vector Store / Redis / DB / Object Storage
```

推荐拆分方向：

- 网关层：鉴权、限流、审计、日志
- Agent 层：模型调用、RAG、工作流编排
- 存储层：
  - MySQL / PostgreSQL：用户、会话元数据、运营数据
  - Redis：缓存、限流、会话态
  - 对象存储：附件、报告、导出文件
  - Chroma / 其他向量库：知识库检索

## 8. Docker 部署说明

当前仓库里有两份 Compose 配置：

- 根目录 `docker-compose.yml`
- `agent/docker-compose.yml`

部署时优先使用 `agent/docker-compose.yml`，原因是：

- 它与当前 `agent` 目录结构更接近
- 根目录版本仍包含历史 `backend/` 路径残留

示例：

```powershell
cd C:\Users\34206\OneDrive\Desktop\项目\WarmStudy\WarmStudy-MOXI-fresh\agent
docker compose up -d --build
```

如果需要把 `8000` 网关也容器化，建议后续单独补一份新的生产版 Compose，而不是继续沿用根目录旧配置。

## 9. Nginx 反向代理示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /agent/ {
        proxy_pass http://127.0.0.1:5177/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 10. 上线前必须补齐的工程项

当前代码能演示，但距离稳定上线还有这些关键缺口：

1. 把 `mock_database` 替换成真实持久化存储
2. 清理根目录历史 `docker-compose.yml`
3. 统一接口归属，避免 `app.py` 与 `api_gateway.py` 出现重复路由
4. 统一前端 API 调用方式，去掉页面级硬编码地址
5. 增加日志、监控、告警、审计与异常追踪
6. 明确未成年人数据、敏感内容、危机干预的处理流程

## 11. 部署排障清单

### 11.1 前端访问不到后端

优先检查：

1. `app.ts` 里的 `apiBase` 是否正确
2. `8000` 端口是否真的启动
3. 服务器安全组和防火墙是否放行
4. 小程序域名白名单是否已配置

### 11.2 聊天接口失败

优先检查：

1. `RAG_AGENT_URL` 是否指向 `5177`
2. 模型 API Key 是否配置成功
3. 目标模型名是否存在且可用
4. 服务器是否能访问外部模型平台

### 11.3 本地能跑、服务器不能跑

高频原因：

- `.env` 没上传
- 依赖没有完整安装
- 端口占用
- Windows 路径硬编码残留
- 根目录旧配置误导了启动方式

## 12. 推荐交付路径

如果目标是快速交付，建议按下面顺序推进：

1. 先完成单机演示部署
2. 再完成校内试点版部署
3. 再补监控、数据库、审计、备份
4. 最后做多租户与商业化能力
