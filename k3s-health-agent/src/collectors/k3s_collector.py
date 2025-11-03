"""K3s数据收集器"""
from kubernetes import client, config
from kubernetes.client import Configuration
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class K3sCollector:
    """K3s集群数据收集器"""

    def __init__(self, cluster_config: dict):
        """初始化收集器"""
        try:
            # 检查是否使用 kubectl proxy
            if cluster_config.get("proxy_url"):
                # 使用 kubectl proxy 连接
                configuration = Configuration()
                configuration.host = cluster_config.get("proxy_url")
                # kubectl proxy 不需要认证
                configuration.verify_ssl = False

                # 创建 API 客户端
                api_client = client.ApiClient(configuration)
                self.v1 = client.CoreV1Api(api_client)
                self.apps_v1 = client.AppsV1Api(api_client)

                logger.info(f"K3s collector initialized with proxy: {configuration.host}")

            elif cluster_config.get("in_cluster"):
                # from kubernetes import config
                config.load_incluster_config()
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                logger.info("K3s collector initialized (in-cluster)")

            else:
                # from kubernetes import config
                kubeconfig = cluster_config.get("kubeconfig")
                if kubeconfig:
                    config.load_kube_config(config_file=kubeconfig)
                else:
                    config.load_kube_config()

                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                logger.info("K3s collector initialized (kubeconfig)")

        except Exception as e:
            logger.error(f"Failed to initialize K3s collector: {e}")
            raise
    
    def collect_cluster_metrics(self) -> Dict:
        """收集集群整体指标"""
        try:
            metrics = {
                "nodes": self._collect_node_metrics(),
                "pods": self._collect_pod_metrics(),
                "services": self._collect_service_metrics(),
                "deployments": self._collect_deployment_metrics()
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect cluster metrics: {e}")
            return {}
    
    def _collect_node_metrics(self) -> Dict:
        """收集节点指标"""
        try:
            nodes = self.v1.list_node()
            
            total = len(nodes.items)
            ready = sum(1 for node in nodes.items 
                       if any(c.type == "Ready" and c.status == "True" 
                             for c in node.status.conditions))
            
            return {
                "total": total,
                "ready": ready,
                "not_ready": total - ready
            }
        except Exception as e:
            logger.error(f"Failed to collect node metrics: {e}")
            return {}
    
    def _collect_pod_metrics(self) -> Dict:
        """收集Pod指标"""
        try:
            pods = self.v1.list_pod_for_all_namespaces()
            
            status_count = {}
            for pod in pods.items:
                phase = pod.status.phase
                status_count[phase] = status_count.get(phase, 0) + 1
            
            return {
                "total": len(pods.items),
                "by_status": status_count
            }
        except Exception as e:
            logger.error(f"Failed to collect pod metrics: {e}")
            return {}
    
    def _collect_service_metrics(self) -> Dict:
        """收集Service指标"""
        try:
            services = self.v1.list_service_for_all_namespaces()
            
            type_count = {}
            for svc in services.items:
                svc_type = svc.spec.type
                type_count[svc_type] = type_count.get(svc_type, 0) + 1
            
            return {
                "total": len(services.items),
                "by_type": type_count
            }
        except Exception as e:
            logger.error(f"Failed to collect service metrics: {e}")
            return {}
    
    def _collect_deployment_metrics(self) -> Dict:
        """收集Deployment指标"""
        try:
            deployments = self.apps_v1.list_deployment_for_all_namespaces()
            
            total = len(deployments.items)
            healthy = sum(1 for d in deployments.items
                         if d.status.ready_replicas == d.spec.replicas)
            
            return {
                "total": total,
                "healthy": healthy,
                "unhealthy": total - healthy
            }
        except Exception as e:
            logger.error(f"Failed to collect deployment metrics: {e}")
            return {}

