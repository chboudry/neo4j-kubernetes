# Prereqs
brew install --cask docker
brew install kubectl helm kind

# Start Docker Desktop (it provides the Docker engine)
open -a "Docker"

# Create a 3-node cluster (1 control-plane + 2 workers)
cat <<'EOF' > kind-neo4j.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
# Optional: map a host path for persistent data if you want
# extraMounts:
#   - hostPath: /tmp/kind-data
#     containerPath: /var/local-path-provisioner
EOF

kind create cluster --name neo4j --config kind-neo4j.yaml

# Point kubectl to the kind context
kubectl cluster-info --context kind-neo4j
kubectl get nodes

# Install a default StorageClass (local-path)
helm repo add rancher https://charts.rancher.io
helm repo update
helm install local-path-storage rancher/local-path-provisioner \
  -n kube-system --create-namespace \
  --set storageClass.defaultClass=true

# Confirm default StorageClass
kubectl get storageclass

# Neo4j Helm repo + namespace
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
kubectl create namespace neo4j

# Deploy Membre 1 (core)
helm install core-1 neo4j/neo4j -n neo4j -f values-core.yaml


OowqF6kgIUBCVT