"""配置管理"""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # OpenAI配置
    OPENAI_API_KEY: str = None
    OPENAI_MODEL: str = "qwen-plus"
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    
    # Cohere配置（可选）
    COHERE_API_KEY: Optional[str] = None
    
    # Qdrant配置
    QDRANT_URL: str = "http://47.82.7.110:19449"
    QDRANT_API_KEY: Optional[str] = None
    
    # 知识库配置
    KNOWLEDGE_BASE_PATH: str = "./knowledge_base"
    AUTO_RECORD_INCIDENTS: bool = True
    MIN_SIMILARITY_SCORE: float = 0.7
    
    # K3s配置
    K3S_IN_CLUSTER: bool = False
    K3S_KUBECONFIG: Optional[str] = None
    K3S_PROXY_URL: Optional[str] = "http://47.82.7.110:19445"
    
    # 数据库配置
    DB_HOST: str = "47.82.7.110"
    DB_PORT: int = 30432
    DB_NAME: str = "k3s_agent"
    DB_USER: str = "postgres"
    DB_PASSWORD: str
    
    # Redis配置
    REDIS_HOST: str = "47.82.7.110"
    REDIS_PORT: int = 19448
    REDIS_PASSWORD: Optional[str] = None  # ← 添加这一行
    
    # 监控配置
    PROMETHEUS_URL: str = "http://47.82.7.110:19447"
    HEALTH_CHECK_INTERVAL: int = 300
    
    # 告警配置
    ALERT_WEBHOOK_URL: Optional[str] = None
    
    @property
    def DATABASE_URL(self) -> str:
        """数据库连接URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        """Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    @property
    def K3S_CONFIG(self) -> dict:
        """K3s配置字典"""
        return {
            "in_cluster": self.K3S_IN_CLUSTER,
            "kubeconfig": self.K3S_KUBECONFIG,
            "proxy_url": self.K3S_PROXY_URL
        }
    
    @property
    def RAG_CONFIG(self) -> dict:
        """RAG配置字典"""
        return {
            "openai_api_key": self.OPENAI_API_KEY,
            "cohere_api_key": self.COHERE_API_KEY,
            "qdrant_url": self.QDRANT_URL,
            "qdrant_api_key": self.QDRANT_API_KEY,
            "knowledge_base_path": self.KNOWLEDGE_BASE_PATH,
            "min_similarity_score": self.MIN_SIMILARITY_SCORE
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()

