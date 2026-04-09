"""知识库管理API"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.api.schemas import BaseResponse, KnowledgeDoc
from app.rag.knowledge_base import get_knowledge_base, initialize_knowledge_base
from typing import Optional, List
import tempfile
import os
import io

router = APIRouter()


@router.get("/knowledge/stats")
async def get_stats():
    """获取知识库统计"""
    try:
        kb = get_knowledge_base()
        stats = kb.get_collection_stats()
        return BaseResponse(data=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/categories")
async def get_categories():
    """获取所有分类"""
    try:
        kb = get_knowledge_base()
        categories = kb.get_all_categories()
        return BaseResponse(data={"categories": categories})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/search")
async def search_knowledge(query: str, top_k: int = 3, category: Optional[str] = None):
    """搜索知识库"""
    try:
        kb = get_knowledge_base()
        results = kb.search(query, top_k, category)
        return BaseResponse(data={"results": results, "count": len(results)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/document")
async def add_document(doc: KnowledgeDoc):
    """添加文档"""
    try:
        kb = get_knowledge_base()
        result = kb.add_text(doc.content, {
            "title": doc.title,
            "category": doc.category,
            "tags": ",".join(doc.tags) if doc.tags else ""
        })
        if result.get("success"):
            return BaseResponse(data=result, message="文档添加成功")
        return BaseResponse(success=False, message=result.get("error", "添加失败"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/upload")
async def upload_file(file: UploadFile = File(...), category: str = "general"):
    """上传文件到知识库"""
    try:
        kb = get_knowledge_base()

        content = await file.read()
        ext = os.path.splitext(file.filename)[1].lower()
        text = ""

        if ext == '.pdf':
            import fitz
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            try:
                text = kb._extract_pdf(temp_file_path)
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        elif ext in ['.docx', '.doc']:
            from docx import Document as DocxDocument
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            try:
                text = kb._extract_docx(temp_file_path)
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        elif ext == '.xlsx':
            import openpyxl
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            try:
                text = kb._extract_xlsx(temp_file_path)
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        elif ext == '.csv':
            text = content.decode('utf-8')
            import csv
            import io
            reader = csv.reader(io.StringIO(text))
            lines = [" | ".join(row) for row in reader]
            text = "\n".join(lines)
        elif ext == '.json':
            import json
            data = json.loads(content.decode('utf-8'))
            text = json.dumps(data, ensure_ascii=False, indent=2)
        elif ext == '.html':
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content.decode('utf-8'), 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
        else:
            text = content.decode('utf-8')

        from langchain_core.documents import Document
        doc = Document(
            page_content=text,
            metadata={
                "source": file.filename,
                "category": category,
                "file_type": ext
            }
        )

        docs = kb.splitter.split_documents([doc])
        if not docs:
            return BaseResponse(success=False, message="文档内容为空或解析失败")

        result = kb.add_documents(docs, category)

        return BaseResponse(
            data={"count": len(docs), "result": result},
            message=f"成功上传{len(docs)}个文档片段"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/init")
async def init_knowledge():
    """初始化知识库（从文件目录加载）"""
    try:
        result = initialize_knowledge_base()
        return BaseResponse(data=result, message="知识库初始化完成")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/documents")
async def get_documents(limit: int = 100):
    """获取所有文档"""
    try:
        kb = get_knowledge_base()
        docs = kb.get_all_documents(limit)
        return BaseResponse(data={"documents": docs, "count": len(docs)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/category/{category}")
async def delete_category(category: str):
    """删除指定分类"""
    try:
        kb = get_knowledge_base()
        result = kb.delete_by_category(category)
        if result.get("success"):
            return BaseResponse(data=result, message=f"分类'{category}'已删除")
        return BaseResponse(success=False, message=result.get("error", "删除失败"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/reset")
async def reset_knowledge():
    """重置知识库"""
    try:
        kb = get_knowledge_base()
        kb.reset()
        return BaseResponse(message="知识库已重置")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))