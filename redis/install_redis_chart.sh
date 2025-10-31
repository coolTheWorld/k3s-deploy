#!/bin/bash
helm --kubeconfig /etc/rancher/k3s/k3s.yaml install redis bitnami/redis -f  redis-values.yaml