#!/bin/bash
helm --kubeconfig /etc/rancher/k3s/k3s.yaml install postgresql bitnami/postgresql -f  postgresql-values.yaml