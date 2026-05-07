# Local Neo4j Tutorial deployment

## Prerequisites for MAC
```
brew install --cask docker
brew install kubectl helm kind
```

## Start Docker Desktop (it provides the Docker engine)
```
open -a "Docker"
```

## Create a 3-node cluster (1 control-plane + 2 workers)
```
kind create cluster --name neo4j --config 0_kind-neo4j.yaml
```

## Point kubectl to the kind context
```
kubectl cluster-info --context kind-neo4j
kubectl get nodes
```

## Neo4j Helm repo + namespace
```
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
kubectl create namespace neo4j
```

# Deploy Neo4j
```
helm install my-neo4j-release neo4j/neo4j -n neo4j -f 1_neo4j.yaml
```

## Expose HTTP (7474) & Bolt (7687)
```
kubectl port-forward -n neo4j svc/my-neo4j-release 7888:7474 7999:7687
```

## Connect 
```
http://localhost:7888
```

```
bolt://localhost:7999
```