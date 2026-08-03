# SSL / TLS for Neo4j on Kubernetes

This document explains how to configure SSL/TLS certificates for Neo4j deployed on Kubernetes, covering both standalone and cluster deployments.

---

## Key Concepts

| Term | Description |
|---|---|
| **Certificate (public key)** | The public half of a key pair. Safe to distribute. Sent on the wire so clients can verify server identity. |
| **Private Key** | The secret half of the key pair. Must never leave the server. |
| **Certificate Authority (CA)** | The entity that signs certificates. Can be internal (self-managed PKI), an IT Security team CA, or a commercial CA. |
| **SAN (Subject Alternative Name)** | Extension field in a certificate listing additional valid hostnames / IPs. If SANs are present, the CN may be ignored — always include the primary FQDN in the SAN list. |
| **Wildcard certificate** | A single certificate valid for all hosts under a domain level: `*.neo4j.example.com` covers `node1.neo4j.example.com`, `node2.neo4j.example.com`, etc. The wildcard `*` can only appear at the **leftmost** label: `*.neo4j.example.com` is valid, `neo4j.*.example.com` is not. |

> **Reference:** [Deploying Neo4j with Certificates: Preparation](https://support.neo4j.com/s/article/1500001257002-Deploying-Neo4j-with-Certificates-Preparation)

---

## Naming Strategy

Always use **Fully Qualified Domain Names (FQDNs)** — never short names or IP addresses.

- Use a consistent, hierarchical DNS zone dedicated to your Neo4j nodes (e.g., `neo4j.example.com`).
- The FQDN must be used everywhere: browser URL bar, application connection strings, and all `neo4j.conf` settings (`server.default_advertised_address`, `dbms.cluster.discovery.advertised_address`, etc.).
- IP addresses can be added as additional SANs if necessary, but the FQDN must remain the primary name.

---

## 1. Standalone

A standalone deployment consists of a single Neo4j instance. One certificate/key pair is sufficient.

### Certificate Requirements

The certificate must include:

| Field | Value |
|---|---|
| **CN** | `neo4j.example.com` |
| **SAN** | `neo4j.example.com` (repeat the CN), optionally the LoadBalancer IP |

### Kubernetes Secret

```bash
kubectl create secret generic neo4j-ssl \
  --from-file=tls.crt=neo4j.example.com.crt \
  --from-file=tls.key=neo4j.example.com.key \
  --from-file=ca.crt=ca.crt \
  -n neo4j
```

### neo4j.conf (Helm values)

```yaml
config:
  dbms.ssl.policy.bolt.enabled: "true"
  dbms.ssl.policy.bolt.base_directory: "/ssl/bolt"
  dbms.ssl.policy.bolt.private_key: "private.key"
  dbms.ssl.policy.bolt.public_certificate: "public.crt"
  dbms.ssl.policy.bolt.trusted_dir: "/ssl/bolt/trusted"
  dbms.ssl.policy.bolt.client_auth: NONE

  dbms.ssl.policy.https.enabled: "true"
  dbms.ssl.policy.https.base_directory: "/ssl/https"
  dbms.ssl.policy.https.private_key: "private.key"
  dbms.ssl.policy.https.public_certificate: "public.crt"
  dbms.ssl.policy.https.trusted_dir: "/ssl/https/trusted"
  dbms.ssl.policy.https.client_auth: NONE
```

Mount the secret to `/ssl/bolt` and `/ssl/https` in the pod, placing:
- `public.crt` ← the signed certificate
- `private.key` ← the private key
- `trusted/ca.crt` ← the CA certificate (for client certificate validation if needed)

---

## 2. Cluster

A cluster is composed of multiple Neo4j instances that communicate with each other (Bolt + inter-cluster traffic) and are accessed by clients through a single entry point.

### Certificate Strategy

Two layers of naming are involved:

| Layer | Purpose | DNS name |
|---|---|---|
| **Cluster endpoint** | Single entry point for clients (LoadBalancer / Ingress) | `neo4j.example.com` |
| **Node FQDNs** | Each pod's individual address, required for intra-cluster TLS | `neo4j-0.neo4j.example.com`, `neo4j-1.neo4j.example.com`, `neo4j-2.neo4j.example.com` |

### Option A — Wildcard Certificate (recommended for Kubernetes)

A single wildcard certificate covers all nodes and the cluster endpoint.

```
CN  : neo4j.example.com
SAN : neo4j.example.com
      *.neo4j.example.com
```

This covers:
- `neo4j.example.com` — the cluster entry endpoint
- `neo4j-0.neo4j.example.com` — node 0
- `neo4j-1.neo4j.example.com` — node 1
- `neo4j-2.neo4j.example.com` — node 2

> **Note:** The wildcard `*` matches only one label. `*.neo4j.example.com` matches `neo4j-0.neo4j.example.com` but **not** `neo4j-0.core.neo4j.example.com`.

All nodes share the same certificate/key pair. This is acceptable unless your organisation policy mandates unique per-instance certificates.

### Option B — Individual Certificates per Node

Each node gets its own certificate. The cluster entry endpoint has a separate certificate.

```
# Cluster entry endpoint
CN  : neo4j.example.com
SAN : neo4j.example.com

# Node 0
CN  : neo4j-0.neo4j.example.com
SAN : neo4j-0.neo4j.example.com

# Node 1
CN  : neo4j-1.neo4j.example.com
SAN : neo4j-1.neo4j.example.com

# Node 2
CN  : neo4j-2.neo4j.example.com
SAN : neo4j-2.neo4j.example.com
```

This is more work but preferred in strict security environments.

### DNS Requirements

The following DNS records must exist before generating certificates:

```
neo4j.example.com           → <LoadBalancer IP>   # cluster entry
neo4j-0.neo4j.example.com   → <Pod/Node IP>       # node 0
neo4j-1.neo4j.example.com   → <Pod/Node IP>       # node 1
neo4j-2.neo4j.example.com   → <Pod/Node IP>       # node 2
```

With a headless Kubernetes Service named `neo4j` in namespace `neo4j`, the internal DNS names follow the pattern:
```
<pod-name>.<service-name>.<namespace>.svc.cluster.local
```
e.g. `neo4j-0.neo4j.neo4j.svc.cluster.local`

If using internal cluster DNS, include these as additional SANs.

### Kubernetes Secrets

```bash
# Wildcard (Option A) — one secret, shared by all pods
kubectl create secret generic neo4j-ssl \
  --from-file=tls.crt=wildcard.neo4j.example.com.crt \
  --from-file=tls.key=wildcard.neo4j.example.com.key \
  --from-file=ca.crt=ca.crt \
  -n neo4j

# Individual (Option B) — one secret per node
kubectl create secret generic neo4j-ssl-0 \
  --from-file=tls.crt=neo4j-0.neo4j.example.com.crt \
  --from-file=tls.key=neo4j-0.neo4j.example.com.key \
  --from-file=ca.crt=ca.crt \
  -n neo4j
```

### neo4j.conf (Helm values — cluster)

```yaml
config:
  # Advertised address must match the node's FQDN in the certificate
  server.default_advertised_address: "neo4j-0.neo4j.example.com"

  dbms.ssl.policy.bolt.enabled: "true"
  dbms.ssl.policy.bolt.base_directory: "/ssl/bolt"
  dbms.ssl.policy.bolt.private_key: "private.key"
  dbms.ssl.policy.bolt.public_certificate: "public.crt"
  dbms.ssl.policy.bolt.trusted_dir: "/ssl/bolt/trusted"
  dbms.ssl.policy.bolt.client_auth: NONE

  dbms.ssl.policy.cluster.enabled: "true"
  dbms.ssl.policy.cluster.base_directory: "/ssl/cluster"
  dbms.ssl.policy.cluster.private_key: "private.key"
  dbms.ssl.policy.cluster.public_certificate: "public.crt"
  dbms.ssl.policy.cluster.trusted_dir: "/ssl/cluster/trusted"
  dbms.ssl.policy.cluster.client_auth: REQUIRE
```

> The `cluster` SSL policy secures intra-cluster communication. Setting `client_auth: REQUIRE` enforces mutual TLS between cluster members.

---

## Summary

| Deployment | Certificates needed | Wildcard usable |
|---|---|---|
| **Standalone** | 1 — for the single node / endpoint | No need |
| **Cluster (Option A)** | 1 wildcard covering entry endpoint + all node FQDNs | Yes — `*.neo4j.example.com` |
| **Cluster (Option B)** | 1 per node + 1 for entry endpoint | No |
