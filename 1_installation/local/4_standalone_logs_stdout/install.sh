#!/usr/bin/env bash
#
# Neo4j standalone 2026.01.4 en local, avec TOUS les logs écrits
# à la fois dans les fichiers /logs/*.log ET sur la sortie standard
# du conteneur (visible via `kubectl logs`).
#
# La bascule "logs -> stdout" est faite dans neo4j.yaml (logging.serverLogsXml
# et logging.userLogsXml), via un appender <Console target="SYSTEM_OUT">.
#
# Prérequis : kind, kubectl et helm installés (le cluster kind est créé par
# ce script).
#
# Usage :
#   ./install.sh            # crée le cluster kind + déploie
#   ./install.sh teardown   # supprime le cluster kind
#
set -euo pipefail

NEO4J_VERSION="2026.01.4"
CLUSTER="neo4j-logs"
NS="neo4j"
RELEASE="standalone"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "${1:-}" == "teardown" ]]; then
  echo ">> Suppression du cluster kind '$CLUSTER'..."
  kind delete cluster --name "$CLUSTER"
  exit 0
fi

# --- Cluster kind ----------------------------------------------------------
echo ">> Création du cluster kind '$CLUSTER'..."
if ! kind get clusters | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER"
else
  echo "   cluster déjà présent, on continue."
fi

echo ">> Contexte kube courant : $(kubectl config current-context)"

echo ">> Helm repo neo4j..."
helm repo add neo4j https://helm.neo4j.com/neo4j >/dev/null 2>&1 || true
# On ne met à jour QUE le repo neo4j (d'autres repos cassés feraient
# échouer un "helm repo update" global à cause du set -e).
helm repo update neo4j

echo ">> Namespace '$NS'..."
kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -

# Si une release existe mais n'est pas "deployed" (état failed/pending d'un
# essai précédent), on la nettoie pour repartir propre.
if helm status "$RELEASE" -n "$NS" >/dev/null 2>&1; then
  STATUS="$(helm status "$RELEASE" -n "$NS" -o json | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)"
  if [[ "$STATUS" != "deployed" ]]; then
    echo ">> Release '$RELEASE' en état '$STATUS' -> désinstallation..."
    helm uninstall "$RELEASE" -n "$NS" || true
  fi
fi

echo ">> Installation de Neo4j $NEO4J_VERSION..."
# upgrade --install : idempotent (installe si absent, met à jour sinon),
# évite l'erreur "cannot reuse a name that is still in use" au relancement.
helm upgrade --install "$RELEASE" neo4j/neo4j \
  --version "$NEO4J_VERSION" \
  -n "$NS" \
  -f neo4j.yaml

echo ">> Attente du démarrage..."
kubectl -n "$NS" rollout status --watch --timeout=600s "statefulset/$RELEASE"

cat <<EOF

========================================================================
Neo4j déployé (ns=$NS, release=$RELEASE).

Voir les logs sur la sortie standard (fichiers + stdout) :
  kubectl logs -n $NS $RELEASE-0 -f

Vérifier que les fichiers de logs existent toujours dans le pod :
  kubectl exec -n $NS $RELEASE-0 -- ls -l /logs

Tout supprimer (cluster kind '$CLUSTER') :
  ./install.sh teardown
========================================================================
EOF
