K3S_VERSION="v1.34.1+k3s1"

# 1. 下载 K3s 二进制文件
curl -LO https://github.com/k3s-io/k3s/releases/download/${K3S_VERSION}/k3s
chmod +x k3s
# 或者 ARM64 架构
# curl -LO https://github.com/k3s-io/k3s/releases/download/${K3S_VERSION}/k3s-arm64
# chmod +x k3s-arm64

# 2. 下载安装脚本
curl -sfL https://get.k3s.io -o install_k3s.sh
chmod +x install_k3s.sh

# 3. 下载离线镜像包（根据架构选择）
# AMD64
curl -LO https://github.com/k3s-io/k3s/releases/download/${K3S_VERSION}/k3s-airgap-images-amd64.tar.zst
# 或 ARM64
# curl -LO https://github.com/k3s-io/k3s/releases/download/${K3S_VERSION}/k3s-airgap-images-arm64.tar.zst

# 4. 如果启用了 SELinux，下载 SELinux RPM（CentOS/RHEL） cat /etc/os-release 查找匹配的k3s-selinux包
K3S_SELINUX_VERSION="v1.6.stable.1"
curl -LO https://github.com/k3s-io/k3s-selinux/releases/download/${K3S_SELINUX_VERSION}/k3s-selinux-1.6-1.el8.noarch.rpm
