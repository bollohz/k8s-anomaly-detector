#!/usr/bin/env sh

helm delete --purge k8s-anomaly-detector
helm delete --purge k8s-anomaly-detector-redis
