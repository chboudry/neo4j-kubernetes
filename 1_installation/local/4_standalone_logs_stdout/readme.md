kubectl logs -n neo4j standalone-0 -f

kubectl logs -n neo4j standalone-0 -f | grep '"log_source":"query"'

kubectl exec -n neo4j standalone-0 -- ls -l /logs