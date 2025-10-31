#!/bin/bash
K3S_SELINUX_VERSION="v1.6.stable.1"
curl -LO https://github.com/k3s-io/k3s-selinux/releases/download/${K3S_SELINUX_VERSION}/k3s-selinux-1.6-1.el9.noarch.rpm
rpm -ivh k3s-selinux*.rpm
rpm -qa | grep k3s-selinux
semodule -l | grep k3s
