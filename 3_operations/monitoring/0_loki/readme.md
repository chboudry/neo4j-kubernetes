```
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo update
```

```
helm install loki grafana-community/loki -f 3_operations/monitoring/0_loki/loki_single.yaml
```

```
kubectl get pods 
kubectl get svc
```

```
kubectl port-forward svc/loki 3100:3100
```

http://127.0.0.1:3100/ready
http://127.0.0.1:3100/metrics
