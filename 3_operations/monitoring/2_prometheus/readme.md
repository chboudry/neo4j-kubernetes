```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack -f 3_operations/monitoring/2_prometheus/0_prometheus.yaml

kubectl apply -f 3_operations/monitoring/2_prometheus/1_servicemonitor.yaml


kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090 -n default
```

http://localhost:9090/targets

