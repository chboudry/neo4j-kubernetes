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

kubectl cluster-info
kubectl get nodes
```

# 2. Create disk and bucket

## Create disk for data
```
gcloud compute disks create neo4j-data-disk \
    --project $PROJECT_ID \
    --zone $REGION \
    --type pd-ssd \
    --size 50GB
```
## Create bucket for import
```
gsutil mb -p ${PROJECT_ID} -l ${BUCKET_REGION} -c STANDARD gs://${BUCKET_NAME}
```
## Check
```
gsutil ls -L gs://${BUCKET_NAME}
```
# 3. Configure Workload Identity

## Enable Workload Identity on cluster (authentication mechanism)
```
gcloud container clusters update $CLUSTER_NAME \
    --project $PROJECT_ID \
    --workload-pool=$PROJECT_ID.svc.id.goog \
    --zone=$REGION
```

## Enable GCS Fuse CSI driver addon (volume mounting mechanism)
```
gcloud container clusters update $CLUSTER_NAME \
    --project $PROJECT_ID \
    --update-addons GcsFuseCsiDriver=ENABLED \
    --zone=$REGION
```

## Verify node pool Workload Identity
```
gcloud container node-pools list \
  --project=$PROJECT_ID \
  --cluster "$CLUSTER_NAME" \
  --zone="$REGION"
```
```
gcloud container node-pools describe <POOL_NAME> \
  --project=$PROJECT_ID \
  --cluster "$CLUSTER_NAME" \
  --zone="$REGION" \
  --format='value(config.workloadMetadataConfig.mode)'
```
If the describe command prints nothing (or `GCE_METADATA`), update that pool to use Workload Identity. This recreates the nodes.
```
gcloud container node-pools update <POOL_NAME> \
  --project=$PROJECT_ID \
  --cluster "$CLUSTER_NAME" \
  --zone="$REGION" \
  --workload-metadata=GKE_METADATA
```
Wait for the update to finish before proceeding.

## Get project number
```
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
```
## Provide IAM permissions to Kubernetes Service Account
```
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member "principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PROJECT_ID}.svc.id.goog/subject/ns/application/sa/neo4j-gcs-sa" \
    --role "roles/storage.objectAdmin"
```

## Create a Google Service Account
```
gcloud iam service-accounts create neo4j-gcs-gsa \
    --project=$PROJECT_ID \
    --display-name="Neo4j GCS Access"
```

## Grant storage permissions to the GSA
```
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:neo4j-gcs-gsa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

## Bind Kubernetes SA to Google SA
```
gcloud iam service-accounts add-iam-policy-binding neo4j-gcs-gsa@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=$PROJECT_ID \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:${PROJECT_ID}.svc.id.goog[application/neo4j-gcs-sa]"
```

## Check permissions
```
gcloud storage buckets get-iam-policy gs://${BUCKET_NAME}
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

## Add NEO4J Helm repo
```
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
```

## Install Neo4j
```
helm install my-neo4j-release neo4j/neo4j \
    --namespace application \
    -f 1_neo4j.yaml
```

## Patch annotations
```
kubectl patch statefulset my-neo4j-release -n application \
  --type=merge \
  -p '{
    "spec": {
      "template": {
        "metadata": {
          "annotations": {
            "gke-gcsfuse/volumes": "true"
          }
        }
      }
    }
  }'
```
## Recreate pod 
```
kubectl delete pod my-neo4j-release-0 -n application
```
## Wait deployment to finish
```
kubectl --namespace application rollout status \
    --watch --timeout=600s statefulset/my-neo4j-release
```
or 
```
kubectl describe pod my-neo4j-release-0 -n application
```
## Access database
```
kubectl run -it --rm --namespace "application" --image "neo4j:2025.12.1" cyphershell -- cypher-shell -a "neo4j://my-neo4j-release.application.svc.cluster.local:7687" -u neo4j -p "my-initial-password"
```
## Logs
```
kubectl exec my-neo4j-release-0 -n application -- tail -n50 /logs/neo4j.log
```

# 6. Test import

## Create persons.csv in bucket/import/
```
personId,name,age
1,Alice,34
2,Bob,28
3,Charlie,45
4,Diana,31
5,Eric,29
```

## Connect on the neo4J pod
```
kubectl exec -it my-neo4j-release-0 -n application -- bash
```
## Run Import
```
helm upgrade my-neo4j-release neo4j/neo4j \
  --namespace application \
  --version=2025.10.1 \
  --reuse-values \
  --set neo4j.offlineMaintenanceModeEnabled=true
```
```
kubectl exec my-neo4j-release-0 -n application -- neo4j-admin database import full \
  neo4j \
  --nodes=/import/persons.csv \
  --overwrite-destination=true
```
```
helm upgrade my-neo4j-release neo4j/neo4j \
  --namespace application \
  --version=2025.10.1 \
  --reuse-values \
  --set neo4j.offlineMaintenanceModeEnabled=false
```
```
kubectl get pod my-neo4j-release-0 -n application
```

# 7. Deploy Reverse proxy
