"""日志收集器"""
from kubernetes import client
from typing import Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


class LogCollector:
    """Pod日志收集器"""
    
    def __init__(self, k8s_api):
        """初始化收集器"""
        self.v1 = k8s_api
        logger.info("Log collector initialized")
    
    def collect_pod_logs(
        self, 
        pod_name: str, 
        namespace: str = "default",
        tail_lines: int = 100
    ) -> str:
        """收集Pod日志"""
        try:
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail_lines
            )
            return logs
        except Exception as e:
            logger.error(f"Failed to collect logs for {pod_name}: {e}")
            return ""
    
    def analyze_logs_for_errors(
        self, 
        logs: str
    ) -> Dict[str, List[str]]:
        """分析日志中的错误"""
        errors = {
            "critical": [],
            "error": [],
            "warning": []
        }
        
        if not logs:
            return errors
        
        # 错误模式匹配
        error_patterns = {
            "critical": [
                r"CRITICAL",
                r"FATAL",
                r"panic:",
                r"core dumped"
            ],
            "error": [
                r"ERROR",
                r"Exception",
                r"failed to",
                r"cannot connect"
            ],
            "warning": [
                r"WARNING",
                r"WARN",
                r"deprecated"
            ]
        }
        
        for line in logs.split('\n'):
            for level, patterns in error_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        errors[level].append(line.strip())
                        break
        
        return errors

