"""项目健康度检查脚本"""
import sys
import os

# 添加backend目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_config():
    """检查配置"""
    print('\n1. 测试配置加载...')
    try:
        from app.config import get_settings
        settings = get_settings()
        print(f'✓ 配置加载成功')
        print(f'  - 项目名称: {settings.PROJECT_NAME}')
        print(f'  - 版本: {settings.VERSION}')
        return True
    except Exception as e:
        print(f'✗ 配置加载失败: {e}')
        return False

def check_llm():
    """检查LLM"""
    print('\n2. 测试LLM初始化...')
    try:
        from app.core.llm import get_qwen_chat, get_qwen_embedding
        llm = get_qwen_chat()
        embedding = get_qwen_embedding()
        print(f'✓ LLM初始化成功')
        return True
    except Exception as e:
        print(f'✗ LLM初始化失败: {e}')
        return False

def check_knowledge_base():
    """检查知识库"""
    print('\n3. 测试知识库...')
    try:
        from app.rag.knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        stats = kb.get_collection_stats()
        print(f'✓ 知识库初始化成功')
        print(f'  - 文档数: {stats.get("total_documents", 0)}')
        return True
    except Exception as e:
        print(f'✗ 知识库初始化失败: {e}')
        return False

def check_agent():
    """检查智能体"""
    print('\n4. 测试智能体...')
    try:
        from app.core.agent import get_agent
        agent = get_agent('test_user', 'student')
        print(f'✓ 智能体初始化成功')
        return True
    except Exception as e:
        print(f'✗ 智能体初始化失败: {e}')
        return False

def check_performance():
    """检查性能优化模块"""
    print('\n5. 测试性能优化模块...')
    try:
        from app.core.performance_optimization import ClientPool, ResponseCache, RateLimiter
        print(f'✓ 性能优化模块导入成功')
        return True
    except Exception as e:
        print(f'✗ 性能优化模块导入失败: {e}')
        return False

def check_multimodal():
    """检查多模态模块"""
    print('\n6. 测试多模态模块...')
    try:
        from app.core.multimodal import get_multimodal_processor
        processor = get_multimodal_processor()
        print(f'✓ 多模态模块初始化成功')
        print(f'  - 支持图像格式: {len(processor.supported_image_formats)} 种')
        print(f'  - 支持音频格式: {len(processor.supported_audio_formats)} 种')
        print(f'  - 支持视频格式: {len(processor.supported_video_formats)} 种')
        return True
    except Exception as e:
        print(f'✗ 多模态模块初始化失败: {e}')
        return False

def main():
    """主函数"""
    print('测试核心功能稳定性...')
    print('='*50)
    
    results = []
    results.append(('配置加载', check_config()))
    results.append(('LLM初始化', check_llm()))
    results.append(('知识库', check_knowledge_base()))
    results.append(('智能体', check_agent()))
    results.append(('性能优化', check_performance()))
    results.append(('多模态', check_multimodal()))
    
    print('\n' + '='*50)
    print('核心功能稳定性测试完成！')
    print('\n测试结果汇总:')
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f'通过: {passed}/{total}')
    
    for name, result in results:
        status = '✓' if result else '✗'
        print(f'  {status} {name}')
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
