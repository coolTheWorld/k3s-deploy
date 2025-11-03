#!/bin/bash

kubectl port-forward svc/qdrant --address=0.0.0.0 19449:6333 &

kubectl port-forward svc/redis-master --address=0.0.0.0 19448:6379 &

kubectl port-forward svc/kube-prometheus-stack-prometheus --address=0.0.0.0 19447:9090 &

kubectl port-forward svc/kube-prometheus-stack-grafana --address=0.0.0.0 19446:80 &

kubectl proxy --port=19445 --address=0.0.0.0 --accept-hosts='.*' &