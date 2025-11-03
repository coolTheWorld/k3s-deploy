# #!/usr/bin/env python3
# """测试 K3s 连接"""
# import sys
# from pathlib import Path
#
# # 添加项目根目录到 Python 路径
# project_root = Path(__file__).parent.parent.parent
# sys.path.insert(0, str(project_root / 'src'))

# 使用绝对导入
from ..collectors.k3s_collector import K3sCollector
from ..utils.config import settings


def main():
    print("=== 测试 K3s API 连接 ===")
    print(f"Proxy URL: {settings.K3S_PROXY_URL}")

    try:
        # 初始化收集器
        collector = K3sCollector(settings.K3S_CONFIG)
        print("✅ 连接成功！")

        # 收集集群指标
        print("\n=== 收集集群指标 ===")
        metrics = collector.collect_cluster_metrics()

        print(f"\n节点信息:")
        print(f"  总数: {metrics['nodes']['total']}")
        print(f"  就绪: {metrics['nodes']['ready']}")
        print(f"  未就绪: {metrics['nodes']['not_ready']}")

        print(f"\nPod信息:")
        print(f"  总数: {metrics['pods']['total']}")
        print(f"  状态分布: {metrics['pods']['by_status']}")

        print(f"\nService信息:")
        print(f"  总数: {metrics['services']['total']}")
        print(f"  类型分布: {metrics['services']['by_type']}")

        print(f"\nDeployment信息:")
        print(f"  总数: {metrics['deployments']['total']}")
        print(f"  健康: {metrics['deployments']['healthy']}")
        print(f"  不健康: {metrics['deployments']['unhealthy']}")

    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()