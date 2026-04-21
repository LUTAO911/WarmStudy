# 暖学帮 Agent

青少年心理关怀AI智能体后端服务

## 安装

```bash
pip install -e .
```

## 测试

```bash
pytest tests/ -v
```

## 开发

```bash
# 安装依赖
pip install poetry
poetry install

# 运行测试
poetry run pytest tests/ -v --cov=agent
```
