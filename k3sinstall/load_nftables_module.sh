#!/bin/bash
yum install -y iptables* nftables kernel-modules-extra

# 1. 加载 nftables 相关内核模块
modprobe nf_tables nf_nat nf_conntrack xt_conntrack xt_comment xt_mark xt_MASQUERADE iptable_filter iptable_nat br_netfilter overlay 
modprobe ipt_MASQUERADE
modprobe ip6t_MASQUERADE

# 2. 验证模块是否加载


# 3. 持久化模块加载（开机自动加载）
tee /etc/modules-load.d/k3s.conf >/dev/null <<'EOF'
nf_tables
nf_nat
nf_conntrack
xt_conntrack
xt_comment
xt_mark
xt_MASQUERADE
iptable_filter
iptable_nat
br_netfilter
overlay
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


