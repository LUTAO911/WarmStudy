# 服务器更新部署步骤

## 说明

WarmStudy 当前对外只有一个管理员后台入口，默认通过 `8000` 提供统一网页后台。

本项目的前端应用形态应表述为：

- 基于微信小程序技术实现的 App 应用前端
- 不是单纯意义上的“普通微信小程序演示页”

如果服务器已经部署过旧版本，更新时建议按下面步骤执行。

## 1. 更新前备份

建议至少备份以下内容：

- `agent/.env`
- `agent/data/`
- `agent/uploads/`
- `agent/logs/`

如果服务器上已经接入数据库，也建议先做数据库备份。

## 2. 拉取最新代码

```bash
cd /path/to/WarmStudy
git fetch --all
git checkout main
git pull
```

如果你服务器固定跑的是 `moxi`，则改为：

```bash
git checkout moxi
git pull
```

## 3. 重新构建并启动容器

在项目根目录执行：

```bash
docker compose up -d --build
```

如果只想重建核心服务，也可以先执行：

```bash
docker compose down
docker compose up -d --build
```

## 4. 更新后检查

至少检查以下内容：

### 4.1 管理员后台

- 打开 `https://你的域名/`
- 确认管理员后台首页能正常加载
- 确认能看到：
  - 用户列表
  - 登录记录
  - 模型使用统计
  - 模型配置面板
  - RAG 管理面板

### 4.2 模型配置

在管理员后台中确认可以直接查看和修改：

- 聊天模型
- RAG 生成模型
- Embedding 模型
- Embedding 备选模型

并验证修改后刷新页面仍能看到最新配置。

### 4.3 智能体能力

确认以下链路可用：

- 学生聊天
- 家长聊天
- 学生资料同步
- 测评提交
- 打卡提交
- RAG 问答

### 4.4 API 检查

可以手动访问或调用：

- `/api/admin/overview`
- `/api/admin/users`
- `/api/admin/logins`
- `/api/admin/model-usage`
- `/api/admin/model-config`

## 5. 如果管理员后台改了模型配置

当前实现会把模型配置更新到运行时，并写回服务端 `.env`。

因此建议：

- 修改模型配置后立即刷新后台确认
- 如有需要，再重启一次容器确保新配置完全一致

```bash
docker compose restart
```

## 6. 更新失败时的回退建议

如果更新后出现问题，建议按这个顺序回退：

1. 回退代码到上一个稳定 commit
2. 恢复备份的 `.env`
3. 恢复 `agent/data/`、`agent/uploads/`
4. 重新执行 `docker compose up -d --build`

## 7. 当前管理员后台能直接做什么

当前后台已经可以直接：

- 看登录账号和用户数据
- 看近期活动记录
- 看模型使用统计
- 看并修改 chat / RAG / embedding 模型
- 上传、更新、删除、重置知识库
- 做 RAG 检索和问答

这意味着服务器更新完成后，不需要再额外打开别的网页后台，统一在这个管理员后台里操作即可。

## 8. 新增的工程化改进

当前版本还新增了几项针对服务器部署问题的工程化改进：

- 网关集中配置文件：
  - `agent/config/gateway.json`
- 路由治理：
  - 保留 `/api/chat` 兼容别名
  - 保留 `/api/agent/chat` 兼容别名
  - 新增 `/api/admin/routes` 可查看路由清单
- 健康检查增强：
  - `/api/health` 返回更完整的网关状态、RAG 状态和运行配置摘要
  - 响应头带 `X-Request-ID` 与响应时间信息，便于日志追踪

如果服务器侧需要排查调用问题，建议优先查看：

- `/api/health`
- `/api/admin/routes`
- `/api/admin/overview`
