"""通知模块"""
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
    
    def send_alert(self, 
                   title: str, 
                   message: str, 
                   severity: str = "warning",
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """发送告警通知"""
        if not self.webhook_url:
            logger.warning("Webhook URL not configured, skipping notification")
            return False
        
        try:
            payload = {
                "title": title,
                "message": message,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Alert sent successfully: {title}")
                return True
            else:
                logger.error(f"Failed to send alert: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    def send_health_report(self, report: Dict[str, Any]) -> bool:
        """发送健康检查报告"""
        return self.send_alert(
            title="K3s集群健康检查报告",
            message=f"健康评分: {report.get('health_score', 'N/A')}",
            severity="info",
            metadata=report
        )

