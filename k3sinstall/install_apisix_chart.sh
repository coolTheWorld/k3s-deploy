#!/usr/bin/env bash
source ./deploy.conf

kubectl  patch deployment metrics-server  -n kube-system  --type='json' -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

kubectl  rollout status deployment metrics-server -n kube-system

helm --kubeconfig /etc/rancher/k3s/k3s.yaml  install apisix --namespace kube-system  --create-namespace -f apisix_chart.yaml apisix-${K3S_APISIX_VERSION}.tgz