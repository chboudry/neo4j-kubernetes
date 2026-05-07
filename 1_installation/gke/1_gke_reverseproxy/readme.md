# Description

**Neo4j Tutorial deployment on GKE with:**

**Network Architecture:**
- Reverse proxy (nginx) for HTTPS web interface access from internet
- Direct Bolt access via nginx TCP proxy on dedicated port
- Neo4j service as ClusterIP (not directly accessible from outside)

**Security:**
- Internal Neo4j service (ClusterIP)
- Public access only through reverse proxy + NGINX bolt port


# 1. Prerequisites you might need

## Constraints

- Splitting reverse proxy & neo4j in 2 kubernetes namespaces as below requires helm charts 2025.10.1 minimum
- Neo4j Browser has 2 UIs. For the latest to take the port into account, you need to be at least version 2025.12.17 which is shipped in Neo4j 2025.12.1.

## Variables
```
export PROJECT_ID="chboudry-project"
export REGION="europe-west1-b"

export BUCKET_NAME="chboudry-import-bucket"
export BUCKET_REGION="europe-west1"

export CLUSTER_NAME="chboudry-cluster"
export CLUSTER_NODES_NUM=3
export MACHINE_TYPE="n2-standard-2"
```

## gcloud-cli for MAC
```
brew install --cask gcloud-cli
gcloud components install gke-gcloud-auth-plugin
```
## Authent
```
gcloud auth login
```
## Cluster Creation & kubectl set context
```
gcloud container clusters create $CLUSTER_NAME \
 --project $PROJECT_ID \
 --zone $REGION \
 --num-nodes $CLUSTER_NODES_NUM \
 --machine-type $MACHINE_TYPE 

gcloud container clusters get-credentials $CLUSTER_NAME --zone $REGION --project $PROJECT_ID

kubectl config current-context
kubectl config get-contexts
```

# 2. Deploy Neo4j

```
kubectl create namespace application
```

```
helm install my-neo4j-release neo4j/neo4j --namespace application -f 1_neo4j.yaml
```

```
kubectl --namespace "application" rollout status --watch --timeout=600s statefulset/my-neo4j-release
```

```
kubectl run -it --rm --namespace "application" --image "neo4j:2025.12.1" cyphershell -- cypher-shell -a "neo4j://my-neo4j-release.application.svc.cluster.local:7687" -u neo4j -p "my-initial-password"
```

```
show databases;
```

```
kubectl exec my-neo4j-release-0 -- tail -n50 /logs/neo4j.log
```

# 3. Setup Load Balancer & Neo4j Reverse Proxy

https://neo4j.com/docs/operations-manual/current/kubernetes/accessing-neo4j-ingress/#_install_the_reverse_proxy_helm_chart

https://github.com/neo4j/helm-charts/blob/dev/neo4j-reverse-proxy/values.yaml

helm show values neo4j/neo4j-reverse-proxy

```
helm upgrade --install ingress-nginx ingress-nginx \
     --repo https://kubernetes.github.io/ingress-nginx \
     --namespace proxy --create-namespace
```

```
helm install rp neo4j/neo4j-reverse-proxy -f 2_load_balancer.yaml --namespace proxy
```
```
kubectl get ingress/rp-reverseproxy-ingress -n proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

```
kubectl logs rp-reverseproxy-dep-6b56547479-gh2dk -n proxy 
```

http://34.77.79.14:80 

# 4. Setup Bolt DirectAccess

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


