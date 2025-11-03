"""AI Agent核心"""
from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import SecretStr

from .tools import K3sTools
from .prompts import SYSTEM_PROMPT, HEALTH_CHECK_PROMPT, DIAGNOSE_PROMPT, FIX_PROMPT
from ..rag.rag_engine import RAGEngine
from ..rag.knowledge_base import KnowledgeBaseManager
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class K3sHealthAgentRAG:
    """RAG增强的K3s集群健康监控AI Agent"""

    def __init__(self, api_key: str, cluster_config: dict, rag_config: dict):
        logger.info("Initializing K3s Health Agent...")

        # self.llm = ChatOpenAI(
        #     model="gpt-4-turbo-preview",
        #     temperature=0,
        #     api_key=api_key
        # )
        self.llm = ChatOpenAI(
            api_key=SecretStr(api_key),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",  # Base URL
            temperature=0
        )

        # 初始化K3s工具集
        self.k3s_tools = K3sTools(cluster_config)

        # 初始化RAG引擎
        self.rag_engine = RAGEngine(rag_config)

        # 初始化知识库管理器
        self.kb_manager = KnowledgeBaseManager(
            self.rag_engine,
            rag_config.get("knowledge_base_path", "./knowledge_base")
        )

        # 初始化知识库
        try:
            self.kb_manager.initialize_knowledge_base()
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")

        # 记忆管理（必须在创建Agent之前初始化）
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # 创建Agent
        self.agent = self._create_agent()

        logger.info("K3s Health Agent initialized successfully")

    def _create_agent(self):
        """创建RAG增强的Agent"""

        # RAG增强的Prompt模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 获取工具列表
        tools = self.k3s_tools.get_tools()

        # 创建Agent
        agent = create_openai_tools_agent(self.llm, tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=15,  # 增加迭代次数以支持RAG
            memory=self.memory,
            handle_parsing_errors=True
        )

    async def analyze_cluster_health(self) -> dict:
        """RAG增强的集群健康检查"""
        try:
            # 检索相关的最佳实践
            best_practices = self.rag_engine.retrieve_best_practices(
                "kubernetes cluster health check monitoring",
                k=3
            )

            retrieved_context = self.rag_engine.format_retrieved_context(
                best_practices
            )

            # 构建包含上下文信息的完整输入
            full_input = f"""当前时间: {datetime.now().isoformat()}

【检索到的相关知识】
{retrieved_context}

---

{HEALTH_CHECK_PROMPT}"""

            result = await self.agent.ainvoke({
                "input": full_input
            })

            return {
                "status": "success",
                "analysis": result["output"],
                "timestamp": datetime.now().isoformat(),
                "references": [doc.metadata for doc in best_practices]
            }
        except Exception as e:
            logger.error(f"Health analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def diagnose_issue(self, issue_description: str) -> dict:
        """RAG增强的问题诊断"""
        try:
            # 检索相似的历史事件
            similar_incidents = self.rag_engine.retrieve_similar_incidents(
                issue_description,
                k=3
            )

            # 检索相关解决方案
            solutions = self.rag_engine.retrieve_solutions(
                issue_description,
                k=3
            )

            # 检索K8s文档
            k8s_docs = self.rag_engine.retrieve(
                issue_description,
                k=2,
                filter_dict={"doc_type": "k8s_doc"}
            )

            # 组合检索结果
            all_docs = similar_incidents + solutions + k8s_docs
            retrieved_context = self.rag_engine.format_retrieved_context(all_docs)

            # 构建包含上下文信息的完整输入
            full_input = f"""当前时间: {datetime.now().isoformat()}

【检索到的相关知识】
{retrieved_context}

---

{DIAGNOSE_PROMPT.format(issue_description=issue_description)}"""

            result = await self.agent.ainvoke({
                "input": full_input
            })

            return {
                "status": "success",
                "diagnosis": result["output"],
                "timestamp": datetime.now().isoformat(),
                "similar_incidents": [
                    {
                        "id": doc.metadata.get("incident_id"),
                        "snippet": doc.page_content[:200] + "..."
                    }
                    for doc in similar_incidents
                ],
                "related_solutions": [
                    {
                        "id": doc.metadata.get("solution_id"),
                        "problem_type": doc.metadata.get("problem_type"),
                        "success_rate": doc.metadata.get("success_rate")
                    }
                    for doc in solutions
                ]
            }
        except Exception as e:
            logger.error(f"Diagnosis failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def auto_fix(self, issue: dict, auto_approve: bool = False) -> dict:
        """RAG增强的自动修复"""
        if not auto_approve:
            return {
                "status": "pending_approval",
                "message": "需要用户批准才能执行修复操作"
            }

        try:
            # 检索成功的解决方案
            solutions = self.rag_engine.retrieve_solutions(
                issue.get('description'),
                k=3
            )

            retrieved_context = self.rag_engine.format_retrieved_context(solutions)

            # 构建包含上下文信息的完整输入
            full_input = f"""当前时间: {datetime.now().isoformat()}

【检索到的相关知识】
{retrieved_context}

---

{FIX_PROMPT.format(issue_description=issue.get('description'))}"""

            result = await self.agent.ainvoke({
                "input": full_input
            })

            # 自动记录成功的修复到知识库
            if result.get("status") == "success":
                await self._record_successful_fix(issue, result)

            return {
                "status": "success",
                "fix_result": result["output"],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Auto fix failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _record_successful_fix(self, issue: dict, fix_result: dict):
        """记录成功的修复到知识库"""
        try:
            incident = {
                "description": issue.get("description"),
                "severity": issue.get("severity", "medium"),
                "impact": issue.get("impact", "Unknown"),
                "root_cause": fix_result.get("root_cause", "Analyzing..."),
                "solution": fix_result.get("solution_steps", ""),
                "resolution_time": fix_result.get("resolution_time", "Unknown"),
                "resolved": True
            }

            self.kb_manager.add_incident(incident)
            logger.info(f"Recorded successful fix to knowledge base")

        except Exception as e:
            logger.error(f"Failed to record fix: {e}")

    def search_knowledge(self, query: str, k: int = 5) -> dict:
        """搜索知识库"""
        try:
            docs = self.kb_manager.search_knowledge_base(query, k=k)

            return {
                "status": "success",
                "results": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in docs
                ],
                "count": len(docs)
            }
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
