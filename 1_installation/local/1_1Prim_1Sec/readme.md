
## Create kind cluster of one node
```
kind create cluster --name neo4jtest
```

## Get context
```
kubectl cluster-info --context kind-neo4jtest
kubectl get nodes
```

## Neo4j Helm repo + namespace
```
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
kubectl create namespace neo4j
```

## Deploy Neo4j primary
```
helm -n neo4j install primary neo4j/neo4j -f 1_installation/local/1_1Prim_1Sec/primary.yaml
```

## Deploy Neo4j secondary
```
helm -n neo4j install secondary neo4j/neo4j -f 1_installation/local/1_1Prim_1Sec/secondary.yaml
```

## Check
```
kubectl -n neo4j get pods 
kubectl -n neo4j get svc 
kubectl -n neo4j logs  secondary-0 --tail=200
kubectl -n neo4j get endpoints myneo4j-lb-neo4j -o yaml
```

## Connect 
```
kubectl port-forward -n neo4j svc/myneo4j-lb-neo4j 7474:7474 7687:7687
```
http://127.0.0.1:7474/browser/