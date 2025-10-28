# Setup 

1 standalone neo4J instance on a GKE 
     NOT accessible from outside
1 LB with public IP to access
     accessible to the outside
     able to reach neo4j service

# 1. Setup GKE
brew install --cask gcloud-cli
gcloud auth login
gcloud components install gke-gcloud-auth-plugin
gcloud container clusters create chboudry-cluster --project chboudry-project --zone europe-west1-b --num-nodes 3 --machine-type e2-medium 
gcloud container clusters get-credentials chboudry-cluster --zone europe-west1-b --project chboudry-project
kubectl config current-context
kubectl config get-contexts
kubectl cluster-info
kubectl get nodes



helm show values neo4j/neo4j

# 2. Setup neo4j standalone

https://neo4j.com/docs/operations-manual/current/kubernetes/accessing-neo4j/

kubectl get ns
kubectl create namespace application
kubectl config set-context --current --namespace=application

helm install my-neo4j-release neo4j/neo4j --namespace application -f 1_neo4j.yaml

kubectl --namespace "application" rollout status --watch --timeout=600s statefulset/my-neo4j-release

kubectl get service -l helm.neo4j.com/service=default,helm.neo4j.com/instance=my-neo4j-release

kubectl run -it --rm --namespace "application" --image "neo4j:2025.09.0" cyphershell -- cypher-shell -a "neo4j://my-neo4j-release.application.svc.cluster.local:7687" -u neo4j -p "my-initial-password"

show databases;

kubectl exec my-neo4j-release-0 -- tail -n50 /logs/neo4j.log

# 3. Setup LB
https://neo4j.com/docs/operations-manual/current/kubernetes/accessing-neo4j-ingress/#_install_the_reverse_proxy_helm_chart

https://github.com/neo4j/helm-charts/blob/dev/neo4j-reverse-proxy/values.yaml

helm show values neo4j/neo4j-reverse-proxy

helm upgrade --install ingress-nginx ingress-nginx \
      --repo https://kubernetes.github.io/ingress-nginx \
      --namespace proxy --create-namespace

helm install rp neo4j/neo4j-reverse-proxy -f 2_load_balancer.yaml --namespace proxy

kubectl get ingress/rp-reverseproxy-ingress -n proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
kubectl logs rp-reverseproxy-dep-6b56547479-gh2dk -n proxy 

http://34.77.79.14:80 

kubectl apply -f 3_nginx_tcp.yaml
kubectl get svc -n proxy
kubectl edit svc ingress-nginx-controller -n proxy -o yaml
- name: proxied-tcp-9000
  port: 9000
  protocol: TCP
  targetPort: 9000
kubectl edit deployment ingress-nginx-controller -n proxy
--tcp-services-configmap=proxy/tcp-services

cypher-shell -a neo4j://34.77.79.14:9000 -u neo4j -p my-initial-password


