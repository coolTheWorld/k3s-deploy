#!/bin/bash
set -e

source ./deploy.conf
echo "export PATH=$PATH:/usr/local/bin" >> /etc/profile
echo "export K3S_DATA_DIR=$K3S_DATA_DIR" >> /etc/profile
source /etc/profile

# 1. 创建镜像目录
mkdir -p ${IMAGE_DIR}

# 2. 复制镜像包到镜像目录
cp k3s-airgap-images-amd64.tar.zst ${IMAGE_DIR}

# 3. 复制 K3s 二进制文件
cp k3s /usr/local/bin/
chmod +x /usr/local/bin/k3s

# 4. 如果启用 SELinux，安装 SELinux RPM
# sudo yum install -y ./k3s-selinux-1.4-1.el8.noarch.rpm
# 或 Ubuntu/Debian（通常不需要）

# 安装
INSTALL_K3S_SKIP_DOWNLOAD=true K3S_URL="https://${MASTER_SERVER_IP}:6443"  K3S_TOKEN="${K3S_TOKEN}" INSTALL_K3S_EXEC=" --embedded-registry" ./install_k3s.sh
# 检查服务状态
#systemctl status k3s

# 检查节点状态
k3s kubectl get nodes

# 获取集群 Token（后续节点需要）
