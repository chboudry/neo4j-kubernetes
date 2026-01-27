# Description

**Neo4j Tutorial deployment on GKE with:**

**Network Architecture:**
- Plain and simple Neo4j service as Load Balancer : directly accessible from outside

# 1. Prerequisites you might need

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