"""K3s工具集"""
from kubernetes import client, config
from kubernetes.client import Configuration
from typing import Optional, List
import subprocess
import json
import logging

from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Pydantic schemas for structured tools
class PodStatusInput(BaseModel):
    namespace: str = Field(default="default", description="Kubernetes namespace")

class PodLogsInput(BaseModel):
    pod_name: str = Field(description="Pod name")
    namespace: str = Field(default="default", description="Kubernetes namespace")
    container: Optional[str] = Field(default=None, description="Container name (required for multi-container pods)")
    tail_lines: int = Field(default=100, description="Number of log lines to retrieve")

class EventsInput(BaseModel):
    namespace: str = Field(default="default", description="Kubernetes namespace")
    limit: int = Field(default=50, description="Maximum number of events to retrieve")

class RestartPodInput(BaseModel):
    pod_name: str = Field(description="Pod name to restart")
    namespace: str = Field(default="default", description="Kubernetes namespace")

class ScaleDeploymentInput(BaseModel):
    deployment_name: str = Field(description="Deployment name")
    replicas: int = Field(description="Target number of replicas")
    namespace: str = Field(default="default", description="Kubernetes namespace")

class ServiceStatusInput(BaseModel):
    namespace: str = Field(default="default", description="Kubernetes namespace")

class KubectlCommandInput(BaseModel):
    command: str = Field(description="kubectl command to execute (query commands only)")


class K3sTools:
    """K3s集群操作工具集"""
    
    def __init__(self, cluster_config: dict):
        """初始化K3s工具集"""
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
                self.metrics_api = client.CustomObjectsApi(api_client)
                
                logger.info(f"K3s tools initialized with proxy: {configuration.host}")
                
            elif cluster_config.get("in_cluster"):
                # 集群内运行
                config.load_incluster_config()
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                self.metrics_api = client.CustomObjectsApi()
                logger.info("K3s tools initialized (in-cluster)")
                
            else:
                # 使用 kubeconfig 文件
                kubeconfig = cluster_config.get("kubeconfig")
                if kubeconfig:
                    config.load_kube_config(config_file=kubeconfig)
                else:
                    config.load_kube_config()
                
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                self.metrics_api = client.CustomObjectsApi()
                logger.info("K3s tools initialized (kubeconfig)")
            
        except Exception as e:
            logger.error(f"Failed to initialize K3s tools: {e}")
            raise
    
    def get_tools(self):
        """返回所有工具"""
        return [
            Tool(
                name="get_cluster_nodes",
                func=self.get_cluster_nodes,
                description="获取集群所有节点状态，包括节点名称、状态、角色、版本、资源容量等信息"
            ),
            StructuredTool(
                name="get_pod_status",
                func=self.get_pod_status,
                description="获取指定命名空间的所有Pod状态，包括运行状态、重启次数、资源使用等",
                args_schema=PodStatusInput
            ),
            StructuredTool(
                name="get_pod_logs",
                func=self.get_pod_logs,
                description="获取指定Pod的日志，用于问题诊断和错误分析",
                args_schema=PodLogsInput
            ),
            Tool(
                name="get_node_metrics",
                func=self.get_node_metrics,
                description="获取节点的实时资源使用指标（CPU、内存使用率）"
            ),
            StructuredTool(
                name="get_events",
                func=self.get_events,
                description="获取集群事件，包括Warning和Error级别的事件，用于问题追踪",
                args_schema=EventsInput
            ),
            StructuredTool(
                name="restart_pod",
                func=self.restart_pod,
                description="重启指定的Pod（通过删除Pod让Deployment重建）",
                args_schema=RestartPodInput
            ),
            StructuredTool(
                name="scale_deployment",
                func=self.scale_deployment,
                description="调整Deployment的副本数量，用于扩缩容",
                args_schema=ScaleDeploymentInput
            ),
            StructuredTool(
                name="get_service_status",
                func=self.get_service_status,
                description="获取所有Service状态和端点信息",
                args_schema=ServiceStatusInput
            ),
            StructuredTool(
                name="run_kubectl_command",
                func=self.run_kubectl_command,
                description="执行kubectl命令（仅限查询类命令，修改类命令需要额外授权）",
                args_schema=KubectlCommandInput
            )
        ]
    
    def get_cluster_nodes(self, _: str = "") -> str:
        """获取集群所有节点状态，包括节点名称、状态、角色、版本、资源容量等信息"""
        try:
            nodes = self.v1.list_node()
            result = []
            
            for node in nodes.items:
                node_info = {
                    "name": node.metadata.name,
                    "status": "Ready" if any(
                        condition.type == "Ready" and condition.status == "True"
                        for condition in node.status.conditions
                    ) else "NotReady",
                    "roles": node.metadata.labels.get("node-role.kubernetes.io/master", "worker"),
                    "version": node.status.node_info.kubelet_version,
                    "cpu": node.status.capacity.get("cpu"),
                    "memory": node.status.capacity.get("memory"),
                    "pods": node.status.capacity.get("pods")
                }
                result.append(node_info)
            
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"获取节点信息失败: {str(e)}"
    
    def get_pod_status(self, namespace: str = "default") -> str:
        """获取指定命名空间的所有Pod状态，包括运行状态、重启次数、资源使用等"""
        try:
            # 如果 namespace 为 'all'，获取所有命名空间的 Pod
            if namespace.lower() == 'all':
                pods = self.v1.list_pod_for_all_namespaces()
            else:
                pods = self.v1.list_namespaced_pod(namespace)
            result = []
            
            for pod in pods.items:
                pod_info = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "restarts": sum(
                        container.restart_count 
                        for container in (pod.status.container_statuses or [])
                    ),
                    "node": pod.spec.node_name,
                    "ip": pod.status.pod_ip,
                    "ready": sum(
                        1 for container in (pod.status.container_statuses or [])
                        if container.ready
                    )
                }
                
                # 检查异常状态
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        if container.state.waiting:
                            pod_info["issue"] = container.state.waiting.reason
                        elif container.state.terminated:
                            pod_info["issue"] = container.state.terminated.reason
                
                result.append(pod_info)
            
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"获取Pod状态失败: {str(e)}"
    
    def get_pod_logs(self, pod_name: str, namespace: str = "default", 
                     container: str = None, tail_lines: int = 100) -> str:
        """获取指定Pod的日志，用于问题诊断和错误分析"""
        try:
            kwargs = {
                "name": pod_name,
                "namespace": namespace,
                "tail_lines": tail_lines
            }
            if container:
                kwargs["container"] = container
                
            logs = self.v1.read_namespaced_pod_log(**kwargs)
            return logs
        except Exception as e:
            error_msg = str(e)
            # 如果错误提示需要指定容器，提取容器列表
            if "container name must be specified" in error_msg:
                return f"获取Pod日志失败: 该Pod有多个容器，{error_msg}"
            return f"获取Pod日志失败: {error_msg}"
    
    def get_node_metrics(self, _: str = "") -> str:
        """获取节点的实时资源使用指标（CPU、内存使用率）"""
        try:
            metrics = self.metrics_api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
            
            result = []
            for item in metrics.get("items", []):
                node_metric = {
                    "name": item["metadata"]["name"],
                    "cpu_usage": item["usage"]["cpu"],
                    "memory_usage": item["usage"]["memory"],
                    "timestamp": item["timestamp"]
                }
                result.append(node_metric)
            
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"获取节点指标失败: {str(e)}"
    
    def get_events(self, namespace: str = "default", limit: int = 50) -> str:
        """获取集群事件，包括Warning和Error级别的事件，用于问题追踪"""
        try:
            # 如果 namespace 为 'all'，获取所有命名空间的事件
            if namespace.lower() == 'all':
                events = self.v1.list_event_for_all_namespaces()
            else:
                events = self.v1.list_namespaced_event(namespace)
            result = []
            
            for event in events.items[:limit]:
                event_info = {
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "object": f"{event.involved_object.kind}/{event.involved_object.name}",
                    "count": event.count,
                    "first_time": str(event.first_timestamp),
                    "last_time": str(event.last_timestamp)
                }
                result.append(event_info)
            
            # 按时间倒序排序
            result.sort(key=lambda x: x["last_time"], reverse=True)
            
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"获取事件失败: {str(e)}"
    
    def restart_pod(self, pod_name: str, namespace: str = "default") -> str:
        """重启指定的Pod（通过删除Pod让Deployment重建）"""
        try:
            self.v1.delete_namespaced_pod(
                name=pod_name,
                namespace=namespace,
                body=client.V1DeleteOptions()
            )
            return f"Pod {pod_name} 已成功删除，等待重建"
        except Exception as e:
            return f"重启Pod失败: {str(e)}"
    
    def scale_deployment(self, deployment_name: str, replicas: int, 
                         namespace: str = "default") -> str:
        """调整Deployment的副本数量，用于扩缩容"""
        try:
            body = {"spec": {"replicas": replicas}}
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body=body
            )
            return f"Deployment {deployment_name} 已扩缩容至 {replicas} 个副本"
        except Exception as e:
            return f"扩缩容失败: {str(e)}"
    
    def get_service_status(self, namespace: str = "default") -> str:
        """获取所有Service状态和端点信息"""
        try:
            # 如果 namespace 为 'all'，获取所有命名空间的 Service
            if namespace.lower() == 'all':
                services = self.v1.list_service_for_all_namespaces()
            else:
                services = self.v1.list_namespaced_service(namespace)
            result = []
            
            for svc in services.items:
                svc_info = {
                    "name": svc.metadata.name,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip,
                    "ports": [
                        f"{port.port}:{port.target_port}/{port.protocol}"
                        for port in (svc.spec.ports or [])
                    ],
                    "selector": svc.spec.selector
                }
                result.append(svc_info)
            
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"获取Service状态失败: {str(e)}"
    
    def run_kubectl_command(self, command: str) -> str:
        """执行kubectl命令（仅限查询类命令，修改类命令需要额外授权）"""
        # 安全检查：只允许查询命令
        safe_commands = ["get", "describe", "logs", "top", "explain"]
        if not any(cmd in command for cmd in safe_commands):
            return "拒绝执行：仅允许查询类命令"
        
        try:
            result = subprocess.run(
                f"kubectl {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"执行kubectl命令失败: {str(e)}"

