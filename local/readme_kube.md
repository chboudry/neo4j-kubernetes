# Outils de base
brew install --cask docker
brew install kubectl helm minikube
brew install --cask lens


# Démarrez Docker Desktop puis :
minikube stop
minikube delete
minikube start --driver=docker --nodes=1 --cpus=6 --memory=16g --disk-size=40g
minikube start --driver=docker --nodes=3 --cpus=2 --memory=4g --disk-size=10g

minikube addons enable storage-provisioner
minikube addons enable default-storageclass


helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
kubectl create namespace neo4j


helm install core-1 neo4j/neo4j -n neo4j -f standalone.yaml

xa1FR38hnGNfdd

# Membre 1
helm install core-1 neo4j/neo4j -n neo4j -f values-core.yaml
# Membre 2
helm install core-2 neo4j/neo4j -n neo4j -f values-core.yaml
# Membre 3
helm install core-3 neo4j/neo4j -n neo4j -f values-core.yaml

# monitor
kubectl get pods -n neo4j -w
#ContainerCreating
#Running

# debug 
kubectl describe pod -n neo4j core-1-0 | sed -n '/Events/,$p'

kubectl get svc -n neo4j
# Accès interne (DNS headless du cluster)
kubectl exec -n neo4j deploy/core-1-neo4j -- cypher-shell -u neo4j -p 'ChangezMoi!42' \
  'SHOW SERVERS;'


# Expose HTTP (7474) + Bolt (7687) du service du membre 1
kubectl port-forward -n neo4j svc/core-1-neo4j 7474:7474 7687:7687


# Keep up to date
helm repo update
helm upgrade core-1 neo4j/neo4j -n neo4j -f values-core.yaml
helm upgrade core-2 neo4j/neo4j -n neo4j -f values-core.yaml
helm upgrade core-3 neo4j/neo4j -n neo4j -f values-core.yaml
