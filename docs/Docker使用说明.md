# WarmStudy Docker 使用说明

## 1. 什么是 Docker？

Docker 是一种容器化技术，它把应用程序及其所有依赖打包到一个"集装箱"里，确保应用在任何环境中都能一致地运行。

### 为什么使用 Docker？

- **环境一致**：开发、测试、生产环境完全一致
- **一键部署**：几分钟内完成部署
- **易于维护**：更新、回滚都很方便
- **资源高效**：比虚拟机更轻量

## 2. 安装 Docker

### Windows 系统

1. 下载 Docker Desktop：[https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. 安装并启动 Docker Desktop
3. 在 PowerShell 中验证安装：
   ```powershell
   docker --version
   docker-compose --version
   ```

## 3. 快速开始

### 步骤 1：配置环境变量

1. 复制 `.env.example` 文件为 `.env`
2. 编辑 `.env` 文件，填写你的 API 密钥：
   ```
   MINIMAX_API_KEY=sk-cp-oZ13uYhDN5gGkBgIzTG1qWLX5acK2VhDzcRk_LNWBIMOkgkRs3QegFI60fUVDi1QjLOcEEueHB6Q0QzUmq_kSKEYQBr4uT91UJxDnQRc1rLRZKibf_Sw0vI
   QWEN_API_KEY=sk-48aa65856f334e33a9a5de3d603e6799
   ```

### 步骤 2：启动服务

在 PowerShell 中执行：

```powershell
cd c:\Users\34206\Desktop\WarmStudy
docker-compose up -d
```

### 步骤 3：验证服务

1. **后端 API**：访问 http://localhost:8000/docs
2. **健康检查**：访问 http://localhost:8000/health
3. **RAG 管理界面**：访问 http://localhost:8501

## 4. 常用命令

### 查看运行状态
```powershell
# 查看所有容器状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend

# 查看 RAG 管理界面日志
docker-compose logs -f rag-admin
```

### 停止服务
```powershell
docker-compose down
```

### 重启服务
```powershell
docker-compose restart
```

### 重新构建（代码更新后）
```powershell
docker-compose up -d --build
```

### 查看容器资源使用
```powershell
docker stats
```

## 5. 数据持久化

Docker 容器中的数据会保存在以下位置：

- **数据库**：`./backend/data/nuanxuebang.db`
- **知识库文件**：`./backend/knowledge/`
- **向量数据库**：`./backend/vector_db/`

这些数据在容器重启后依然存在。

## 6. 故障排查

### 问题 1：端口被占用

**症状**：`Bind for 0.0.0.0:8000 failed: port is already allocated`

**解决**：
```powershell
# 查找占用端口的进程
netstat -ano | findstr :8000

# 或者修改 docker-compose.yml 中的端口映射
# 例如：将 "8000:8000" 改为 "8080:8000"
```

### 问题 2：容器无法启动

**症状**：容器状态显示 `Exited`

**解决**：
```powershell
# 查看详细日志
docker-compose logs backend

# 检查环境变量是否正确配置
cat .env
```

### 问题 3：API 密钥无效

**症状**：AI 对话返回错误

**解决**：
1. 检查 `.env` 文件中的 API 密钥
2. 重新启动容器：
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

## 7. 更新部署

当代码更新后，需要重新构建镜像：

```powershell
# 1. 停止当前服务
docker-compose down

# 2. 重新构建并启动
docker-compose up -d --build

# 3. 验证更新
docker-compose ps
```

## 8. 生产环境部署

### 使用 Docker Hub

1. 构建镜像并推送到 Docker Hub：
   ```powershell
   docker build -t yourusername/nuanxuebang-backend:latest ./backend
   docker push yourusername/nuanxuebang-backend:latest
   ```

2. 在服务器上拉取并运行：
   ```bash
   docker pull yourusername/nuanxuebang-backend:latest
   docker-compose up -d
   ```

### 使用云服务器

以阿里云为例：

1. 购买云服务器（ECS）
2. 安装 Docker
3. 上传项目文件
4. 执行 `docker-compose up -d`
5. 配置安全组，开放 8000 和 8501 端口

## 9. 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker 环境                           │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │   nuanxuebang-      │    │   nuanxuebang-      │        │
│  │   backend           │    │   rag-admin         │        │
│  │   (后端服务)         │    │   (知识库管理)       │        │
│  │                     │    │                     │        │
│  │   端口: 8000        │    │   端口: 8501        │        │
│  │                     │    │                     │        │
│  │   FastAPI           │    │   Streamlit         │        │
│  │   SQLite            │    │                     │        │
│  │   ChromaDB          │    │                     │        │
│  └─────────────────────┘    └─────────────────────┘        │
│           │                          │                      │
│           └──────────┬───────────────┘                      │
│                      │                                      │
│           ┌──────────▼───────────────┐                      │
│           │  nuanxuebang-network     │                      │
│           │  (Docker 网络)            │                      │
│           └──────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## 10. 注意事项

1. **API 密钥安全**：不要把真实的 API 密钥提交到代码仓库
2. **数据备份**：定期备份 `./backend/data/` 目录
3. **日志管理**：生产环境需要配置日志轮转，防止磁盘占满
4. **性能监控**：建议使用 `docker stats` 监控资源使用

## 11. 联系支持

如有问题，请查看：
- Docker 官方文档：https://docs.docker.com/
- 项目 GitHub Issues
- 开发者文档

---

**祝使用愉快！** 🌟
