"""AI Agent核心 - 使用 LangGraph API 支持 AI Agents Debugger 可视化"""
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
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

        # 手动管理聊天历史
        self.chat_history: List = []

        # 创建Agent
        self.agent = self._create_agent()

        logger.info("K3s Health Agent initialized successfully")

    def _create_agent(self):
        """创建 LangGraph Agent（支持 AI Agents Debugger 可视化）"""

        # 获取工具列表
        tools = self.k3s_tools.get_tools()

        # LangGraph create_agent API
        agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            # LangGraph 内部自动管理状态和消息历史
        )

        logger.info(f"Created LangGraph agent with {len(tools)} tools (supports AI Agents Debugger visualization)")
        return agent
    
    def _log_tool_calls(self, output_messages, history_length):
        """打印工具调用过程的辅助方法"""
        logger.info(" 工具调用过程:")
        tool_call_count = 0
        
        # 跳过历史消息和输入消息，只看新的消息
        for msg in output_messages[history_length + 1:]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_call_count += 1
                    logger.info(f"  [{tool_call_count}] 调用工具: {tool_call.get('name', 'unknown')}")
                    logger.info(f"      参数: {tool_call.get('args', {})}")
            elif hasattr(msg, 'content') and msg.content and not isinstance(msg, HumanMessage):
                # 工具返回的结果或 AI 的思考
                if hasattr(msg, 'name'):  # 工具返回消息
                    content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    logger.info(f"  ↳ 工具返回: {content_preview}")
        
        logger.info(f" 总工具调用次数: {tool_call_count}")
        logger.info("-" * 80)

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


            # 将历史消息和新消息组合成完整的消息列表
            messages = self.chat_history + [HumanMessage(content=full_input)]
            
            # 打印输入
            logger.info("=" * 80)
            logger.info(" LLM 调用 - 健康检查")
            logger.info("=" * 80)
            logger.info(" 系统提示 (SYSTEM_PROMPT):")
            logger.info(f"{SYSTEM_PROMPT}")
            logger.info("-" * 80)
            logger.info(f" 用户输入 (HEALTH_CHECK_PROMPT):\n{full_input}")
            logger.info("-" * 80)
            
            result = await self.agent.ainvoke(
                {"messages": messages},
                config={"recursion_limit": 50}  # 增加递归限制，防止过早停止
            )

            # 提取 LangGraph 返回的所有消息
            output_messages = result.get("messages", [])
            
            # 打印工具调用过程
            self._log_tool_calls(output_messages, len(self.chat_history))
            
            # 提取最终输出
            output = output_messages[-1].content if output_messages else ""
            
            # 打印最终输出
            logger.info(f" 最终输出:\n{output}")
            logger.info("=" * 80)

            # 更新聊天历史
            self.chat_history.append(HumanMessage(content=full_input))
            self.chat_history.append(AIMessage(content=output))

            return {
                "status": "success",
                "analysis": output,
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

                # LangGraph Agent 使用 messages 格式调用
                messages = self.chat_history + [HumanMessage(content=full_input)]
                
                # 打印输入
                logger.info("=" * 80)
                logger.info(" LLM 调用 - 问题诊断 (RAG模式)")
                logger.info("=" * 80)
                logger.info(" 系统提示 (SYSTEM_PROMPT):")
                logger.info(f"{SYSTEM_PROMPT}")
                logger.info("-" * 80)
                logger.info(f" 用户输入 (含RAG上下文):\n{full_input}")
                logger.info("-" * 80)
                
                result = await self.agent.ainvoke(
                    {"messages": messages},
                    config={"recursion_limit": 50}  # 增加递归限制
                )

                # 提取输出
                output_messages = result.get("messages", [])
                
                # 打印工具调用过程
                self._log_tool_calls(output_messages, len(self.chat_history))
                
                output = output_messages[-1].content if output_messages else ""
                
                # 打印最终输出
                logger.info(f" 最终输出:\n{output}")
                logger.info("=" * 80)

                # 更新聊天历史
                self.chat_history.append(HumanMessage(content=full_input))
                self.chat_history.append(AIMessage(content=output))

                return {
                    "status": "success",
                    "diagnosis": output,
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

                # LangGraph Agent 使用 messages 格式调用
                messages = self.chat_history + [HumanMessage(content=full_input)]
                
                # 打印输入
                logger.info("=" * 80)
                logger.info(" LLM 调用 - 问题诊断 (基础模式)")
                logger.info("=" * 80)
                logger.info(" 系统提示 (SYSTEM_PROMPT):")
                logger.info(f"{SYSTEM_PROMPT}")
                logger.info("-" * 80)
                logger.info(f" 用户输入:\n{full_input}")
                logger.info("-" * 80)
                
                result = await self.agent.ainvoke(
                    {"messages": messages},
                    config={"recursion_limit": 50}  # 增加递归限制
                )

                # 提取输出
                output_messages = result.get("messages", [])
                
                # 打印工具调用过程
                self._log_tool_calls(output_messages, len(self.chat_history))
                
                output = output_messages[-1].content if output_messages else ""
                
                # 打印最终输出
                logger.info(f" 最终输出:\n{output}")
                logger.info("=" * 80)

                # 更新聊天历史
                self.chat_history.append(HumanMessage(content=full_input))
                self.chat_history.append(AIMessage(content=output))

                return {
                    "status": "success",
                    "diagnosis": output,
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

            #LangGraph Agent 使用 messages 格式调用
            messages = self.chat_history + [HumanMessage(content=full_input)]
            
            # 打印输入
            logger.info("=" * 80)
            logger.info(f" LLM 调用 - 自动修复 ({'RAG模式' if self.enable_rag else '基础模式'})")
            logger.info("=" * 80)
            logger.info(" 系统提示 (SYSTEM_PROMPT):")
            logger.info(f"{SYSTEM_PROMPT}")
            logger.info("-" * 80)
            logger.info(f" 用户输入:\n{full_input}")
            logger.info("-" * 80)
            
            result = await self.agent.ainvoke(
                {"messages": messages},
                config={"recursion_limit": 50}  # 增加递归限制
            )

            # 提取输出
            output_messages = result.get("messages", [])
            
            # 打印工具调用过程
            self._log_tool_calls(output_messages, len(self.chat_history))
            
            output = output_messages[-1].content if output_messages else ""
            
            # 打印最终输出
            logger.info(f" 最终输出:\n{output}")
            logger.info("=" * 80)

            # 更新聊天历史
            self.chat_history.append(HumanMessage(content=full_input))
            self.chat_history.append(AIMessage(content=output))

            # 自动记录成功的修复到知识库（仅在 RAG 启用时）
            if self.enable_rag and result.get("status") == "success":
                await self._record_successful_fix(issue, result)

            return {
                "status": "success",
                "fix_result": output,
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
