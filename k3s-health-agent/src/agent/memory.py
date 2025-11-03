"""记忆管理模块"""
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_openai import ChatOpenAI
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AgentMemory:
    """Agent记忆管理器"""
    
    def __init__(self, api_key: str, memory_type: str = "buffer"):
        """
        初始化记忆管理器
        
        Args:
            api_key: OpenAI API密钥
            memory_type: 记忆类型 ("buffer" 或 "summary")
        """
        self.memory_type = memory_type
        
        if memory_type == "summary":
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0,
                api_key=api_key
            )
            self.memory = ConversationSummaryMemory(
                llm=llm,
                memory_key="chat_history",
                return_messages=True
            )
        else:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                max_token_limit=2000
            )
    
    def add_message(self, role: str, content: str):
        """添加消息到记忆"""
        try:
            if role == "user":
                self.memory.chat_memory.add_user_message(content)
            elif role == "assistant":
                self.memory.chat_memory.add_ai_message(content)
        except Exception as e:
            logger.error(f"Failed to add message to memory: {e}")
    
    def get_memory_variables(self) -> dict:
        """获取记忆变量"""
        return self.memory.load_memory_variables({})
    
    def clear(self):
        """清空记忆"""
        self.memory.clear()
        logger.info("Memory cleared")

