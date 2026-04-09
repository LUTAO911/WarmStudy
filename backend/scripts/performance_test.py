"""性能测试脚本"""
import sys
import os
import time
import asyncio

# 添加backend目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.llm import get_qwen_chat, get_qwen_embedding
from app.rag.knowledge_base import get_knowledge_base
from app.core.agent import get_agent

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results = []
    
    def test_llm_response_time(self, iterations=5):
        """测试LLM响应时间"""
        print("\n=== 测试LLM响应时间 ===")
        llm = get_qwen_chat()
        
        from langchain_core.messages import HumanMessage
        test_message = "你好，请简单介绍一下自己"
        
        times = []
        for i in range(iterations):
            start = time.time()
            try:
                response = llm.invoke([HumanMessage(content=test_message)])
                elapsed = time.time() - start
                times.append(elapsed)
                print(f"  迭代 {i+1}: {elapsed:.2f}秒")
            except Exception as e:
                print(f"  迭代 {i+1}: 失败 - {e}")
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            print(f"\n  平均响应时间: {avg_time:.2f}秒")
            print(f"  最快响应时间: {min_time:.2f}秒")
            print(f"  最慢响应时间: {max_time:.2f}秒")
            self.results.append({"test": "LLM响应时间", "avg": avg_time, "min": min_time, "max": max_time})
    
    def test_embedding_speed(self, iterations=5):
        """测试嵌入生成速度"""
        print("\n=== 测试嵌入生成速度 ===")
        embedding = get_qwen_embedding()
        
        test_texts = [
            "这是一个测试文本",
            "青少年心理健康很重要",
            "如何管理情绪压力"
        ]
        
        times = []
        for i in range(iterations):
            start = time.time()
            try:
                for text in test_texts:
                    embedding.embed_query(text)
                elapsed = time.time() - start
                times.append(elapsed)
                print(f"  迭代 {i+1}: {elapsed:.2f}秒 (3个文本)")
            except Exception as e:
                print(f"  迭代 {i+1}: 失败 - {e}")
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"\n  平均时间: {avg_time:.2f}秒")
            print(f"  每个文本平均: {avg_time/3:.2f}秒")
            self.results.append({"test": "嵌入生成速度", "avg": avg_time, "per_text": avg_time/3})
    
    def test_knowledge_search(self, iterations=5):
        """测试知识库搜索速度"""
        print("\n=== 测试知识库搜索速度 ===")
        kb = get_knowledge_base()
        
        test_queries = [
            "情绪调节方法",
            "学业压力",
            "亲子沟通"
        ]
        
        times = []
        for i in range(iterations):
            start = time.time()
            try:
                for query in test_queries:
                    kb.search(query, top_k=3)
                elapsed = time.time() - start
                times.append(elapsed)
                print(f"  迭代 {i+1}: {elapsed:.2f}秒 (3次搜索)")
            except Exception as e:
                print(f"  迭代 {i+1}: 失败 - {e}")
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"\n  平均时间: {avg_time:.2f}秒")
            print(f"  每次搜索平均: {avg_time/3:.2f}秒")
            self.results.append({"test": "知识库搜索", "avg": avg_time, "per_query": avg_time/3})
    
    def test_agent_response(self, iterations=3):
        """测试智能体响应时间"""
        print("\n=== 测试智能体响应时间 ===")
        agent = get_agent("test_user", "student")
        
        test_messages = [
            "你好",
            "我最近感觉很焦虑",
            "有什么方法可以缓解压力吗"
        ]
        
        times = []
        for i, message in enumerate(test_messages):
            start = time.time()
            try:
                result = agent.chat("test_user", message)
                elapsed = time.time() - start
                times.append(elapsed)
                print(f"  消息 {i+1}: {elapsed:.2f}秒 - {message[:20]}...")
            except Exception as e:
                print(f"  消息 {i+1}: 失败 - {e}")
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"\n  平均响应时间: {avg_time:.2f}秒")
            self.results.append({"test": "智能体响应", "avg": avg_time})
    
    def generate_report(self):
        """生成性能报告"""
        print("\n" + "="*50)
        print("性能测试报告")
        print("="*50)
        
        for result in self.results:
            print(f"\n{result['test']}:")
            for key, value in result.items():
                if key != 'test':
                    if isinstance(value, float):
                        print(f"  {key}: {value:.2f}秒")
                    else:
                        print(f"  {key}: {value}")
        
        print("\n" + "="*50)
        print("优化建议:")
        print("="*50)
        print("1. 使用响应缓存减少重复API调用")
        print("2. 实现异步处理提高并发能力")
        print("3. 优化知识库索引结构")
        print("4. 使用客户端池减少连接开销")
        print("5. 考虑使用本地模型减少网络延迟")

def main():
    """主函数"""
    print("开始性能测试...")
    print("="*50)
    
    tester = PerformanceTester()
    
    # 运行测试
    tester.test_llm_response_time(iterations=3)
    tester.test_embedding_speed(iterations=3)
    tester.test_knowledge_search(iterations=3)
    tester.test_agent_response()
    
    # 生成报告
    tester.generate_report()
    
    print("\n性能测试完成！")

if __name__ == "__main__":
    main()
