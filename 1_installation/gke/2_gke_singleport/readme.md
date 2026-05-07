# Setup Neo4j sur GKE avec SNI TLS Routing# Setup 

1 standalone neo4j instance sur GKE avec TLS1 standalone neo4J instance on a GKE 

- NOT accessible from outside directement     NOT accessible from outside

- Accessible via Load Balancer avec SNI routing sur port 443:1 LB with public IP to access

  - `bolt.server:443` → Neo4j Bolt avec TLS (port 7687)     accessible to the outside

  - `https.server:443` → Neo4j Browser HTTPS (port 7474)     able to reach neo4j service


brew install --cask gcloud-cli

## 1. Setup GKEgcloud auth login

gcloud components install gke-gcloud-auth-plugin

bashgcloud container clusters create chboudry-cluster --project chboudry-project --zone europe-west1-b --num-nodes 3 --machine-type e2-medium 

brew install --cask gcloud-cligcloud container clusters get-credentials chboudry-cluster --zone europe-west1-b --project chboudry-project

gcloud auth loginkubectl config current-context

gcloud components install gke-gcloud-auth-pluginkubectl config get-contexts

gcloud container clusters create chboudry-cluster --project chboudry-project --zone europe-west1-b --num-nodes 3 --machine-type e2-medium 

gcloud container clusters get-credentials chboudry-cluster --zone europe-west1-b --project chboudry-project

kubectl config current-context

kubectl cluster-info

kubectl get nodes

kubectl create namespace application
kubectl config set-context --current --namespace=application

## 2. Certificats

https://neo4j.com/docs/operations-manual/current/kubernetes/accessing-neo4j/


# Certificat pour Bolt

openssl req -x509 -newkey rsa:2048 -keyout bolt.server.key -out bolt.server.crt -days 1095 -nodes -subj "/CN=bolt.server" -addext "subjectAltName=DNS:bolt.server"

# Certificat pour HTTPS

openssl req -x509 -newkey rsa:2048 -keyout https.server.key -out https.server.crt -days 1095 -nodes -subj "/CN=https.server" -addext "subjectAltName=DNS:https.server"

# Créer les secrets TLS (type kubernetes.io/tls)

kubectl create secret tls bolt-server-tls -n application \
  --cert=bolt.server.crt \
  --key=bolt.server.key
  
kubectl create secret tls https-server-tls -n application \
  --cert=https.server.crt \
  --key=https.server.key 


## 3. Install NGINX Ingress Controller avec SSL passthrough

# 3. Setup LB

https://neo4j.com/docs/operations-manual/current/kubernetes/accessing-neo4j-ingress/#_install_the_reverse_proxy_helm_chart

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx

helm repo update https://github.com/neo4j/helm-charts/blob/dev/neo4j-reverse-proxy/values.yaml

# IMPORTANT: --set controller.extraArgs.enable-ssl-passthrough=truehelm show values neo4j/neo4j-reverse-proxy

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.extraArgs.enable-ssl-passthrough=true


## 4. Setup neo4j avec TLS sur Bolt

kubectl apply -f 2_ingress_bolt.yaml
kubectl apply -f 2_ingress_https.yaml


## 5. Install Neo4J

helm install my-neo4j-release neo4j/neo4j --namespace application -f 1_neo4j.yaml

kubectl --namespace "application" rollout status --watch --timeout=600s statefulset/my-neo4j-release

## 6. TEST

kubectl get ingress -n application

ADD ADDRESS bolt.server https.server to /etc/hosts

sudo vim /etc/hosts

https://https.server:443

cypher-shell -a neo4j+ssc://bolt.server:443 -u neo4j -p my-initial-password -d neo4j


```bash
# Vérifier les certificats montés dans le pod
kubectl exec -n application my-neo4j-release-0 -- ls -la /var/lib/neo4j/certificates/bolt/

# Vérifier les logs Neo4j
kubectl logs -n application my-neo4j-release-0 --tail=50 | grep -i "bolt\|tls"

# Tester TLS localement sur le pod Neo4j
kubectl exec -n application my-neo4j-release-0 -- openssl s_client -connect localhost:7687 -showcerts </dev/null 2>&1 | grep "subject="
# Devrait afficher: subject=CN=bolt.server
```

---

## 7. Déployer les Ingress avec SNI routing

```bash
# Déployer l'Ingress pour Bolt (avec ssl-passthrough)
kubectl apply -f 2_ingress_bolt.yaml

# Déployer l'Ingress pour HTTPS
kubectl apply -f 2_ingress_https.yaml

# Vérifier les Ingress
kubectl get ingress -n application
```

---

## 8. Récupérer l'IP du Load Balancer

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller

# Récupérer juste l'IP
export LB_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Load Balancer IP: $LB_IP"
```

---

## 9. Configurer /etc/hosts (temporaire pour les tests)

```bash
# Ajouter les entrées DNS locales
sudo bash -c "echo '$LB_IP bolt.server' >> /etc/hosts"
sudo bash -c "echo '$LB_IP https.server' >> /etc/hosts"

# Vérifier
cat /etc/hosts | grep server
```

---

## 10. Tester les connexions

```bash
# Test 1: Vérifier le certificat TLS sur Bolt
openssl s_client -servername bolt.server -connect $LB_IP:443 </dev/null 2>&1 | grep "subject="
# ✓ Devrait afficher: subject=CN=bolt.server

# Test 2: Vérifier le certificat TLS sur HTTPS
openssl s_client -servername https.server -connect $LB_IP:443 </dev/null 2>&1 | grep "subject="
# ✓ Devrait afficher: subject=CN=https.server

# Test 3: Connexion Cypher-shell (avec certificat auto-signé)
cypher-shell -a neo4j+ssc://bolt.server:443 -u neo4j -p my-initial-password -d neo4j

# Test 4: Neo4j Browser (ouvrir dans navigateur, accepter le certificat auto-signé)
open "https://https.server:443"
```

---

## 11. Commandes utiles pour déboguer

```bash
# Logs NGINX Ingress
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller --tail=100

# Vérifier que ssl-passthrough est activé
kubectl get deployment -n ingress-nginx ingress-nginx-controller -o yaml | grep "enable-ssl-passthrough"

# Config Neo4j complète
kubectl exec -n application my-neo4j-release-0 -- cat /var/lib/neo4j/conf/neo4j.conf | grep -i "bolt\|tls"

# Restart Neo4j si nécessaire
kubectl rollout restart statefulset my-neo4j-release -n application

# Vérifier les services
kubectl get service -n application
kubectl get svc -n ingress-nginx
```

---

## Architecture de la solution

```
                             ┌─────────────────────────┐
Internet ──────────────────► │  Load Balancer (443)    │
                             │  IP: 104.199.38.161     │
                             └───────────┬─────────────┘
                                         │
                                         │ TLS (SNI routing)
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
         SNI: bolt.server                          SNI: https.server
                    │                                         │
                    ▼                                         ▼
        ┌───────────────────────┐               ┌───────────────────────┐
        │ Ingress: bolt-server  │               │ Ingress: https-server │
        │ ssl-passthrough: true │               │ TLS termination       │
        └───────────┬───────────┘               └───────────┬───────────┘
                    │                                       │
                    │ TLS passthrough                       │ HTTP
                    │                                       │
                    ▼                                       ▼
        ┌───────────────────────┐               ┌───────────────────────┐
        │ Neo4j Service:7687    │               │ Neo4j Service:7474    │
        │ (Bolt avec TLS)       │               │ (Browser HTTPS)       │
        └───────────────────────┘               └───────────────────────┘
                    │                                       │
                    └───────────────┬───────────────────────┘
                                    ▼
                        ┌───────────────────────┐
                        │   Neo4j Pod           │
                        │   my-neo4j-release-0  │
                        └───────────────────────┘
```

---

## Notes importantes

### Fonctionnement du SNI Routing
1. **SNI (Server Name Indication)** : Extension TLS qui permet au client d'envoyer le nom de domaine dans le handshake TLS
2. **NGINX Ingress** lit le SNI sans décrypter le flux TLS et route vers le bon backend
3. **ssl-passthrough** : Le TLS est transmis tel quel à Neo4j (pas de terminaison au niveau NGINX)

### Différence Bolt vs HTTPS
- **Bolt (port 7687)** : Utilise ssl-passthrough car le protocole Bolt nécessite que Neo4j gère directement le TLS
- **HTTPS (port 7474)** : NGINX peut terminer le TLS (ou aussi utiliser passthrough)

### Certificats
- **Type de secret** : `kubernetes.io/tls` (clés: `tls.crt` et `tls.key`)
- **Production** : Utilisez Let's Encrypt ou un CA reconnu
- **Auto-signés** : Protocole `neo4j+ssc://` pour Cypher-shell

### Fichiers de configuration
- `1_neo4j.yaml` : Configuration Helm Neo4j avec `ssl.bolt.*` pour monter les certificats
- `2_ingress_bolt.yaml` : Ingress avec annotation `nginx.ingress.kubernetes.io/ssl-passthrough: "true"`
- `2_ingress_https.yaml` : Ingress standard pour Neo4j Browser
- `3_configmap.yaml` : Non utilisé dans cette configuration SNI (ConfigMap TCP non nécessaire)

### Upgrade si déjà déployé
```bash
# Mettre à jour Neo4j avec la nouvelle config
helm upgrade my-neo4j-release neo4j/neo4j --namespace application -f 1_neo4j.yaml

# Redéployer les Ingress
kubectl apply -f 2_ingress_bolt.yaml
kubectl apply -f 2_ingress_https.yaml
```
