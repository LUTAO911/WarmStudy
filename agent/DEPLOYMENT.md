# RAG知识库系统部署文档

**项目**: 暖学帮智能知识库
**版本**: v3.0
**日期**: 2026-04-11

---

## 1. 环境要求

### 1.1 硬件要求

| 环境 | CPU | 内存 | 磁盘 | 说明 |
|------|-----|------|------|------|
| 开发环境 | 4核+ | 8GB+ | 20GB+ | 本地测试 |
| 生产环境 | 8核+ | 16GB+ | 100GB+ | SSD推荐 |
| 分布式节点 | 4核+ | 8GB+ | 50GB+ | 每节点 |

### 1.2 软件要求

- Python 3.10+
- Node.js 18+ (前端)
- Docker 24+ (可选)
- Redis 7+ (可选，缓存层)
- MongoDB 6+ (可选，日志存储)

### 1.3 环境变量

```bash
# 必需
DASHSCOPE_API_KEY=your_api_key_here

# 可选
FLASK_ENV=production
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379
MONGODB_URI=mongodb://localhost:27017
```

---

## 2. 本地部署

### 2.1 基础安装

```bash
# 1. 克隆项目
git clone <repository_url>
cd 暖学帮/agent

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 5. 初始化数据目录
mkdir -p data/chroma uploads logs

# 6. 运行服务
python app.py
```

### 2.2 前端部署

```bash
cd ../web  # 前端项目目录
npm install
npm run build
# 静态文件放入 agent/static/
```

---

## 3. Docker部署

### 3.1 单节点部署

```bash
# 构建镜像
docker build -t nuanxuebang-rag:latest .

# 运行容器
docker run -d \
  --name rag-server \
  -p 5177:5177 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/logs:/app/logs \
  -e DASHSCOPE_API_KEY=your_api_key \
  nuanxuebang-rag:latest
```

### 3.2 Docker Compose 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  rag:
    build: .
    ports:
      - "5177:5177"
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - FLASK_ENV=production
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

```bash
# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f rag

# 停止
docker-compose down
```

---

## 4. 分布式部署

### 4.1 架构概览

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │   (Nginx/HAProxy)│
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ Node 1  │          │ Node 2  │          │ Node 3  │
   │ ChromaDB│          │ ChromaDB│          │ ChromaDB│
   │ :8001   │          │ :8002   │          │ :8003   │
   └─────────┘          └─────────┘          └─────────┘
```

### 4.2 节点配置

```json
// config/distributed_nodes.json
{
  "nodes": [
    {
      "host": "192.168.1.101",
      "port": 8001,
      "persist_dir": "/data/chroma_node1",
      "collection_name": "knowledge_base",
      "weight": 2
    },
    {
      "host": "192.168.1.102",
      "port": 8002,
      "persist_dir": "/data/chroma_node2",
      "collection_name": "knowledge_base",
      "weight": 2
    },
    {
      "host": "192.168.1.103",
      "port": 8003,
      "persist_dir": "/data/chroma_node3",
      "collection_name": "knowledge_base",
      "weight": 1
    }
  ],
  "enable_failover": true,
  "enable_monitoring": true
}
```

### 4.3 Nginx 配置

```nginx
upstream rag_backend {
    least_conn;
    server 192.168.1.101:5177 weight=2;
    server 192.168.1.102:5177 weight=2;
    server 192.168.1.103:5177 backup;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://rag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
    }

    location /api/stream {
        proxy_pass http://rag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
    }
}
```

---

## 5. 生产环境配置

### 5.1 Systemd 服务

```ini
# /etc/systemd/system/rag-agent.service
[Unit]
Description=RAG Knowledge Base Agent
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/nuanxuebang/agent
Environment="PATH=/opt/nuanxuebang/venv/bin"
Environment="DASHSCOPE_API_KEY=your_key"
ExecStart=/opt/nuanxuebang/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl enable rag-agent
sudo systemctl start rag-agent
sudo systemctl status rag-agent
```

### 5.2 日志轮转

```bash
# /etc/logrotate.d/rag-agent
/opt/nuanxuebang/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    postrotate
        systemctl reload rag-agent > /dev/null 2>&1 || true
    endscript
}
```

---

## 6. HTTPS 配置

### 6.1 Let's Encrypt 证书

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加: 0 0 * * * certbot renew --quiet
```

### 6.2 反向代理 HTTPS

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://rag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
    }
}
```

---

## 7. 性能调优

### 7.1 Gunicorn 配置

```python
# gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:5177"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
preload_app = True
```

```bash
# 运行
gunicorn -c gunicorn_config.py app:app
```

### 7.2 ChromaDB 调优

```python
# 在 vectorstore.py 中
collection = client.get_or_create_collection(
    name="knowledge_base",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 100,  # 构建索引时的参数
        "hnsw:search_ef": 100,          # 搜索时的参数
        "hnsw:M": 16                    # 连接数
    }
)
```

---

## 8. 部署检查清单

### 部署前
- [ ] 服务器环境确认
- [ ] 依赖安装完成
- [ ] 配置文件就绪
- [ ] API Key 配置
- [ ] 数据目录创建

### 部署后
- [ ] 服务启动验证
- [ ] 健康检查通过
- [ ] API 接口测试
- [ ] 日志输出正常
- [ ] 监控指标正常

### 上线前
- [ ] 性能基准测试
- [ ] 故障切换测试
- [ ] 备份策略验证
- [ ] 安全扫描通过
- [ ] 文档更新完成

---

## 9. 快速命令参考

```bash
# 启动服务
python app.py

# Docker 部署
docker-compose up -d

# 查看状态
curl http://localhost:5177/api/status

# 查看日志
tail -f logs/app.log

# 重启服务
sudo systemctl restart rag-agent

# 备份数据
tar -czf backup_$(date +%Y%m%d).tar.gz data/
```
