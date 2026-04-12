# RAG知识库系统运维手册

**项目**: 暖学帮智能知识库
**版本**: v3.0
**日期**: 2026-04-11

---

## 1. 日常运维

### 1.1 健康检查

```bash
# API 健康检查
curl http://localhost:5177/api/agent/health

# 索引状态
curl http://localhost:5177/api/agent/status

# 索引详情
curl http://localhost:5177/api/index/stats
```

### 1.2 日志查看

```bash
# 实时日志
tail -f logs/app.log

# 错误日志
grep -i error logs/app.log | tail -50

# 访问日志
tail -f logs/access.log

# 按时间过滤
grep "2026-04-11 10:" logs/app.log
```

### 1.3 监控指标

```bash
# Prometheus 指标
curl http://localhost:5177/api/agent/metrics

# 当前会话
curl http://localhost:5177/api/agent/status

# 活跃告警
curl http://localhost:5177/api/agent/metrics | jq '.alerts'
```

---

## 2. 故障处理

### 2.1 服务无响应

```bash
# 1. 检查进程
ps aux | grep python

# 2. 检查端口
netstat -tlnp | grep 5177

# 3. 重启服务
sudo systemctl restart rag-agent

# 4. 查看重启原因
sudo journalctl -u rag-agent -n 50
```

### 2.2 数据库问题

```bash
# 检查 ChromaDB 数据目录
ls -la data/chroma/

# 验证数据完整性
python -c "import chromadb; c = chromadb.PersistentClient('data/chroma'); print(c.list_collections())"

# 重建索引 (谨慎)
curl -X POST http://localhost:5177/api/reset
```

### 2.3 内存泄漏

```bash
# 查看内存使用
ps aux | grep python

# 详细内存分析
python -c "
import tracemalloc
tracemalloc.start()
# 运行一段时间后
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"

# 重启释放内存
sudo systemctl restart rag-agent
```

### 2.4 磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 查看大文件
du -sh data/* | sort -h

# 清理日志
rm -rf logs/*.log.* && sudo systemctl restart rag-agent

# 清理上传目录
find uploads/ -type f -mtime +30 -delete
```

---

## 3. 性能优化

### 3.1 查询性能

```bash
# 启用缓存
curl -X POST http://localhost:5177/api/agent/cache/invalidate

# 调整混合搜索权重
# 编辑 vectorstore.py 中 HybridSearchEngine 的 vector_weight/bm25_weight
```

### 3.2 批量索引优化

```python
# 在 ingest_to_chroma 调用时调整
result = ingest_to_chroma(
    docs,
    persist_dir="data/chroma",
    collection_name="knowledge_base",
    batch_size=50,  # 增大批次
    chunk_size=500,
    chunk_overlap=50
)
```

### 3.3 自适应调参

```bash
# 查看当前权重
curl http://localhost:5177/api/agent/metrics | jq '.adaptive_weights'

# 记录反馈 (通过API使用后自动触发)
# 系统会根据用户反馈自动调整 vector_weight 和 bm25_weight
```

---

## 4. 数据管理

### 4.1 备份

```bash
# 全量备份脚本
#!/bin/bash
BACKUP_DIR=/opt/backups/rag
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份向量数据库
tar -czf $BACKUP_DIR/chroma_$DATE.tar.gz data/chroma/

# 备份上传文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz uploads/

# 备份配置
cp -r config/ $BACKUP_DIR/config_$DATE/

# 保留最近30天
find $BACKUP_DIR -mtime +30 -delete

echo "Backup completed: $DATE"
```

### 4.2 恢复

```bash
# 停止服务
sudo systemctl stop rag-agent

# 恢复数据
tar -xzf /path/to/backup/chroma_20260411.tar.gz -C /

# 启动服务
sudo systemctl start rag-agent

# 验证
curl http://localhost:5177/api/index/stats
```

### 4.3 数据迁移

```bash
# 导出到新服务器
# 1. 源服务器
tar -czf data_migration.tar.gz data/chroma/ config/

# 2. 传输
scp data_migration.tar.gz user@new-server:/tmp/

# 3. 目标服务器
tar -xzf /tmp/data_migration.tar.gz -C /opt/nuanxuebang/agent/
```

---

## 5. 安全运维

### 5.1 API Key 管理

```bash
# 查看当前配置
grep DASHSCOPE_API_KEY .env

# 更新 Key
sed -i 's/DASHSCOPE_API_KEY=.*/DASHSCOPE_API_KEY=new_key_here/' .env

# 重启服务
sudo systemctl restart rag-agent
```

### 5.2 访问控制

```nginx
# 限制 IP 访问
location /api/ {
    allow 10.0.0.0/8;
    allow 192.168.0.0/16;
    deny all;
}
```

### 5.3 日志审计

```bash
# 审计错误日志
grep -E "(ERROR|WARNING)" logs/app.log | \
  awk '{print $1,$2,$3,$NF}' | sort | uniq -c

# 审计异常请求
grep -B5 "500\|502\|503" logs/access.log | head -50
```

---

## 6. 监控告警

### 6.1 告警规则

| 规则名称 | 指标 | 阈值 | 级别 |
|----------|------|------|------|
| HighCPU | cpu_percent | >80% | WARNING |
| HighMemory | memory_percent | >85% | WARNING |
| HighErrorRate | error_rate | >10% | ERROR |
| SlowResponse | avg_response_time | >10s | WARNING |

### 6.2 告警处理

```python
# 自定义告警处理器
def custom_alert_handler(alert):
    # 发送邮件
    send_email(
        to="ops@company.com",
        subject=f"[{alert.level}] RAG Alert: {alert.rule_name}",
        body=alert.message
    )
    # 或发送钉钉/飞书
    send_dingtalk(alert.message)

# 注册处理器
from agent.utils.monitor import PerformanceMonitor
monitor = PerformanceMonitor()
monitor.add_alert_handler(custom_alert_handler)
```

### 6.3 Prometheus 集成

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'rag-agent'
    static_configs:
      - targets: ['localhost:5177']
    metrics_path: '/api/agent/metrics'
    scrape_interval: 15s
```

---

## 7. 升级维护

### 7.1 版本升级

```bash
# 1. 备份当前版本
cp -r agent agent_backup_$(date +%Y%m%d)

# 2. 拉取新版本
git pull origin main

# 3. 更新依赖
pip install -r requirements.txt

# 4. 检查配置变更
diff .env.example .env

# 5. 测试运行
python app.py &

# 6. 验证功能
curl http://localhost:5177/api/status

# 7. 重启生产服务
sudo systemctl restart rag-agent
```

### 7.2 回滚操作

```bash
# 停止当前版本
sudo systemctl stop rag-agent

# 恢复备份
rm -rf agent
mv agent_backup_20260410 agent

# 重启
sudo systemctl start rag-agent
```

---

## 8. 运维检查清单

### 每日检查
- [ ] 服务运行状态
- [ ] 错误日志数量
- [ ] 磁盘空间使用
- [ ] 内存使用情况
- [ ] 响应时间正常

### 每周检查
- [ ] 备份完整性
- [ ] 日志轮转
- [ ] 监控告警
- [ ] 性能趋势
- [ ] 安全更新

### 每月检查
- [ ] 灾难恢复演练
- [ ] 容量规划
- [ ] 性能基准测试
- [ ] 依赖安全审计
- [ ] 文档更新

---

## 9. 紧急联系

| 角色 | 职责 | 联系方式 |
|------|------|----------|
| 运维负责人 | 故障响应 | - |
| 开发负责人 | 技术支持 | - |
| DBA | 数据库问题 | - |

---

## 10. 常用命令速查

```bash
# 服务管理
sudo systemctl start rag-agent     # 启动
sudo systemctl stop rag-agent      # 停止
sudo systemctl restart rag-agent   # 重启
sudo systemctl status rag-agent     # 状态

# 日志
tail -f logs/app.log               # 实时日志
grep error logs/app.log            # 错误日志

# 监控
curl http://localhost:5177/api/agent/status  # 健康检查
curl http://localhost:5177/api/agent/metrics # 指标

# 数据
curl -X POST http://localhost:5177/api/reset  # 重置索引
curl -X POST http://localhost:5177/api/agent/cache/invalidate  # 清除缓存

# 备份
tar -czf backup.tar.gz data/       # 备份数据
```
