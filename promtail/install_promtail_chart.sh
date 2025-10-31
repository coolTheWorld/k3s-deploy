#!/bin/bash
helm --kubeconfig /etc/rancher/k3s/k3s.yaml install promtail grafana/promtail -f  promtail-values.yaml