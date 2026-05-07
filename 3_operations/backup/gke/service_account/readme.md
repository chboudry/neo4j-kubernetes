# Documentation 

https://neo4j.com/docs/operations-manual/current/backup-restore/

https://neo4j.com/docs/operations-manual/current/kubernetes/operations/backup-restore/

# Steps 

## 1. Prerequisites

### Variables
```
export PROJECT_ID="chboudry-project"
export BUCKET_NAME="chboudry-import-bucket"
export BUCKET_REGION="europe-west1"
export SERVICE_ACCOUNT_NAME="neo4j-backup-sa"
```

### Create the backup bucket
```
gcloud storage buckets create gs://$BUCKET_NAME \
  --project $PROJECT_ID \
  --location=$BUCKET_REGION \
  --uniform-bucket-level-access
```
### Create the service account 
```
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --project $PROJECT_ID \
  --display-name="Neo4j Backup Service Account"
```

### Retrieve SA email
```
export SA_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
```

### Grant access
```
gsutil iam ch serviceAccount:$SA_EMAIL:objectAdmin \
  gs://$BUCKET_NAME
```

### Create a json key
```
gcloud iam service-accounts keys create key.json \
  --iam-account=$SA_EMAIL
```

### Create a kubernetes secret for that key
```
kubectl create secret generic neo4j-backup-sa \
  --from-file=key.json \
  -n application
```

## 2. Setup

### Install through helm
```
helm install neo4j-backup neo4j/neo4j-admin \
  -f 3_operations/backup/gke/service_account/neo4j_backup.yaml \
  -n application
```

## 3. Monitor

### Check the cron
```
kubectl get cronjob -n application
kubectl describe cronjob neo4j-backup -n application
```

### Manual Launch
```
kubectl create job --from=cronjob/neo4j-backup neo4j-backup-manual -n application
```

### Review backup in progres
```
kubectl get pods -n application
kubectl logs neo4j-backup-manual-s6fvj -n application
```

### Look at the backups
```
gsutil ls gs://$BUCKET_NAME
```