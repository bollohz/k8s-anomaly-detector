#!/usr/bin/env sh

set -euo

helm upgrade --namespace "$1" --install k8s-anomaly-detector-redis stable/redis --version 10.0.1  -f k8s-anomaly-detector-redis/values.yaml --debug
helm upgrade --install k8s-anomaly-detector ./k8s-anomaly-detector --namespace "$1" -f k8s-anomaly-detector/"$2" --version 1.0.0 --debug
