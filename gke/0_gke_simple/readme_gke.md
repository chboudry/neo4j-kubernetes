brew install --cask gcloud-cli
gcloud auth login
gcloud components install gke-gcloud-auth-plugin
gcloud container clusters get-credentials cluster-1 --region us-central1 --project neo4j-ps-202001
kubectl config current-context
kubectl config get-contexts
kubectl cluster-info
kubectl get nodes

kubectl get ns
kubectl create namespace neo4j
kubectl config set-context --current --namespace=neo4j


helm install my-neo4j-release neo4j/neo4j --namespace neo4j -f gke_standalone_values.yaml

kubectl --namespace "neo4j" rollout status --watch --timeout=600s statefulset/my-neo4j-release

kubectl run --rm -it --namespace "neo4j" --image "neo4j:2025.08.0-enterprise" cypher-shell \
     -- cypher-shell -a "neo4j://my-neo4j-release.neo4j.svc.cluster.local:7687" -u neo4j -p "my-initial-password"