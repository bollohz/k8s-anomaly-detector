# Summary

Redis used by k8s-anomaly-detector installation
## Install

```console
helm upgrade --namespace ${TARGET_NAMESPACE} --install k8s-anomaly-detector-redis stable/redis --version 10.0.1  -f values.yaml 
```


## Uninstall
```console
helm delete --purge k8s-anomaly-detector-redis
```
