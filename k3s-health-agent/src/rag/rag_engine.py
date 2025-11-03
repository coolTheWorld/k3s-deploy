"""RAG检索引擎"""
from typing import List, Dict, Optional
import logging

from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CohereRerank
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG检索增强生成引擎"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # 初始化嵌入模型
        # 如果使用阿里云 DashScope，需要配置 base_url
        embeddings_config = {
            "api_key": config.get("openai_api_key"),
            "model": config.get("embedding_model", "text-embedding-v1"),
            "timeout": 5,  # 增加超时时间到30秒
            "max_retries": 1  # 增加重试次数
        }
        
        # 检查是否使用阿里云（通过 API key 前缀判断）
        api_key = config.get("openai_api_key", "")
        if api_key.startswith("sk-") and "dashscope" not in api_key.lower():
            # 真正的 OpenAI
            embeddings_config["model"] = "text-embedding-3-large"
        else:
            # 阿里云 DashScope - 使用正确的模型名称
            embeddings_config["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            # 阿里云支持的 embedding 模型：text-embedding-v1, text-embedding-v2
            # 注意：text-embedding-v3 可能不存在，改用 v2
            embeddings_config["model"] = "text-embedding-v3"
        
        self.embeddings = OpenAIEmbeddings(**embeddings_config)
        
        # 初始化向量数据库
        self.vector_store = QdrantVectorStore(
            client=self._init_qdrant_client(),
            collection_name="k3s_knowledge_base",
            embedding=self.embeddings
        )
        
        # 初始化重排序器（可选，提升检索质量）
        self.reranker = CohereRerank(
            cohere_api_key=config.get("cohere_api_key"),
            top_n=5
        ) if config.get("cohere_api_key") else None
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        
        logger.info("RAG Engine initialized successfully")
    
    def _init_qdrant_client(self):
        """初始化Qdrant客户端"""
        
        if self.config.get("qdrant_url"):
            # 连接到远程Qdrant服务
            return QdrantClient(
                url=self.config["qdrant_url"],
                api_key=self.config.get("qdrant_api_key")
            )
        else:
            # 使用本地内存模式（开发测试）
            logger.warning("Using in-memory Qdrant client (for development only)")
            return QdrantClient(":memory:")
    
    def add_documents(self, documents: List[Document], 
                     metadata: Optional[Dict] = None) -> List[str]:
        """添加文档到知识库"""
        try:
            # 分割文档
            chunks = self.text_splitter.split_documents(documents)
            
            # 添加元数据
            if metadata:
                for chunk in chunks:
                    chunk.metadata.update(metadata)
            
            # 添加到向量数据库
            ids = self.vector_store.add_documents(chunks)
            
            logger.info(f"Successfully added {len(chunks)} chunks to knowledge base")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def retrieve(self, query: str, k: int = 5, 
                 filter_dict: Optional[Dict] = None) -> List[Document]:
        """检索相关文档"""
        try:
            # 基础检索
            if filter_dict:
                # 带过滤条件的检索
                retriever = self.vector_store.as_retriever(
                    search_kwargs={
                        "k": k * 2 if self.reranker else k,
                        "filter": filter_dict
                    }
                )
            else:
                retriever = self.vector_store.as_retriever(
                    search_kwargs={"k": k * 2 if self.reranker else k}
                )
            
            # 如果启用重排序
            if self.reranker:
                retriever = ContextualCompressionRetriever(
                    base_compressor=self.reranker,
                    base_retriever=retriever
                )
            
            # 执行检索（使用新版 LangChain 的 invoke 方法）
            docs = retriever.invoke(query)
            
            logger.info(f"Retrieved {len(docs)} documents for query: {query[:50]}...")
            return docs
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []
    
    def retrieve_by_category(self, query: str, 
                            category: str, k: int = 5) -> List[Document]:
        """按类别检索"""
        filter_dict = {"category": category}
        return self.retrieve(query, k, filter_dict)
    
    def retrieve_similar_incidents(self, current_issue: str, 
                                   k: int = 3) -> List[Document]:
        """检索相似的历史事件"""
        filter_dict = {"doc_type": "incident"}
        return self.retrieve(current_issue, k, filter_dict)
    
    def retrieve_solutions(self, problem_description: str, 
                          k: int = 3) -> List[Document]:
        """检索解决方案"""
        filter_dict = {"doc_type": "solution"}
        return self.retrieve(problem_description, k, filter_dict)
    
    def retrieve_best_practices(self, topic: str, k: int = 3) -> List[Document]:
        """检索最佳实践"""
        filter_dict = {"doc_type": "best_practice"}
        return self.retrieve(topic, k, filter_dict)
    
    def hybrid_retrieve(self, query: str, k: int = 5) -> List[Document]:
        """混合检索：同时检索多个类别"""
        results = []
        
        # 检索历史事件
        incidents = self.retrieve_similar_incidents(query, k=2)
        results.extend(incidents)
        
        # 检索解决方案
        solutions = self.retrieve_solutions(query, k=2)
        results.extend(solutions)
        
        # 检索最佳实践
        best_practices = self.retrieve_best_practices(query, k=1)
        results.extend(best_practices)
        
        # 去重
        unique_results = self._deduplicate_documents(results)
        
        return unique_results[:k]
    
    def _deduplicate_documents(self, docs: List[Document]) -> List[Document]:
        """文档去重"""
        seen = set()
        unique_docs = []
        
        for doc in docs:
            content_hash = hash(doc.page_content)
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)
        
        return unique_docs
    
    def format_retrieved_context(self, docs: List[Document]) -> str:
        """格式化检索结果为上下文"""
        if not docs:
            return "没有找到相关的历史案例或文档。"
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            metadata = doc.metadata
            doc_type = metadata.get("doc_type", "unknown")
            source = metadata.get("source", "unknown")
            
            context_parts.append(
                f"### 参考资料 {i} ({doc_type})\n"
                f"来源: {source}\n"
                f"内容:\n{doc.page_content}\n"
            )
        
        return "\n".join(context_parts)

