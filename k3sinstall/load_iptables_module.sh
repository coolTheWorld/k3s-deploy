#!/bin/bash

yum install -y iptables* nftables kernel-modules-extra
# 1. 加载 iptables 相关内核模块
modprobe br_netfilter
modprobe overlay
modprobe xt_mark
modprobe xt_MASQUERADE
modprobe xt_conntrack
modprobe nf_conntrack
modprobe iptable_filter
modprobe iptable_nat
modprobe ipt_MASQUERADE
modprobe ip6t_MASQUERADE

# 2. 验证模块是否加载
lsmod | grep -E "br_netfilter|overlay|xt_mark|xt_MASQUERADE"

# 3. 持久化模块加载（开机自动加载）
cat <<EOF | tee /etc/modules-load.d/k3s.conf
br_netfilter
overlay
xt_mark
xt_MASQUERADE
xt_conntrack
nf_conntrack
iptable_filter
iptable_nat
ipt_MASQUERADE
ip6t_MASQUERADE
EOF

# 4. 配置内核参数
cat <<EOF | tee /etc/sysctl.d/k3s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

# 5. 应用配置
sysctl --system

# 6. 重启 k3s
systemctl restart k3s-agent
systemctl restart k3s


