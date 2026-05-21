Configmap targets neo4j in neo4j namespace
Edit configmap if you installed neo4j somewhere else

kubectl apply -n neo4j -f 3_operations/monitoring/1_sidecar_fluentbit/configmap.yaml 


helm -n neo4j upgrade primary  neo4j/neo4j -f 3_operations/monitoring/1_sidecar_fluentbit/neo4j.yaml

kubectl -n neo4j get pods

kubectl logs <neo4j-pod> -c fluent-bit -n neo4j

kubectl -n neo4j rollout status --watch --timeout=600s statefulset/primary

kubectl rollout restart statefulset/primary -n neo4j


kubectl -n neo4j exec -it primary-0  -c neo4j -- \
  sh -c 'echo "TEST-FLUENTBIT-$(date)" >> /logs/fluent-test.log'

kubectl -n neo4j logs primary-0 -c fluent-bit 

kubectl delete pvc -n neo4j -l app=myneo4j