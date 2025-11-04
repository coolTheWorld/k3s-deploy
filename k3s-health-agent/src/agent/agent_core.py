"""AI Agent核心"""
from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import SecretStr
from typing import List

from .tools import K3sTools
from .prompts import SYSTEM_PROMPT, HEALTH_CHECK_PROMPT, DIAGNOSE_PROMPT, FIX_PROMPT
from ..rag.rag_engine import RAGEngine
from ..rag.knowledge_base import KnowledgeBaseManager
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class K3sHealthAgentRAG:
    """K3s集群健康监控AI Agent（可选RAG增强）"""

    def __init__(self, api_key: str, cluster_config: dict, rag_config: dict = None, enable_rag: bool = False):
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

        # RAG 开关
        self.enable_rag = enable_rag
        self.rag_engine = None
        self.kb_manager = None

        # 仅在启用 RAG 时初始化
        if self.enable_rag and rag_config:
            try:
                logger.info("Initializing RAG engine...")
                self.rag_engine = RAGEngine(rag_config)
                
                self.kb_manager = KnowledgeBaseManager(
                    self.rag_engine,
                    rag_config.get("knowledge_base_path", "./knowledge_base")
                )
                
                self.kb_manager.initialize_knowledge_base()
                logger.info("RAG engine initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG engine (continuing without RAG): {e}")
                self.enable_rag = False
                self.rag_engine = None
                self.kb_manager = None
        else:
            logger.info("RAG engine disabled, running in basic mode")

        # 手动管理聊天历史（替代已弃用的 ConversationBufferMemory）
        self.chat_history: List = []

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
            max_iterations=20,  # 禁用迭代限制
            # max_execution_time=1200,  # 添加20分钟超时保护
            handle_parsing_errors=True
        )

    async def analyze_cluster_health(self) -> dict:
        """集群健康检查（可选RAG增强）"""
        try:
            # 条件性使用 RAG
            if self.enable_rag and self.rag_engine:
                # RAG 增强模式
                best_practices = self.rag_engine.retrieve_best_practices(
                    "kubernetes cluster health check monitoring",
                    k=3
                )
                retrieved_context = self.rag_engine.format_retrieved_context(best_practices)
                
                full_input = f"""当前时间: {datetime.now().isoformat()}

【检索到的相关知识】
{retrieved_context}

---

{HEALTH_CHECK_PROMPT}"""
                references = [doc.metadata for doc in best_practices]
            else:
                # 基础模式（无 RAG）
                full_input = f"""当前时间: {datetime.now().isoformat()}

{HEALTH_CHECK_PROMPT}"""
                references = []

            result = await self.agent.ainvoke({
                "input": full_input,
                "chat_history": self.chat_history
            })

            # 更新聊天历史
            self.chat_history.append(HumanMessage(content=full_input))
            self.chat_history.append(AIMessage(content=result["output"]))

            return {
                "status": "success",
                "analysis": result["output"],
                "timestamp": datetime.now().isoformat(),
                "references": references,
                "rag_enabled": self.enable_rag
            }
        except Exception as e:
            logger.error(f"Health analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def diagnose_issue(self, issue_description: str) -> dict:
        """问题诊断（可选RAG增强）"""
        try:
            # 条件性使用 RAG
            if self.enable_rag and self.rag_engine:
                # RAG 增强模式
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
                    "input": full_input,
                    "chat_history": self.chat_history
                })

                # 更新聊天历史
                self.chat_history.append(HumanMessage(content=full_input))
                self.chat_history.append(AIMessage(content=result["output"]))

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
                    ],
                    "rag_enabled": True
                }
            else:
                # 基础模式（无 RAG）
                full_input = f"""当前时间: {datetime.now().isoformat()}

{DIAGNOSE_PROMPT.format(issue_description=issue_description)}"""

                result = await self.agent.ainvoke({
                    "input": full_input,
                    "chat_history": self.chat_history
                })

                # 更新聊天历史
                self.chat_history.append(HumanMessage(content=full_input))
                self.chat_history.append(AIMessage(content=result["output"]))

                return {
                    "status": "success",
                    "diagnosis": result["output"],
                    "timestamp": datetime.now().isoformat(),
                    "similar_incidents": [],
                    "related_solutions": [],
                    "rag_enabled": False
                }
        except Exception as e:
            logger.error(f"Diagnosis failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def auto_fix(self, issue: dict, auto_approve: bool = False) -> dict:
        """自动修复（可选RAG增强）"""
        if not auto_approve:
            return {
                "status": "pending_approval",
                "message": "需要用户批准才能执行修复操作"
            }

        try:
            # 条件性使用 RAG
            if self.enable_rag and self.rag_engine:
                # RAG 增强模式
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
            else:
                # 基础模式（无 RAG）
                full_input = f"""当前时间: {datetime.now().isoformat()}

{FIX_PROMPT.format(issue_description=issue.get('description'))}"""

            result = await self.agent.ainvoke({
                "input": full_input,
                "chat_history": self.chat_history
            })

            # 更新聊天历史
            self.chat_history.append(HumanMessage(content=full_input))
            self.chat_history.append(AIMessage(content=result["output"]))

            # 自动记录成功的修复到知识库（仅在 RAG 启用时）
            if self.enable_rag and result.get("status") == "success":
                await self._record_successful_fix(issue, result)

            return {
                "status": "success",
                "fix_result": result["output"],
                "timestamp": datetime.now().isoformat(),
                "rag_enabled": self.enable_rag
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
        # 检查 RAG 是否启用
        if not self.enable_rag or not self.kb_manager:
            return {
                "status": "error",
                "error": "RAG engine is disabled. Enable RAG to use knowledge base search."
            }
        
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
