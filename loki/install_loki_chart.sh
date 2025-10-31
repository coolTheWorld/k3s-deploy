#!/bin/bash
helm --kubeconfig /etc/rancher/k3s/k3s.yaml install loki grafana/loki -f  loki-values.yaml