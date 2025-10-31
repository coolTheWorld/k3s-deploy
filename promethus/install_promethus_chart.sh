#!/usr/bin/env bash
source ./deploy.conf

helm --kubeconfig /etc/rancher/k3s/k3s.yaml  install prometheus --namespace monitoring  --create-namespace -f promethus_values.yaml prometheus-${PROMETHUS_VERSION}.tgz

kubectl apply -f gateway-promethus.yaml