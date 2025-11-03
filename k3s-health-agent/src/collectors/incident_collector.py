"""事件收集器"""
from kubernetes import client
from typing import Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class IncidentCollector:
    """K8s事件收集器（用于RAG训练）"""
    
    def __init__(self, k8s_api):
        """初始化收集器"""
        self.v1 = k8s_api
        logger.info("Incident collector initialized")
    
    def collect_recent_incidents(
        self,
        namespace: str = "default",
        hours: int = 24
    ) -> List[Dict]:
        """收集最近的异常事件"""
        try:
            events = self.v1.list_namespaced_event(namespace)
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            incidents = []
            
            for event in events.items:
                # 只收集Warning和Error事件
                if event.type not in ["Warning", "Error"]:
                    continue
                
                # 检查时间范围
                if event.last_timestamp and event.last_timestamp.replace(tzinfo=None) < cutoff_time:
                    continue
                
                incident = {
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "object": f"{event.involved_object.kind}/{event.involved_object.name}",
                    "namespace": event.involved_object.namespace,
                    "count": event.count,
                    "first_time": event.first_timestamp.isoformat() if event.first_timestamp else None,
                    "last_time": event.last_timestamp.isoformat() if event.last_timestamp else None
                }
                
                incidents.append(incident)
            
            logger.info(f"Collected {len(incidents)} incidents from last {hours} hours")
            return incidents
            
        except Exception as e:
            logger.error(f"Failed to collect incidents: {e}")
            return []
    
    def format_incident_for_knowledge_base(self, incident: Dict) -> Dict:
        """格式化事件为知识库条目"""
        return {
            "description": f"{incident['reason']}: {incident['message']}",
            "severity": "high" if incident['type'] == "Error" else "medium",
            "impact": f"Affected {incident['object']} in namespace {incident['namespace']}",
            "root_cause": incident['reason'],
            "timestamp": incident['last_time'] or incident['first_time'],
            "metadata": {
                "event_type": incident['type'],
                "count": incident['count'],
                "k8s_object": incident['object']
            }
        }

