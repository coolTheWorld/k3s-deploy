"""知识库管理API"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import logging
import tempfile

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Base"])
logger = logging.getLogger(__name__)


class IncidentCreate(BaseModel):
    """创建事件"""
    description: str
    severity: str
    impact: str
    root_cause: str
    solution: str
    resolution_time: Optional[str] = None


class SolutionCreate(BaseModel):
    """创建解决方案"""
    problem_type: str
    problem_pattern: str
    solution_steps: str
    prevention: str
    notes: Optional[str] = None
    success_rate: Optional[float] = None


class SearchQuery(BaseModel):
    """搜索查询"""
    query: str
    k: int = 5


@router.post("/incidents")
async def create_incident(incident: IncidentCreate):
    """创建新的事件记录"""
    try:
        from .main import get_agent
        agent = get_agent()
        
        incident_id = agent.kb_manager.add_incident(incident.dict())
        
        return {
            "status": "success",
            "incident_id": incident_id,
            "message": "事件记录已添加到知识库"
        }
    except Exception as e:
        logger.error(f"Failed to create incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/solutions")
async def create_solution(solution: SolutionCreate):
    """创建新的解决方案"""
    try:
        from .main import get_agent
        agent = get_agent()
        
        solution_id = agent.kb_manager.add_solution(solution.dict())
        
        return {
            "status": "success",
            "solution_id": solution_id,
            "message": "解决方案已添加到知识库"
        }
    except Exception as e:
        logger.error(f"Failed to create solution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_knowledge(query: SearchQuery):
    """搜索知识库"""
    try:
        from .main import get_agent
        agent = get_agent()
        
        result = agent.search_knowledge(query.query, k=query.k)
        return result
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "general"
):
    """上传文档到知识库"""
    try:
        from .main import get_agent
        from langchain.document_loaders import TextLoader
        from langchain.schema import Document
        
        agent = get_agent()
        
        # 保存上传的文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # 加载文档
        loader = TextLoader(tmp_path, encoding='utf-8')
        docs = loader.load()
        
        # 添加元数据
        for doc in docs:
            doc.metadata.update({
                "doc_type": doc_type,
                "filename": file.filename
            })
        
        # 添加到知识库
        agent.rag_engine.add_documents(docs)
        
        return {
            "status": "success",
            "message": f"文档 {file.filename} 已添加到知识库",
            "chunks": len(docs)
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_knowledge_base_stats():
    """获取知识库统计信息"""
    try:
        from .main import get_agent
        agent = get_agent()
        
        kb_path = agent.kb_manager.kb_path
        
        stats = {
            "incidents_count": len(list(agent.kb_manager.incidents_path.glob("*.json"))),
            "solutions_count": len(list(agent.kb_manager.solutions_path.glob("*.json"))),
            "best_practices_count": len(list(agent.kb_manager.best_practices_path.glob("*.md"))),
            "k8s_docs_count": len(list(agent.kb_manager.k8s_docs_path.glob("*.md")))
        }
        
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

