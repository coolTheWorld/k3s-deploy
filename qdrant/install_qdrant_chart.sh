#!/bin/bash
helm --kubeconfig /etc/rancher/k3s/k3s.yaml install qdrant qdrant/qdrant -f  qdrant-values.yaml