# 暖学帮 Web 前端

Python / Flask 编写的浏览器端前端，功能对应现有微信小程序（`WarnStudty/`）。

## 项目结构

```
web/
├── app.py               # Flask 应用入口
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量示例
├── templates/
│   ├── base.html        # 公共布局模板
│   ├── login.html       # 登录 / 身份选择页
│   ├── error.html       # 错误页
│   ├── student/
│   │   ├── chat.html       # 学生 AI 对话页
│   │   ├── assessment.html # 心理测评页（打卡 + 量表 + 雷达图）
│   │   └── library.html    # 心理知识库搜索页
│   └── parent/
│       ├── index.html   # 家长中心（仪表盘）
│       └── chat.html    # 家长 AI 助手
└── static/
    ├── css/main.css     # 主样式（温暖设计系统）
    └── js/main.js       # 公共 JS 工具
```

## 功能说明

| 角色 | 页面 | 功能 |
|------|------|------|
| 学生 | AI 对话 | 多角色 AI 聊天（暖暖 / 智慧导师 / 知心姐姐）、快捷问题、多会话 |
| 学生 | 心理测评 | 今日四维打卡（情绪/睡眠/学习/社交）、三套专业量表（MHT / PSS / 亲子沟通）、雷达图画像 |
| 学生 | 知识库 | 关键词搜索知识库（调用后端混合搜索 API）、精选内容卡片 |
| 家长 | 家长中心 | 孩子打卡汇总、AI 建议、心理画像雷达、本周打卡日历、成绩趋势、测评报告 |
| 家长 | AI 助手 | 专业家庭教育顾问对话 |

## 快速启动

### 1. 安装依赖

```bash
cd web
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

复制 `.env.example` 为 `.env` 并按需修改：

```env
# Agent 后端 API 地址（默认 http://localhost:5001）
AGENT_API_URL=http://localhost:5001

# Web 应用密钥（建议生产环境更换）
WEB_SECRET_KEY=your-secret-key

# Web 服务端口（默认 5002）
WEB_PORT=5002

# 调试模式（默认 true）
WEB_DEBUG=true
```

### 3. 启动服务

```bash
python app.py
```

访问 [http://localhost:5002](http://localhost:5002)

### 4. 与 Agent 后端联动

先启动 Agent 后端（`agent/app.py`，默认 5001 端口），Web 前端会自动将对话和搜索请求转发到后端。若后端不可用，各功能页面仍可正常显示，AI 对话功能会提示后端不可用。

## 技术栈

- **Python 3.10+**
- **Flask 3.x** — Web 框架 + Jinja2 模板引擎
- **HTML5 / CSS3 / 原生 JS** — 无额外前端框架依赖
- **Canvas API** — 雷达图绘制
- **Fetch API** — 与后端 API 通信

## 设计说明

- 学生端主色：`#00C853`（绿），家长端主色：`#FF9500`（橙）
- 完整响应式布局，支持移动端访问
- 侧边栏在小屏幕时自动折叠为图标模式
