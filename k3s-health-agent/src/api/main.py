"""FastAPI主应用"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio
from datetime import datetime
import logging
from contextlib import asynccontextmanager

from ..agent.agent_core import K3sHealthAgentRAG
from ..utils.config import settings
from ..database.db import SessionLocal
from ..database.models import HealthCheck, Alert
from .routes import router as health_router
from .knowledge_routes import router as knowledge_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局Agent实例（启动时初始化）
agent: Optional[K3sHealthAgentRAG] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global agent
    
    # Startup
    logger.info("Starting K3s Health Agent...")
    
    try:
        # 初始化Agent
        agent = K3sHealthAgentRAG(
            api_key=settings.OPENAI_API_KEY,
            cluster_config=settings.K3S_CONFIG,
            rag_config=settings.RAG_CONFIG,
            enable_rag=False  # 禁用 RAG
        )
        
        # 启动后台任务
        asyncio.create_task(periodic_health_check())
        
        logger.info("K3s Health Agent started successfully")
    except Exception as e:
        logger.error(f"Failed to start agent: {e}")
        raise
    
    yield  # 应用运行期间
    
    # Shutdown
    logger.info("Shutting down K3s Health Agent...")


app = FastAPI(
    title="K3s Health Agent API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(health_router)
app.include_router(knowledge_router)


async def periodic_health_check():
    """每5分钟执行一次健康检查"""
    while True:
        try:
            if agent:
                logger.info("Running periodic health check...")
                result = await agent.analyze_cluster_health()
                
                # 输出健康检查结果
                if result.get("status") == "success":
                    logger.info("=" * 80)
                    logger.info("集群健康检查完成")
                    # logger.info("-" * 80)
                    # logger.info(f"分析结果:\n{result.get('analysis', 'N/A')}")
                    logger.info("=" * 80)
                else:
                    logger.error(f"健康检查失败: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Periodic health check failed: {e}")
        
        await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "K3s Health Agent",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "agent_ready": agent is not None,
        "timestamp": datetime.now().isoformat()
    }


def get_agent() -> K3sHealthAgentRAG:
    """获取Agent实例"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

