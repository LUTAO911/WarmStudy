"""初始化知识库 - 加载领域训练数据"""
import sys
import os

# 添加backend目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.knowledge_base import get_knowledge_base

def init_knowledge_base():
    """初始化知识库"""
    print("开始初始化知识库...")
    
    kb = get_knowledge_base()
    
    # 加载文档
    knowledge_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge')
    
    if not os.path.exists(knowledge_path):
        print(f"知识库目录不存在: {knowledge_path}")
        return
    
    print(f"从 {knowledge_path} 加载文档...")
    
    # 加载所有文档
    documents = kb.load_documents(knowledge_path)
    
    if not documents:
        print("没有找到可加载的文档")
        return
    
    print(f"找到 {len(documents)} 个文档片段")
    
    # 添加到知识库
    result = kb.add_documents(documents)
    
    if result.get("success"):
        print(f"✓ 成功添加 {result.get('count', 0)} 个文档到知识库")
    else:
        print(f"✗ 添加文档失败: {result.get('error', '未知错误')}")
    
    # 显示知识库统计
    stats = kb.get_collection_stats()
    print(f"\n知识库统计:")
    print(f"  - 总文档数: {stats.get('total_documents', 0)}")
    print(f"  - 分类数: {stats.get('category_count', 0)}")
    print(f"  - 分类列表: {', '.join(stats.get('categories', []))}")
    
    print("\n知识库初始化完成！")

if __name__ == "__main__":
    init_knowledge_base()
