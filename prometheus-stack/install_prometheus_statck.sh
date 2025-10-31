#!/bin/bash
helm --kubeconfig /etc/rancher/k3s/k3s.yaml install kube-prometheus-stack prometheus-community/kube-prometheus-stack -f  prometheus-statck-values.yaml
kubectl apply -f gateway-promethus-statck.yaml