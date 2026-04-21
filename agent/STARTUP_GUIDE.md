# 暖学帮 RAG 知识库 - 启动指南

## 环境要求

| 环境 | 要求 |
|------|------|
| Python | 3.10+ |
| Docker | 24.0+ |
| 内存 | 8GB+ |

---

## 方式一：venv 虚拟环境启动

### 1. 安装依赖

```bash
# 1. 进入项目目录
cd "c:\Users\34206\OneDrive\Desktop\项目\暖学帮"

# 2. 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 3. 进入agent目录
cd agent

# 4. 安装依赖（如果提示缺少包）
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `agent/.env` 文件：

```env
# 必需：阿里云DashScope API密钥
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# 可选配置
FLASK_ENV=production
LOG_LEVEL=INFO
```

### 3. 启动服务

**终端1：RAG Agent (端口 5177)**
```bash
cd agent
python app.py
```

**终端2：API 网关 (端口 8000)**
```bash
cd agent
python ../api_gateway.py
```

### 4. 访问

| 服务 | 地址 |
|------|------|
| RAG Web界面 | http://localhost:5177 |
| RAG API | http://localhost:5177/api |
| API网关 | http://localhost:8000 |

---

## 方式二：Docker 启动

### 1. 配置环境变量

编辑 `agent/.env` 文件：

```env
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 2. 构建并启动

```bash
# 进入agent目录
cd "c:\Users\34206\OneDrive\Desktop\项目\暖学帮\agent"

# 构建镜像
docker build -t nuanxuebang-rag:latest .

# 启动RAG服务 (端口5177)
docker run -d \
  --name rag-server \
  -p 5177:5177 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/uploads:/app/uploads \
  -e DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx \
  nuanxuebang-rag:latest

# 启动API网关 (端口8000)
docker run -d \
  --name api-gateway \
  -p 8000:8000 \
  -e RAG_AGENT_URL=http://rag-server:5177 \
  nuanxuebang-rag:latest \
  python api_gateway.py
```

### 3. Docker Compose 启动（推荐）

编辑 `docker-compose.yml`：

```bash
cd "c:\Users\34206\OneDrive\Desktop\项目\暖学帮\agent"

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4. 访问

| 服务 | 地址 |
|------|------|
| RAG Web界面 | http://localhost:5177 |
| API网关 | http://localhost:8000 |

---

## 方式三：完整前端+后端启动

### venv 环境

```bash
# 终端1：RAG Agent
cd agent
python app.py

# 终端2：API网关
python api_gateway.py

# 前端（暖学帮小程序）
# 在 暖学帮 项目目录中启动开发服务器
```

### Docker 环境

```bash
# 启动后端服务
cd agent
docker-compose up -d

# 前端需要单独启动（使用微信开发者工具或其他小程序开发工具）
```

---

## 验证服务

### 检查 RAG 服务状态

```bash
curl http://localhost:5177/api/agent/health
```

### 检查 API 网关状态

```bash
curl http://localhost:8000/api/health
```

### 检查索引状态

```bash
curl http://localhost:5177/api/status
```

---

## 常见问题

### 1. 端口被占用

```bash
# 查看端口占用
netstat -ano | findstr 5177
netstat -ano | findstr 8000

# 结束占用进程或更换端口
```

### 2. 缺少依赖

```bash
pip install -r requirements.txt
```

### 3. API Key 未配置

编辑 `agent/.env` 文件，确保配置了有效的 `DASHSCOPE_API_KEY`。

### 4. Docker 内存不足

Docker Desktop 设置中分配至少 8GB 内存。

---

## 数据目录

| 目录 | 用途 |
|------|------|
| `data/chroma` | 向量数据库文件 |
| `data/uploads` | 用户上传文件 |
| `logs` | 日志文件 |

---

## 一键启动脚本 (venv)

创建文件 `start_venv.bat`：

```batch
@echo off
cd /d "%~dp0"

echo 激活虚拟环境...
call .\.venv\Scripts\Activate.ps1

echo 启动 RAG Agent (端口 5177)...
start "RAG Agent" python app.py

echo 启动 API 网关 (端口 8000)...
start "API Gateway" python ../api_gateway.py

echo.
echo 服务已启动!
echo RAG Web: http://localhost:5177
echo API网关: http://localhost:8000
pause
```
