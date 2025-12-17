# Description

**Production-ready Neo4j deployment on GKE with:**

**Network Architecture:**
- Reverse proxy (nginx) for HTTPS web interface access from internet
- Direct Bolt access via nginx TCP proxy on dedicated port
- Neo4j service as ClusterIP (not directly accessible from outside)

**Storage Architecture:**
- **Data volume**: Custom StorageClass with Retain policy on SSD (premium-rwo) for database files
- **Import volume**: GCS bucket mounted via CSI driver with Workload Identity for data import operations

**Security:**
- Workload Identity for secure bucket access (no service account keys)
- Internal Neo4j service (ClusterIP)
- Public access only through nginx reverse proxy

# 1. Prerequisites you might need

## Variables
```
export PROJECT_ID="chboudry-project"
export REGION="europe-west1-b"

export BUCKET_NAME="chboudry-import-bucket"
export BUCKET_REGION="europe-west1"

export CLUSTER_NAME="chboudry-cluster"
export CLUSTER_NODES_NUM=3
export MACHINE_TYPE="e2-medium"
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

kubectl cluster-info
kubectl get nodes
```

# 2. Create GCS bucket

## Create bucket and cluster in the same region
```
gsutil mb -p ${PROJECT_ID} -l ${BUCKET_REGION} -c STANDARD gs://${BUCKET_NAME}
```
## Check
```
gsutil ls -L gs://${BUCKET_NAME}
```
# 3. Configure Workload Identity

## 3.1 Enable Workload Identity on cluster
```
gcloud container clusters update $CLUSTER_NAME \
    --project $PROJECT_ID \
    --workload-pool=$PROJECT_ID.svc.id.goog \
    --zone=$REGION
```
## 3.2 Get project number
```
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
```
## 3.3 Provide IAM permissions to Kubernetes Service Account
```
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member "principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PROJECT_ID}.svc.id.goog/subject/ns/application/sa/neo4j-gcs-sa" \
    --role "roles/storage.objectUser"
```

## 3.4 Check permissions
```
gcloud storage buckets get-iam-policy gs://${BUCKET_NAME} \
    --flatten="bindings[].members" \
    --filter="bindings.members:neo4j-gcs-sa"
```
# 4. Deploy Kubernetes resources

## 4.1 create namespace
```
kubectl create namespace application
```
## 4.2 Deploy ServiceAccount, PV, PVC
```
kubectl apply -f 0_prerequisites.yaml
```
## 4.3 Check resources
```
kubectl get sa neo4j-gcs-sa -n application
kubectl get pv
kubectl get pvc -n application
```

## 4.4 Check PVC bound
```
kubectl describe pvc neo4j-import-pvc -n application
```

# 5. Deploy Neo4J

## 5.1 Add NEO4J Helm repo
```
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
```

## 5.2 Install Neo4j
```
helm install my-neo4j-release neo4j/neo4j \
    --namespace application \
    -f 1_neo4j.yaml
```

## 5.3 Wait deployment to finish
```
kubectl --namespace application rollout status \
    --watch --timeout=600s statefulset/my-neo4j-release
```