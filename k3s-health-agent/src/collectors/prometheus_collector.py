"""Prometheus数据收集器"""
from prometheus_api_client import PrometheusConnect
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PrometheusCollector:
    """Prometheus指标收集器"""
    
    def __init__(self, prometheus_url: str):
        """初始化收集器"""
        try:
            self.prom = PrometheusConnect(url=prometheus_url, disable_ssl=True)
            logger.info(f"Prometheus collector initialized: {prometheus_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus collector: {e}")
            raise
    
    def collect_node_metrics(self, node_name: Optional[str] = None) -> Dict:
        """收集节点资源指标"""
        try:
            # CPU使用率
            cpu_query = 'sum(rate(container_cpu_usage_seconds_total[5m])) by (node)'
            cpu_result = self.prom.custom_query(cpu_query)
            
            # 内存使用率
            memory_query = 'sum(container_memory_usage_bytes) by (node)'
            memory_result = self.prom.custom_query(memory_query)
            
            metrics = {
                "cpu": self._parse_prometheus_result(cpu_result),
                "memory": self._parse_prometheus_result(memory_result)
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect node metrics: {e}")
            return {}
    
    def collect_pod_metrics(self, namespace: str = "default") -> Dict:
        """收集Pod资源指标"""
        try:
            # Pod CPU使用
            cpu_query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}"}}[5m])) by (pod)'
            cpu_result = self.prom.custom_query(cpu_query)
            
            # Pod内存使用
            memory_query = f'sum(container_memory_usage_bytes{{namespace="{namespace}"}}) by (pod)'
            memory_result = self.prom.custom_query(memory_query)
            
            metrics = {
                "cpu": self._parse_prometheus_result(cpu_result),
                "memory": self._parse_prometheus_result(memory_result)
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect pod metrics: {e}")
            return {}
    
    def _parse_prometheus_result(self, result: List) -> Dict:
        """解析Prometheus查询结果"""
        parsed = {}
        
        for item in result:
            metric = item.get("metric", {})
            value = item.get("value", [None, None])
            
            key = metric.get("node") or metric.get("pod", "unknown")
            parsed[key] = float(value[1]) if len(value) > 1 else 0.0
        
        return parsed

