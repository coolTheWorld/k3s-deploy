"""知识库管理"""
from pathlib import Path
from typing import List, Dict, Optional
from langchain.document_loaders import (
    TextLoader,
    UnstructuredMarkdownLoader,
    DirectoryLoader
)
from langchain.schema import Document
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """知识库管理器"""
    
    def __init__(self, rag_engine, knowledge_base_path: str):
        self.rag_engine = rag_engine
        self.kb_path = Path(knowledge_base_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)
        
        # 知识库目录结构
        self.incidents_path = self.kb_path / "incidents"
        self.solutions_path = self.kb_path / "solutions"
        self.best_practices_path = self.kb_path / "best_practices"
        self.k8s_docs_path = self.kb_path / "k8s_docs"
        
        # 创建子目录
        for path in [self.incidents_path, self.solutions_path, 
                    self.best_practices_path, self.k8s_docs_path]:
            path.mkdir(exist_ok=True)
        
        logger.info(f"Knowledge base initialized at {knowledge_base_path}")
    
    def initialize_knowledge_base(self):
        """初始化知识库：加载所有文档"""
        logger.info("Initializing knowledge base...")
        
        # 加载K8s官方文档
        self._load_k8s_docs()
        
        # 加载最佳实践
        self._load_best_practices()
        
        # 加载历史事件
        self._load_incidents()
        
        # 加载解决方案
        self._load_solutions()
        
        logger.info("Knowledge base initialized successfully")
    
    def _load_k8s_docs(self):
        """加载K8s文档"""
        logger.info("Loading K8s documentation...")
        
        if not list(self.k8s_docs_path.glob("*.md")):
            logger.warning("No K8s docs found, creating sample docs...")
            self._create_sample_k8s_docs()
        
        # 加载Markdown文档
        try:
            loader = DirectoryLoader(
                str(self.k8s_docs_path),
                glob="**/*.md",
                loader_cls=UnstructuredMarkdownLoader
            )
            
            docs = loader.load()
            
            # 添加元数据
            for doc in docs:
                doc.metadata.update({
                    "doc_type": "k8s_doc",
                    "category": "kubernetes",
                    "source": doc.metadata.get("source", "unknown")
                })
            
            if docs:
                self.rag_engine.add_documents(docs)
                logger.info(f"Loaded {len(docs)} K8s documents")
        except Exception as e:
            logger.error(f"Failed to load K8s docs: {e}")
    
    def _create_sample_k8s_docs(self):
        """创建示例K8s文档"""
        sample_docs = [
            {
                "filename": "pod_lifecycle.md",
                "content": """# Pod生命周期

## Pod相位（Phase）
- Pending：Pod已被K8s接受，但容器镜像未创建
- Running：Pod已绑定到节点，所有容器已创建
- Succeeded：所有容器成功终止
- Failed：至少一个容器失败终止
- Unknown：无法获取Pod状态

## 常见问题
### CrashLoopBackOff
原因：容器启动后立即崩溃
排查：检查容器日志、资源限制、配置错误

### ImagePullBackOff
原因：无法拉取镜像
排查：检查镜像名称、镜像仓库认证、网络连接
"""
            },
            {
                "filename": "resource_management.md",
                "content": """# 资源管理

## CPU和内存限制
- requests：容器请求的最小资源
- limits：容器可使用的最大资源

## 常见问题
### OOMKilled
原因：容器内存使用超过limits
解决：增加memory limits或优化应用内存使用

### CPU节流
原因：CPU使用超过limits
解决：增加CPU limits或优化应用CPU使用
"""
            }
        ]
        
        for doc_info in sample_docs:
            file_path = self.k8s_docs_path / doc_info["filename"]
            file_path.write_text(doc_info["content"], encoding="utf-8")
        
        logger.info("Created sample K8s documentation")
    
    def _load_best_practices(self):
        """加载最佳实践"""
        logger.info("Loading best practices...")
        
        try:
            loader = DirectoryLoader(
                str(self.best_practices_path),
                glob="**/*.md",
                loader_cls=UnstructuredMarkdownLoader
            )
            
            docs = loader.load()
            
            for doc in docs:
                doc.metadata.update({
                    "doc_type": "best_practice",
                    "category": "best_practice"
                })
            
            if docs:
                self.rag_engine.add_documents(docs)
                logger.info(f"Loaded {len(docs)} best practice documents")
        except Exception as e:
            logger.error(f"Failed to load best practices: {e}")
    
    def _load_incidents(self):
        """加载历史事件"""
        logger.info("Loading historical incidents...")
        
        incident_files = list(self.incidents_path.glob("*.json"))
        
        documents = []
        for file_path in incident_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    incident = json.load(f)
                
                # 将事件转换为Document
                content = self._format_incident(incident)
                doc = Document(
                    page_content=content,
                    metadata={
                        "doc_type": "incident",
                        "incident_id": incident.get("id"),
                        "severity": incident.get("severity"),
                        "resolved": incident.get("resolved", False),
                        "timestamp": incident.get("timestamp"),
                        "source": str(file_path)
                    }
                )
                documents.append(doc)
                
            except Exception as e:
                logger.error(f"Failed to load incident {file_path}: {e}")
        
        if documents:
            self.rag_engine.add_documents(documents)
            logger.info(f"Loaded {len(documents)} incident records")
    
    def _load_solutions(self):
        """加载解决方案"""
        logger.info("Loading solutions...")
        
        solution_files = list(self.solutions_path.glob("*.json"))
        
        documents = []
        for file_path in solution_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    solution = json.load(f)
                
                content = self._format_solution(solution)
                doc = Document(
                    page_content=content,
                    metadata={
                        "doc_type": "solution",
                        "solution_id": solution.get("id"),
                        "problem_type": solution.get("problem_type"),
                        "success_rate": solution.get("success_rate", 0),
                        "source": str(file_path)
                    }
                )
                documents.append(doc)
                
            except Exception as e:
                logger.error(f"Failed to load solution {file_path}: {e}")
        
        if documents:
            self.rag_engine.add_documents(documents)
            logger.info(f"Loaded {len(documents)} solution records")
    
    def _format_incident(self, incident: dict) -> str:
        """格式化事件为文本"""
        return f"""
【历史事件记录】
事件ID: {incident.get('id')}
发生时间: {incident.get('timestamp')}
严重程度: {incident.get('severity')}

问题描述:
{incident.get('description')}

影响范围:
{incident.get('impact')}

根因分析:
{incident.get('root_cause')}

解决方案:
{incident.get('solution')}

解决时间: {incident.get('resolution_time')}
        """.strip()
    
    def _format_solution(self, solution: dict) -> str:
        """格式化解决方案为文本"""
        return f"""
【解决方案】
方案ID: {solution.get('id')}
问题类型: {solution.get('problem_type')}
成功率: {solution.get('success_rate', 'N/A')}

问题特征:
{solution.get('problem_pattern')}

解决步骤:
{solution.get('solution_steps')}

预防措施:
{solution.get('prevention')}

注意事项:
{solution.get('notes')}
        """.strip()
    
    def add_incident(self, incident: dict):
        """添加新的事件记录"""
        try:
            incident_id = incident.get("id") or self._generate_id("INC")
            incident["id"] = incident_id
            incident["timestamp"] = incident.get("timestamp") or datetime.now().isoformat()
            
            # 保存到文件
            file_path = self.incidents_path / f"{incident_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(incident, f, ensure_ascii=False, indent=2)
            
            # 添加到向量数据库
            content = self._format_incident(incident)
            doc = Document(
                page_content=content,
                metadata={
                    "doc_type": "incident",
                    "incident_id": incident_id,
                    "severity": incident.get("severity"),
                    "timestamp": incident["timestamp"]
                }
            )
            
            self.rag_engine.add_documents([doc])
            logger.info(f"Added incident: {incident_id}")
            
            return incident_id
            
        except Exception as e:
            logger.error(f"Failed to add incident: {e}")
            raise
    
    def add_solution(self, solution: dict):
        """添加新的解决方案"""
        try:
            solution_id = solution.get("id") or self._generate_id("SOL")
            solution["id"] = solution_id
            
            # 保存到文件
            file_path = self.solutions_path / f"{solution_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(solution, f, ensure_ascii=False, indent=2)
            
            # 添加到向量数据库
            content = self._format_solution(solution)
            doc = Document(
                page_content=content,
                metadata={
                    "doc_type": "solution",
                    "solution_id": solution_id,
                    "problem_type": solution.get("problem_type")
                }
            )
            
            self.rag_engine.add_documents([doc])
            logger.info(f"Added solution: {solution_id}")
            
            return solution_id
            
        except Exception as e:
            logger.error(f"Failed to add solution: {e}")
            raise
    
    def _generate_id(self, prefix: str) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}-{timestamp}"
    
    def search_knowledge_base(self, query: str, k: int = 5) -> List[Document]:
        """搜索知识库"""
        return self.rag_engine.hybrid_retrieve(query, k=k)

