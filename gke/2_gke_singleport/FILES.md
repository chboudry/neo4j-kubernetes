# Fichiers de configuration - SNI TLS Routing

Ce dossier contient la configuration pour déployer Neo4j sur GKE avec SNI TLS routing sur le port 443.

## Fichiers de configuration

### 1. `1_neo4j.yaml`
Configuration Helm pour Neo4j avec :
- TLS activé sur Bolt (`ssl.bolt.*`)
- Certificats montés depuis le secret `bolt-server-tls`
- Configuration `server.bolt.tls_level: "REQUIRED"`

### 2. `2_ingress_bolt.yaml`
Ingress pour le protocole Bolt avec :
- Annotation `nginx.ingress.kubernetes.io/ssl-passthrough: "true"`
- Host: `bolt.server`
- Backend: service `my-neo4j-release` port 7687

### 3. `2_ingress_https.yaml`
Ingress pour Neo4j Browser avec :
- Host: `https.server`
- Backend: service `my-neo4j-release` port 7474
- TLS terminaison au niveau NGINX

### 5. Certificats TLS
- `bolt.server.crt/key` : Certificat auto-signé pour Bolt
- `https.server.crt/key` : Certificat auto-signé pour HTTPS

## Comment ça marche

```
Client (bolt.server:443)
    ↓
    SNI: bolt.server
    ↓
NGINX Ingress (ssl-passthrough)
    ↓
Neo4j Service:7687 (Bolt TLS)
```

```
Client (https.server:443)
    ↓
    SNI: https.server
    ↓
NGINX Ingress (TLS termination)
    ↓
Neo4j Service:7474 (HTTP)
```

## Ordre de déploiement

1. Créer les certificats TLS
2. Créer le namespace `application`
3. Créer les secrets `bolt-server-tls` et `https-server-tls`
4. Installer NGINX Ingress Controller avec `--set controller.extraArgs.enable-ssl-passthrough=true`
5. Installer Neo4j avec `helm install ... -f 1_neo4j.yaml`
6. Appliquer `kubectl apply -f 2_ingress_bolt.yaml`
7. Appliquer `kubectl apply -f 2_ingress_https.yaml`

## Tests

```bash
# Vérifier les certificats
openssl s_client -servername bolt.server -connect $LB_IP:443 </dev/null 2>&1 | grep "subject="
openssl s_client -servername https.server -connect $LB_IP:443 </dev/null 2>&1 | grep "subject="

# Se connecter avec cypher-shell
cypher-shell -a neo4j+ssc://bolt.server:443 -u neo4j -p my-initial-password -d neo4j
```

Voir `readme_gke.md` pour les instructions détaillées.
