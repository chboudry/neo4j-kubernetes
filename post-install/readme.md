# 1. Apply post install
```
kubectl apply -f post-install/1_neo4j_post_install_job.yaml
```
# 2. Check Status
```
kubectl get job -n application neo4j-post-install -w
kubectl describe job -n application neo4j-post-install
```

# 3. Review logs
```
kubectl logs -n application -l job-name=neo4j-post-install -f
```

# 4. Manual Verification

```
kubectl run -it --rm --namespace "application" --image "neo4j:2025.12.1" cyphershell -- cypher-shell -a "neo4j://my-neo4j-release.application.svc.cluster.local:7687" -u neo4j -p "my-initial-password"
```

```
SHOW DATABASES;
```
```
SHOW USERS;
```
```
SHOW ROLES;
```

# 5. Clean up (optionnal - does not affect post install)
```
kubectl delete job -n application neo4j-post-install
```