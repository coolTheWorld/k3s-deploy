"""数据库模型"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text
from sqlalchemy.sql import func
from .db import Base


class HealthCheck(Base):
    """健康检查记录"""
    __tablename__ = "health_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50))
    result = Column(JSON)
    health_score = Column(Integer)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "result": self.result,
            "health_score": self.health_score
        }


class Alert(Base):
    """告警记录"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    severity = Column(String(50))
    title = Column(String(255))
    description = Column(Text)
    status = Column(String(50), default="open")  # open, in_progress, resolved
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSON)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata
        }


class Incident(Base):
    """事件记录"""
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(100), unique=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text)
    severity = Column(String(50))
    impact = Column(Text)
    root_cause = Column(Text)
    solution = Column(Text)
    resolution_time = Column(String(100))
    resolved = Column(Boolean, default=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "description": self.description,
            "severity": self.severity,
            "impact": self.impact,
            "root_cause": self.root_cause,
            "solution": self.solution,
            "resolution_time": self.resolution_time,
            "resolved": self.resolved
        }

