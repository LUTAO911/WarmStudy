"""性能基准测试脚本"""
import sys
import os
import time
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Benchmark:
    """性能测试类"""
    
    def __init__(self):
        self.results = []
    
    def benchmark_embedding(self, iterations=10):
        """测试嵌入生成性能"""
        print('\n测试嵌入生成性能...')
        from app.core.llm import get_qwen_embedding
        
        embedding = get_qwen_embedding()
        test_texts = [
            "这是一个测试文本",
            "青少年心理健康很重要",
            "如何管理情绪压力",
            "亲子沟通技巧",
            "学业压力应对方法"
        ]
        
        times = []
        for i in range(iterations):
            start = time.time()
            try:
                for text in test_texts:
                    embedding.embed_query(text)
                elapsed = time.time() - start
                times.append(elapsed)
            except Exception as e:
                print(f'  迭代 {i+1} 失败: {e}')
        
        if times:
            avg_time = sum(times) / len(times)
            print(f'  平均时间: {avg_time:.3f}秒 ({len(test_texts)}个文本)')
            print(f'  每个文本平均: {avg_time/len(test_texts):.3f}秒')
            self.results.append(('嵌入生成', avg_time, '秒/5个文本'))
    
    def benchmark_knowledge_search(self, iterations=10):
        """测试知识库搜索性能"""
        print('\n测试知识库搜索性能...')
        from app.rag.knowledge_base import get_knowledge_base
        
        kb = get_knowledge_base()
        test_queries = [
            "情绪调节",
            "学业压力",
            "亲子沟通",
            "心理健康",
            "压力管理"
        ]
        
        times = []
        for i in range(iterations):
            start = time.time()
            try:
                for query in test_queries:
                    kb.search(query, top_k=3)
                elapsed = time.time() - start
                times.append(elapsed)
            except Exception as e:
                print(f'  迭代 {i+1} 失败: {e}')
        
        if times:
            avg_time = sum(times) / len(times)
            print(f'  平均时间: {avg_time:.3f}秒 ({len(test_queries)}次搜索)')
            print(f'  每次搜索平均: {avg_time/len(test_queries):.3f}秒')
            self.results.append(('知识库搜索', avg_time, '秒/5次搜索'))
    
    def benchmark_memory_usage(self):
        """测试内存使用"""
        print('\n测试内存使用...')
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # 加载所有模块
        from app.core.llm import get_qwen_chat, get_qwen_embedding
        from app.rag.knowledge_base import get_knowledge_base
        from app.core.agent import get_agent
        from app.core.multimodal import get_multimodal_processor
        
        llm = get_qwen_chat()
        embedding = get_qwen_embedding()
        kb = get_knowledge_base()
        agent = get_agent('benchmark_user', 'student')
        processor = get_multimodal_processor()
        
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before
        
        print(f'  加载前内存: {mem_before:.2f} MB')
        print(f'  加载后内存: {mem_after:.2f} MB')
        print(f'  内存使用: {mem_used:.2f} MB')
        self.results.append(('内存使用', mem_used, 'MB'))
    
    def run_all(self):
        """运行所有测试"""
        print('开始性能基准测试...')
        print('='*50)
        
        self.benchmark_embedding(iterations=5)
        self.benchmark_knowledge_search(iterations=5)
        
        try:
            self.benchmark_memory_usage()
        except ImportError:
            print('\n内存测试跳过 (需要安装psutil)')
        
        print('\n' + '='*50)
        print('性能基准测试完成！')
        print('\n测试结果汇总:')
        for name, value, unit in self.results:
            print(f'  {name}: {value:.3f} {unit}')

def main():
    """主函数"""
    benchmark = Benchmark()
    benchmark.run_all()

if __name__ == '__main__':
    main()
