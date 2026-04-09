"""RAG知识库Web管理界面 - 美化版"""
import streamlit as st
import requests
import json
from datetime import datetime
import time

st.set_page_config(
    page_title="WarmStudy Knowledge Base",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE = "http://localhost:8000/api"


st.markdown("""
<style>
    /* 主色调 */
    :root {
        --primary: #4A90D9;
        --secondary: #67C23A;
        --accent: #E6A23C;
        --danger: #F56C6C;
        --bg-dark: #1a1a2e;
        --bg-card: #16213e;
        --text: #eee;
    }

    /* 标题样式 */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }

    .sub-header {
        text-align: center;
        color: #888;
        margin-bottom: 2rem;
    }

    /* 卡片样式 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }

    .metric-card.green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        box-shadow: 0 8px 32px rgba(56, 239, 125, 0.3);
    }

    .metric-card.orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        box-shadow: 0 8px 32px rgba(245, 87, 108, 0.3);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }

    /* 搜索框样式 */
    .search-box {
        background: #f0f2f5;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    /* 文档卡片 */
    .doc-card {
        background: #fff;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid var(--primary);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }

    .doc-card:hover {
        transform: translateX(4px);
    }

    /* 标签样式 */
    .tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        margin: 2px;
    }

    .tag-primary { background: #e8f4fd; color: #4A90D9; }
    .tag-success { background: #e8f5e9; color: #67C23A; }
    .tag-warning { background: #fff3e0; color: #E6A23C; }

    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }

    /* 侧边栏样式 */
    .sidebar .stRadio > label {
        font-weight: 600;
        color: #4A90D9;
    }

    /* 消息样式 */
    .success-msg {
        padding: 1rem;
        border-radius: 8px;
        background: #e8f5e9;
        border-left: 4px solid #67C23A;
    }

    .error-msg {
        padding: 1rem;
        border-radius: 8px;
        background: #fff2f0;
        border-left: 4px solid #F56C6C;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """检查API健康状态"""
    try:
        resp = requests.get(f"{API_BASE.replace('/api', '')}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def get_stats():
    """获取知识库统计"""
    try:
        resp = requests.get(f"{API_BASE}/knowledge/stats", timeout=5)
        return resp.json().get("data", {})
    except:
        return {}


def get_categories():
    """获取分类列表"""
    try:
        resp = requests.get(f"{API_BASE}/knowledge/categories", timeout=5)
        return resp.json().get("data", {}).get("categories", [])
    except:
        return []


def search_knowledge(query, top_k=5, category=None):
    """搜索知识库"""
    try:
        resp = requests.post(
            f"{API_BASE}/knowledge/search",
            json={"query": query, "top_k": top_k, "category": category},
            timeout=10
        )
        return resp.json().get("data", {}).get("results", [])
    except Exception as e:
        return []


def add_document(title, content, category, tags=None):
    """添加文档"""
    try:
        resp = requests.post(
            f"{API_BASE}/knowledge/document",
            json={"title": title, "content": content, "category": category, "tags": tags or []},
            timeout=10
        )
        return resp.json()
    except Exception as e:
        return {"success": False, "message": str(e)}


def upload_file(file, category):
    """上传文件"""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        resp = requests.post(f"{API_BASE}/knowledge/upload", files=files, data={"category": category}, timeout=30)
        return resp.json()
    except Exception as e:
        return {"success": False, "message": str(e)}


def init_knowledge_base():
    """初始化知识库"""
    try:
        resp = requests.post(f"{API_BASE}/knowledge/init", timeout=60)
        return resp.json()
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_all_docs(limit=100):
    """获取所有文档"""
    try:
        resp = requests.get(f"{API_BASE}/knowledge/documents?limit={limit}", timeout=10)
        return resp.json().get("data", {}).get("documents", [])
    except:
        return []


st.markdown('<h1 class="main-header">📚 WarmStudy RAG Knowledge Base</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">基于 LangChain + Chroma 的智能心理知识库管理</p>', unsafe_allow_html=True)

if not check_api_health():
    st.error("⚠️ 无法连接到后端API服务，请确保后端已启动 (python main.py)")
    st.stop()

stats = get_stats()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card"><div class="metric-value">{}</div><div class="metric-label">📄 文档总数</div></div>'.format(
        stats.get("total_documents", 0)
    ), unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card green"><div class="metric-value">{}</div><div class="metric-label">📁 知识分类</div></div>'.format(
        stats.get("category_count", 0)
    ), unsafe_allow_html=True)

with col3:
    categories = get_categories()
    st.markdown('<div class="metric-card orange"><div class="metric-value">{}</div><div class="metric-label">🔍 可检索</div></div>'.format(
        "Yes" if stats.get("total_documents", 0) > 0 else "No"
    ), unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-card"><div class="metric-value">v2.0</div><div class="metric-label">✨ 系统版本</div></div>', unsafe_allow_html=True)

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 智能检索",
    "➕ 添加文档",
    "📁 文件管理",
    "📊 知识浏览"
])

with tab1:
    st.header("🔍 智能语义检索")

    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input(
            "输入你的问题",
            placeholder="例如：我最近很焦虑，该怎么办？",
            label_visibility="collapsed"
        )

    with col2:
        top_k = st.selectbox("返回数量", [3, 5, 10, 20], label_visibility="collapsed")

    category = st.selectbox("限定分类", ["全部"] + categories)

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        search_clicked = st.button("🔍 开始检索", type="primary", use_container_width=True)

    with col2:
        if st.button("🎲 示例问题", use_container_width=True):
            examples = [
                "如何缓解考试焦虑？",
                "孩子叛逆怎么办？",
                "什么是抑郁症？",
                "如何帮助有自杀倾向的人？",
                "青春期心理有哪些特点？"
            ]
            st.session_state.example_query = examples[int(time.time()) % len(examples)]

    if 'example_query' in st.session_state:
        query = st.session_state.example_query

    if query and search_clicked:
        with st.spinner("正在检索..."):
            results = search_knowledge(query, top_k, None if category == "全部" else category)

        if results:
            st.success(f"✨ 找到 {len(results)} 条相关内容")

            for i, item in enumerate(results, 1):
                with st.container():
                    st.markdown(f"""
                    <div class="doc-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h4>📄 结果 {i}</h4>
                            <span class="tag tag-primary">相似度: {item.get('score', 0):.1%}</span>
                        </div>
                        <p style="color:#333; line-height:1.6;">{item.get('content', '')[:300]}...</p>
                    </div>
                    """, unsafe_allow_html=True)

                    meta = item.get("metadata", {})
                    if meta:
                        cols = st.columns(4)
                        with cols[0]:
                            st.info(f"📁 {meta.get('category', 'unknown')}")
                        with cols[1]:
                            st.info(f"📌 {meta.get('title', 'untitled')}")

                    st.markdown("---")
        else:
            st.warning("未找到相关内容，尝试更换关键词或扩大搜索范围")

with tab2:
    st.header("➕ 添加文档")

    with st.form("add_doc_form", clear_on_submit=True):
        st.subheader("📝 手动添加")

        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("文档标题")

        with col2:
            category = st.selectbox("分类", [
                "情绪管理", "压力管理", "危机干预", "亲子教育",
                "学习方法", "人际关系", "青春期心理", "其他"
            ])

        tags = st.text_input("标签（逗号分隔）", placeholder="焦虑,情绪,放松技巧")

        content = st.text_area("文档内容", height=200, placeholder="输入文档内容...")

        submitted = st.form_submit_button("提交文档", type="primary")

        if submitted:
            if not title or not content:
                st.error("请填写标题和内容")
            else:
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                result = add_document(title, content, category, tag_list)
                if result.get("success"):
                    st.success("✅ 文档添加成功！")
                else:
                    st.error(f"❌ 添加失败: {result.get('message', '未知错误')}")

    st.markdown("---")

    st.subheader("💡 快速添加模板")

    templates = {
        "😰 焦虑情绪": {
            "title": "焦虑情绪调节方法",
            "category": "情绪管理",
            "tags": "焦虑,情绪调节,放松",
            "content": """# 焦虑情绪调节方法

## 深呼吸放松法（4-7-8呼吸）
1. 用鼻子吸气，数4下
2. 屏住呼吸，数7下
3. 用嘴呼气，数8下
4. 重复3-5次

## 54321 grounding技巧
当焦虑发作时，用感官回到当下：
- 说出5样能看到的东西
- 4样能触摸的东西
- 3样能听到的声音
- 2样能闻到的气味
- 1样能尝到的味道"""
        },
        "📝 考试焦虑": {
            "title": "考试焦虑应对策略",
            "category": "压力管理",
            "tags": "考试,焦虑,学习压力",
            "content": """# 考试焦虑应对

## 考前准备
- 制定合理的复习计划
- 保证充足睡眠（7-8小时）
- 适度运动放松

## 考试技巧
- 深呼吸放松
- 积极的自我暗示
- 从简单题目开始

## 考后心态
- 不要过度纠结
- 关注进步而非完美"""
        },
        "🚨 危机干预": {
            "title": "危机识别与求助",
            "category": "危机干预",
            "tags": "危机,自杀,求助",
            "content": """# 危机识别与求助

## 危险信号
- 言语：提到想死、活着没意思
- 行为：突然社交退缩、送礼物
- 情绪：长期绝望、无价值感

## 求助方式
📞 全国心理援助热线：400-161-9995
📞 北京心理危机干预中心：010-82951332

## 陪伴原则
- 不评判，认真倾听
- 表达关心
- 鼓励寻求专业帮助"""
        }
    }

    cols = st.columns(3)
    for idx, (name, template) in enumerate(templates.items()):
        with cols[idx]:
            if st.button(f"{name}", key=f"template_{idx}"):
                result = add_document(template["title"], template["content"], template["category"], template["tags"].split(","))
                if result.get("success"):
                    st.success(f"✅ 已添加：{template['title']}")
                else:
                    st.error("❌ 添加失败")

with tab3:
    st.header("📁 文件上传管理")

    st.info("支持上传 .md、.txt、.pdf、.docx、.xlsx、.csv、.json、.html 文件，系统会自动解析、分词并向量化")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader("选择文件", type=["md", "txt", "pdf", "docx", "xlsx", "csv", "json", "html"])

    with col2:
        upload_category = st.selectbox("分类", [
            "情绪管理", "压力管理", "危机干预", "亲子教育", "其他"
        ])

    if uploaded_file:
        st.write(f"📄 已选择: **{uploaded_file.name}** ({uploaded_file.size/1024:.1f} KB)")

        if st.button("🚀 上传并处理", type="primary", use_container_width=True):
            with st.spinner("正在上传和处理..."):
                result = upload_file(uploaded_file, upload_category)
                if result.get("success"):
                    st.success(f"✅ 上传成功！处理了 {result.get('data', {}).get('count', 0)} 个文档片段")
                else:
                    st.error(f"❌ 上传失败: {result.get('message', '未知错误')}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📥 初始化知识库")
        st.write("从 knowledge/ 目录加载所有文档")
        if st.button("🔄 初始化知识库", use_container_width=True):
            with st.spinner("正在初始化..."):
                result = init_knowledge_base()
                if result.get("success"):
                    st.success(f"✅ 初始化完成！加载了 {result.get('data', {}).get('document_count', 0)} 个文档")
                else:
                    st.error(f"❌ 初始化失败: {result.get('message', '未知错误')}")

    with col2:
        st.subheader("🗑️ 重置知识库")
        st.write("清空所有知识库数据（谨慎操作）")
        st.write("")
        if st.button("⚠️ 重置知识库", use_container_width=True):
            st.warning("此操作不可恢复！请确认。")

with tab4:
    st.header("📊 知识浏览")

    docs = get_all_docs()

    if docs:
        st.success(f"共有 {len(docs)} 篇文档")

        category_filter = st.selectbox("按分类筛选", ["全部"] + categories)

        filtered_docs = docs
        if category_filter != "全部":
            filtered_docs = [d for d in docs if d.get("metadata", {}).get("category") == category_filter]

        st.write(f"筛选后: {len(filtered_docs)} 篇")

        for i, doc in enumerate(filtered_docs[:20], 1):
            meta = doc.get("metadata", {})
            with st.expander(f"📄 {meta.get('title', doc.get('id', 'unknown'))} ({meta.get('category', 'unknown')})"):
                st.write(doc.get("content", ""))
                st.json(meta)
    else:
        st.info("暂无文档，请先初始化知识库或添加文档")

st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#888; padding:1rem;">
    <p>WarmStudy RAG Knowledge Base | Powered by LangChain + Chroma + Qwen</p>
    <p>© 2026 WarmStudy · Guarding Youth Mental Health</p>
</div>
""", unsafe_allow_html=True)