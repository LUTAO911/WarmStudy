# WarmStudy Deployment Runbook

## 1. 目标

这份手册面向当前仓库的实际实现，目标是说明：

1. 如何在服务器上部署
2. 如何通过网页进入统一管理员后台
3. 如何上传知识文件
4. 数据、数据库和存储应该如何规划

## 2. 当前服务结构

当前是双进程架构，但单一网页入口：

- `8000`
  - 对外唯一入口
  - API Gateway
  - 管理员后台页面
  - 聚合 App 后台、模型使用、登录记录、RAG 管理
- `5177`
  - 内部 Agent / RAG API
  - 只给 `8000` 调用
  - 不再单独对外提供 Web UI

## 3. 服务器部署建议

推荐生产结构：

```text
Browser / App Frontend
        |
   Nginx / Caddy
        |
   warmstudy-gateway:8000
        |
   warmstudy-agent:5177
        |
 PostgreSQL / Redis / Chroma / File Storage
```

## 4. Docker 部署

在服务器项目根目录执行：

```bash
docker compose up -d --build
```

当前 Compose 已收敛为只暴露：

```text
8000:8000
```

`5177` 不再暴露到公网。

## 5. 反向代理建议

推荐把域名直接代理到 `8000`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 6. 环境变量

```env
CHAT_MODEL=qwen
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus
AGENT_API_KEY=your_admin_api_key
RAG_AGENT_URL=http://localhost:5177
FLASK_ENV=production
LOG_LEVEL=INFO
```

说明：

- 当前只保留 `Qwen / DashScope`
- `RAG_AGENT_URL` 是网关访问内部 RAG 服务的地址
- `AGENT_API_KEY` 用于内部管理员接口鉴权

## 7. 网页怎么上传文件

管理员登录后台后，直接在统一后台页面上传知识文件。

当前上传路径是：

1. 浏览器上传到 `8000`
2. 网关调用 `/api/gateway/rag/ingest/sync`
3. 再转发到内部 `5177` RAG 服务
4. 文件入库并写入向量索引

当前涉及的目录：

- `agent/uploads/`
- `agent/data/`

服务器部署时请把这两个目录做卷挂载。

## 8. 数据与数据库规划

### 8.1 当前状态

当前版本分两类数据：

- 已持久化：
  - 上传文件
  - RAG 向量库
  - 知识库索引数据
- 演示态内存数据：
  - 用户
  - 登录记录
  - 9 位孩子 ID 与家长绑定关系
  - 打卡
  - 报告
  - 预警
  - 管理员活动流
  - 模型使用统计

### 8.2 正式服务器推荐

推荐：

- PostgreSQL 或 MySQL
  - 业务数据
- Redis
  - 会话、缓存、限流、验证码
- Chroma
  - RAG 向量库
- 本地卷或对象存储
  - 上传原文件、导出报告、附件

### 8.3 建议的业务表

- `users`
- `login_events`
- `parent_child_bindings`
- `checkins`
- `psych_reports`
- `alerts`
- `admin_activity_logs`
- `model_usage_logs`
- `knowledge_files`

## 9. 统一管理员后台包含什么

当前管理员后台应作为唯一网页入口，负责：

- App 后台概览
- 用户列表
- 登录记录
- 模型调用统计
- 最近活动日志
- RAG 上传、更新、删除、重置
- RAG 检索与问答

## 10. 部署前检查

1. `8000` 页面可以正常打开
2. `5177` 仅内部可访问，不对公网暴露
3. `.env` 已配置有效 DashScope Key
4. 上传目录和数据目录已经挂载
5. 服务器磁盘空间足够
6. 已准备 HTTPS 域名或反向代理

## 11. 当前限制

当前代码已经适合比赛演示和单机后台管理，但如果要长期正式运行，下一步必须把内存态业务数据迁移到数据库。
