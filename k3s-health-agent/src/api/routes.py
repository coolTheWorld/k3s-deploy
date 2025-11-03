"""API路由"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from ..database.db import SessionLocal, get_db
from ..database.models import HealthCheck, Alert
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1", tags=["Health"])
logger = logging.getLogger(__name__)


class HealthCheckRequest(BaseModel):
    """健康检查请求"""
    full_check: bool = True
    namespaces: Optional[List[str]] = None


class DiagnoseRequest(BaseModel):
    """诊断请求"""
    issue_description: str
    context: Optional[dict] = None


class FixRequest(BaseModel):
    """修复请求"""
    issue_id: str
    auto_approve: bool = False


@router.post("/health/check")
async def check_cluster_health(
    request: HealthCheckRequest,
    db: Session = Depends(get_db)
):
    """执行集群健康检查"""
    try:
        from .main import get_agent
        agent = get_agent()
        
        result = await agent.analyze_cluster_health()
        
        # 保存到数据库
        health_check = HealthCheck(
            timestamp=datetime.now(),
            result=result,
            status=result.get("status")
        )
        db.add(health_check)
        db.commit()
        
        return result
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diagnose")
async def diagnose_issue(request: DiagnoseRequest):
    """诊断特定问题"""
    try:
        from .main import get_agent
        agent = get_agent()
        
        result = await agent.diagnose_issue(request.issue_description)
        return result
    except Exception as e:
        logger.error(f"Diagnosis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix")
async def fix_issue(
    request: FixRequest,
    db: Session = Depends(get_db)
):
    """自动修复问题"""
    try:
        from .main import get_agent
        agent = get_agent()
        
        # 从数据库获取问题详情
        issue = db.query(Alert).filter(Alert.id == request.issue_id).first()
        
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        
        result = await agent.auto_fix(
            issue=issue.to_dict(),
            auto_approve=request.auto_approve
        )
        return result
    except Exception as e:
        logger.error(f"Fix failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_health_history(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取历史健康检查记录"""
    try:
        history = db.query(HealthCheck).order_by(
            HealthCheck.timestamp.desc()
        ).limit(limit).all()
        
        return [h.to_dict() for h in history]
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取告警列表"""
    try:
        query = db.query(Alert)
        
        if status:
            query = query.filter(Alert.status == status)
        
        alerts = query.order_by(Alert.timestamp.desc()).limit(limit).all()
        
        return [alert.to_dict() for alert in alerts]
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

