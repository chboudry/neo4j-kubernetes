#  Grafana 
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm install grafana grafana/grafana -f 3_operations/monitoring/3_grafana/grafana.yaml

kubectl get secret grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode ; echo


kubectl port-forward svc/grafana 3000:80

http://localhost:3000

user: admin
password: 

{namespace="neo4j"}
{job="neo4j"} |= "ERROR"
{job="neo4j"} |= "WARNING"
{job="neo4j",file=~".*neo4j.log"}
{job="neo4j",file=~".*security.log"}
