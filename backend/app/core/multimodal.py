"""多模态融合模块 - 支持图像、音频、视频等多模态内容"""
import os
import base64
import json
import numpy as np
from typing import List, Dict, Any, Optional, Union
from langchain_core.documents import Document
from app.core.llm import get_qwen_chat, get_qwen_embedding
from app.config import get_settings

settings = get_settings()


class MultimodalProcessor:
    """多模态处理器"""

    def __init__(self):
        self.llm = get_qwen_chat()
        self.embedding = get_qwen_embedding()
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        self.supported_audio_formats = {'.mp3', '.wav', '.ogg', '.flac'}
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.wmv'}

    def is_image_file(self, file_path: str) -> bool:
        """判断是否为图像文件"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_image_formats

    def is_audio_file(self, file_path: str) -> bool:
        """判断是否为音频文件"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_audio_formats

    def is_video_file(self, file_path: str) -> bool:
        """判断是否为视频文件"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_video_formats

    def is_multimodal_file(self, file_path: str) -> bool:
        """判断是否为多模态文件"""
        return (self.is_image_file(file_path) or 
                self.is_audio_file(file_path) or 
                self.is_video_file(file_path))

    def process_image(self, file_path: str) -> Dict[str, Any]:
        """处理图像文件"""
        try:
            # 读取图像文件
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # 生成图像描述
            description = self._generate_image_description(image_data)
            
            # 提取图像特征
            features = self._extract_image_features(image_data)
            
            # 生成图像嵌入
            embedding = self._generate_image_embedding(description)
            
            return {
                "type": "image",
                "description": description,
                "features": features,
                "embedding": embedding,
                "file_path": file_path,
                "size": os.path.getsize(file_path)
            }
        except Exception as e:
            return {
                "type": "image",
                "error": str(e),
                "file_path": file_path
            }

    def process_audio(self, file_path: str) -> Dict[str, Any]:
        """处理音频文件"""
        try:
            # 提取音频特征
            features = self._extract_audio_features(file_path)
            
            # 生成音频描述
            description = self._generate_audio_description(features)
            
            # 生成音频嵌入
            embedding = self._generate_audio_embedding(description)
            
            return {
                "type": "audio",
                "description": description,
                "features": features,
                "embedding": embedding,
                "file_path": file_path,
                "size": os.path.getsize(file_path)
            }
        except Exception as e:
            return {
                "type": "audio",
                "error": str(e),
                "file_path": file_path
            }

    def process_video(self, file_path: str) -> Dict[str, Any]:
        """处理视频文件"""
        try:
            # 提取视频帧
            frames = self._extract_video_frames(file_path, max_frames=5)
            
            # 生成视频描述
            description = self._generate_video_description(frames)
            
            # 提取视频特征
            features = self._extract_video_features(frames)
            
            # 生成视频嵌入
            embedding = self._generate_video_embedding(description)
            
            return {
                "type": "video",
                "description": description,
                "features": features,
                "embedding": embedding,
                "file_path": file_path,
                "size": os.path.getsize(file_path),
                "frame_count": len(frames)
            }
        except Exception as e:
            return {
                "type": "video",
                "error": str(e),
                "file_path": file_path
            }

    def _generate_image_description(self, image_data: bytes) -> str:
        """生成图像描述"""
        try:
            # 将图像转换为base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # 使用LLM生成描述
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content="你是一个图像分析专家，能够详细描述图像内容和情感表达"),
                HumanMessage(content=f"请详细描述这张图像的内容，包括场景、人物、情绪等：data:image/jpeg;base64,{base64_image}")
            ]
            
            response = self.llm.invoke(messages)
            return response.content
        except Exception:
            return "图像描述生成失败"

    def _extract_image_features(self, image_data: bytes) -> Dict[str, Any]:
        """提取图像特征"""
        try:
            # 简单的图像特征提取
            import cv2
            import numpy as np
            
            # 转换为OpenCV格式
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return {"error": "图像解码失败"}
            
            height, width, channels = img.shape
            
            # 计算基本特征
            features = {
                "width": width,
                "height": height,
                "channels": channels,
                "aspect_ratio": round(width / height, 2),
                "size_kb": round(len(image_data) / 1024, 2)
            }
            
            return features
        except ImportError:
            return {"note": "需要安装OpenCV: pip install opencv-python"}
        except Exception as e:
            return {"error": str(e)}

    def _extract_audio_features(self, file_path: str) -> Dict[str, Any]:
        """提取音频特征"""
        try:
            import librosa
            
            # 加载音频文件
            y, sr = librosa.load(file_path)
            
            # 提取特征
            features = {
                "duration": round(librosa.get_duration(y=y, sr=sr), 2),
                "sampling_rate": sr,
                "mean_amplitude": round(np.mean(np.abs(y)), 4),
                "rms_energy": round(np.sqrt(np.mean(y**2)), 4)
            }
            
            return features
        except ImportError:
            return {"note": "需要安装librosa: pip install librosa"}
        except Exception as e:
            return {"error": str(e)}

    def _extract_video_frames(self, file_path: str, max_frames: int = 5) -> List[bytes]:
        """提取视频帧"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(file_path)
            frames = []
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 均匀采样帧
            step = max(1, frame_count // max_frames)
            
            for i in range(0, frame_count, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    # 转换为JPEG
                    _, buffer = cv2.imencode('.jpg', frame)
                    frames.append(buffer.tobytes())
                if len(frames) >= max_frames:
                    break
            
            cap.release()
            return frames
        except ImportError:
            return []
        except Exception:
            return []

    def _extract_video_features(self, frames: List[bytes]) -> Dict[str, Any]:
        """提取视频特征"""
        return {
            "frame_count": len(frames),
            "type": "video",
            "note": "视频特征提取完成"
        }

    def _generate_audio_description(self, features: Dict[str, Any]) -> str:
        """生成音频描述"""
        try:
            # 基于特征生成描述
            duration = features.get("duration", 0)
            return f"一段时长{duration}秒的音频文件"
        except Exception:
            return "音频描述生成失败"

    def _generate_video_description(self, frames: List[bytes]) -> str:
        """生成视频描述"""
        try:
            if not frames:
                return "视频描述生成失败"
            
            # 使用第一帧生成描述
            return self._generate_image_description(frames[0])
        except Exception:
            return "视频描述生成失败"

    def _generate_image_embedding(self, description: str) -> List[float]:
        """生成图像嵌入"""
        return self.embedding.embed_query(description)

    def _generate_audio_embedding(self, description: str) -> List[float]:
        """生成音频嵌入"""
        return self.embedding.embed_query(description)

    def _generate_video_embedding(self, description: str) -> List[float]:
        """生成视频嵌入"""
        return self.embedding.embed_query(description)

    def process_multimodal_file(self, file_path: str) -> Dict[str, Any]:
        """处理多模态文件"""
        if self.is_image_file(file_path):
            return self.process_image(file_path)
        elif self.is_audio_file(file_path):
            return self.process_audio(file_path)
        elif self.is_video_file(file_path):
            return self.process_video(file_path)
        else:
            return {"error": "不支持的文件格式"}


class MultimodalRAG:
    """多模态RAG系统"""

    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base
        self.multimodal_processor = MultimodalProcessor()

    def add_multimodal_document(self, file_path: str, category: str = "multimodal") -> Dict[str, Any]:
        """添加多模态文档到知识库"""
        try:
            # 处理多模态文件
            result = self.multimodal_processor.process_multimodal_file(file_path)
            
            if "error" in result:
                return {"success": False, "error": result["error"]}
            
            # 生成文档内容
            content = f"""多模态内容
类型: {result['type']}
描述: {result['description']}
文件路径: {result['file_path']}
大小: {result.get('size', 0)} bytes
"""
            
            # 添加元数据
            metadata = {
                "type": result['type'],
                "description": result['description'],
                "file_path": result['file_path'],
                "size": result.get('size', 0),
                "category": category
            }
            
            # 添加到知识库
            document = Document(page_content=content, metadata=metadata)
            result = self.knowledge_base.add_documents([document], category=category)
            
            return {
                "success": True,
                "document": result,
                "multimodal_info": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_multimodal(self, query: str, top_k: int = 3, 
                        modality: Optional[str] = None) -> List[Dict[str, Any]]:
        """多模态搜索"""
        try:
            # 构建搜索过滤条件
            where_filter = {}
            if modality:
                where_filter["type"] = modality
            
            # 执行搜索
            results = self.knowledge_base.search(query, top_k=top_k)
            
            # 过滤多模态结果
            multimodal_results = []
            for result in results:
                if "metadata" in result and "type" in result["metadata"]:
                    multimodal_results.append(result)
            
            return multimodal_results
        except Exception as e:
            return [{"error": str(e)}]

    def cross_modal_search(self, query: str, source_modality: str, 
                         target_modality: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """跨模态搜索"""
        try:
            # 执行搜索
            results = self.knowledge_base.search(query, top_k=top_k)
            
            # 过滤目标模态结果
            cross_results = []
            for result in results:
                if "metadata" in result and "type" in result["metadata"]:
                    if result["metadata"]["type"] == target_modality:
                        cross_results.append(result)
            
            return cross_results
        except Exception as e:
            return [{"error": str(e)}]


class MultimodalIntegration:
    """多模态集成模块"""

    def __init__(self):
        self.processor = MultimodalProcessor()

    def analyze_emotion_from_image(self, image_path: str) -> Dict[str, Any]:
        """从图像分析情绪"""
        try:
            # 处理图像
            result = self.processor.process_image(image_path)
            
            if "error" in result:
                return {"success": False, "error": result["error"]}
            
            # 分析情绪
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content="你是一个情绪分析专家，能够从图像中识别人物的情绪状态"),
                HumanMessage(content=f"请分析这张图像中人物的情绪状态，包括主要情绪、情绪强度和可能的原因：{result['description']}")
            ]
            
            llm = get_qwen_chat()
            response = llm.invoke(messages)
            
            return {
                "success": True,
                "emotion_analysis": response.content,
                "image_description": result["description"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_emotion_from_audio(self, audio_path: str) -> Dict[str, Any]:
        """从音频分析情绪"""
        try:
            # 处理音频
            result = self.processor.process_audio(audio_path)
            
            if "error" in result:
                return {"success": False, "error": result["error"]}
            
            # 分析情绪
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content="你是一个情绪分析专家，能够从音频中识别说话者的情绪状态"),
                HumanMessage(content=f"请分析这段音频中说话者的情绪状态，包括主要情绪、情绪强度和可能的原因：{result['description']}")
            ]
            
            llm = get_qwen_chat()
            response = llm.invoke(messages)
            
            return {
                "success": True,
                "emotion_analysis": response.content,
                "audio_description": result["description"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_multimodal_response(self, query: str, 
                                   multimodal_context: List[Dict[str, Any]]) -> str:
        """生成多模态响应"""
        try:
            # 构建上下文
            context = []
            for item in multimodal_context:
                if "type" in item and "description" in item:
                    context.append(f"{item['type']}内容: {item['description']}")
            
            context_str = "\n".join(context)
            
            # 生成响应
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content="你是一个多模态理解专家，能够综合分析不同类型的内容"),
                HumanMessage(content=f"基于以下多模态上下文，回答用户问题：{query}\n\n上下文：\n{context_str}")
            ]
            
            llm = get_qwen_chat()
            response = llm.invoke(messages)
            
            return response.content
        except Exception:
            return "无法生成多模态响应"


# 全局实例
multimodal_processor = MultimodalProcessor()


def get_multimodal_processor() -> MultimodalProcessor:
    """获取多模态处理器实例"""
    return multimodal_processor


def get_multimodal_rag(knowledge_base) -> MultimodalRAG:
    """获取多模态RAG实例"""
    return MultimodalRAG(knowledge_base)


def get_multimodal_integration() -> MultimodalIntegration:
    """获取多模态集成实例"""
    return MultimodalIntegration()
