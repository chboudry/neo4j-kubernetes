# Standalone local avec plugins (GDS + Bloom)

Déploiement standalone minimal pour **troubleshooter le chargement des plugins**
(apoc, graph-data-science, bloom) et des licences.
Tout ce qui n'est pas lié aux plugins (SSL, SSO, certificats, custom image,
GCS, logging...) a été retiré pour simplifier.

## Créer le cluster local
```
kind create cluster --name neo4j-plugins
kubectl cluster-info --context kind-neo4j-plugins
kubectl get nodes
```

## Helm repo + namespace
```
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
kubectl create namespace neo4j
```

## Créer le secret des licences GDS + Bloom
Le volume `licenses` monte le secret `gds-bloom-license` (clés `gds.license`
et `bloom.license`) dans `/licenses`. Il faut le créer avant le déploiement :
```
kubectl create secret generic gds-bloom-license -n neo4j \
  --from-file=gds.license=./gds.license \
  --from-file=bloom.license=./bloom.license
```
> Sans licences valides, GDS et Bloom Enterprise ne seront pas activés
> (`RETURN gds.isLicensed();` renverra `false`), mais le pod démarre : utile
> pour distinguer un problème de chargement de plugin d'un problème de licence.

## Créer le secret du mot de passe neo4j
Le chart lit `neo4j.passwordFromSecret: neo4j-auth`. Le secret doit contenir une
clé `NEO4J_AUTH` au format `neo4j/<password>` :
```
kubectl create secret generic neo4j-auth -n neo4j \
  --from-literal=NEO4J_AUTH=neo4j/password3
```

## Déployer
Version Neo4j figée à `2026.01.4` (le chart Helm Neo4j suit le versionning du produit) :
```
helm install standalone neo4j/neo4j --version 2026.01.4 -n neo4j -f 1_neo4j.yaml
```

## Suivre le démarrage
```
kubectl get pods -n neo4j -w
kubectl logs -n neo4j standalone-0 --tail=200
```

## Se connecter
```
kubectl port-forward -n neo4j svc/standalone 7474:7474 7687:7687
```
http://localhost:7474

## Vérifier les plugins
```
SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'gds.';
RETURN gds.version();
RETURN gds.isLicensed();
CALL gds.license.state();
```

## Vérifier les licences dans le pod
```
kubectl exec -n neo4j standalone-0 -- ls -l /licenses/
kubectl exec -n neo4j standalone-0 -- stat /licenses/gds.license
```

## Points de vigilance (troubleshooting du YAML client)
- `server.unmanaged_extension_classes` référence `semantics.extension=/rdf`
  (neosemantics / n10s) alors que `n10s` **n'est pas** dans `NEO4J_PLUGINS`.
  Si le JAR neosemantics n'est pas présent, le serveur peut échouer à charger
  l'extension `/rdf`. À ajouter au plugins ou à retirer de la config.
- Le volume `plugins` est en `mode: share` sur `data` : les plugins téléchargés
  via `NEO4J_PLUGINS` doivent atterrir dans le volume data partagé.
- `gds.enterprise.license_file` / `dbms.bloom.license_file` pointent vers
  `/licenses/*` : vérifier que le secret est bien monté (lisible par l'uid neo4j).



The neo4j user's password has been set to "password".To view the progress of the rollout try:

  $ kubectl --namespace "neo4j" rollout status --watch --timeout=600s statefulset/standalone

Once rollout is complete you can log in to Neo4j at "neo4j://standalone.neo4j.svc.cluster.local:7687". Try:

  $ kubectl run --rm -it --namespace "neo4j" --image "neo4j:2026.06.0-enterprise" cypher-shell \
     -- cypher-shell -a "neo4j://standalone.neo4j.svc.cluster.local:7687" -u neo4j -p "password"