"""测试核心功能"""
import os
import sys

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

print("测试核心功能...")

# 测试1: 检查模块导入
print("\n1. 测试模块导入:")
try:
    from app.core.agent import WarmChatAgent
    from app.core.llm import get_qwen_chat, get_qwen_embedding
    from app.rag.knowledge_base import get_knowledge_base
    from app.core.agent_enhancements import get_planning_module, get_reflection_module, get_self_improvement_module
    print("✓ 核心模块导入成功")
except Exception as e:
    print(f"✗ 核心模块导入失败: {e}")

# 测试2: 检查性能优化模块
try:
    from app.core.performance_optimization import ClientPool, ResponseCache, RateLimiter, CircuitBreaker
    print("✓ 性能优化模块导入成功")
except Exception as e:
    print(f"✗ 性能优化模块导入失败: {e}")

# 测试3: 检查多模态模块
try:
    from app.core.multimodal import get_multimodal_processor, get_multimodal_integration
    print("✓ 多模态模块导入成功")
except Exception as e:
    print(f"✗ 多模态模块导入失败: {e}")

# 测试4: 检查知识库功能
print("\n2. 测试知识库功能:")
try:
    from app.rag.knowledge_base import get_knowledge_base
    kb = get_knowledge_base()
    stats = kb.get_collection_stats()
    print(f"✓ 知识库初始化成功，文档数: {stats.get('total_documents', 0)}")
except Exception as e:
    print(f"✗ 知识库初始化失败: {e}")

# 测试5: 检查智能体功能
print("\n3. 测试智能体功能:")
try:
    from app.core.agent import get_agent
    agent = get_agent("test_user", "student")
    print("✓ 智能体初始化成功")
except Exception as e:
    print(f"✗ 智能体初始化失败: {e}")

# 测试6: 检查规划和反思模块
print("\n4. 测试规划和反思模块:")
try:
    from app.core.agent_enhancements import get_planning_module, get_reflection_module
    planning_module = get_planning_module()
    reflection_module = get_reflection_module()
    print("✓ 规划和反思模块初始化成功")
except Exception as e:
    print(f"✗ 规划和反思模块初始化失败: {e}")

print("\n测试完成！")
