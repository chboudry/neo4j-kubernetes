# Neo4j Kubernetes Network Architecture

> This document covers recommended network architectures for exposing Neo4j on Kubernetes, ordered from most to least recommended for production use.

---

## Quick Decision Guide

| | **Dev: Direct LB** | **Prod 1: Ingress TLS Termination** | **Prod 2: Ingress Passthrough** | **Prod 3: Reverse Proxy** | **Prod 4: TLS SNI (Envoy)** |
|---|---|---|---|---|---|
| **Complexity** | Low | Medium | Medium | Medium | High |
| **External ports** | 2 (7473, 7687) | 2 (443, 7687) | 2 (443, 7687) | 1 (443) | 1 (443) |
| **SSL/TLS location** | Neo4j native | Ingress | Neo4j native | Proxy | Ingress |
| **Driver support** | All | All | All | JS/WSS only | All |
| **Neo4j directly exposed** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Bolt support** | ✅ | ✅ | ✅ | ⚠️ WSS only | ✅ |
| **WAF / Rate limiting** | ❌ | ✅ | ❌ | ✅ | ✅ |

---

## Development: Direct LoadBalancer

The simplest way to get started. The Neo4j Helm chart creates a `LoadBalancer` service by default, which provisions a public IP directly to the Neo4j pod. Suitable for development and testing only.

**Do not use in production** — Neo4j is directly reachable from the internet, there is no TLS offloading, no WAF, and no centralized certificate management.

```mermaid
graph TB
    subgraph "Internet"
        Client[Client Browser/App]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Services"
            LB[LoadBalancer Service<br/>neo4j:neo4j]
        end
        subgraph "Pods"
            Neo4j[Neo4j Pod<br/>:7473 HTTPS<br/>:7687 Bolt]
        end
    end

    Client -->|HTTPS :7473| LB
    Client -->|Bolt :7687| LB
    LB -->|:7473| Neo4j
    LB -->|:7687| Neo4j

    style Client fill:#e1f5fe
    style LB fill:#f3e5f5
    style Neo4j fill:#e8f5e8
```

**Helm values:**
```yaml
# Default helm behavior — no change needed for dev
neo4j:
  services:
    neo4j:
      type: LoadBalancer
```

**Pros:**
- Zero configuration, works out of the box
- All drivers supported (native Bolt, no WebSocket wrapping)

**Cons:**
- Neo4j exposed directly to the internet
- Not suitable for production

---

## Production Option 1 — Ingress with TLS Termination ✅ Recommended

TLS is terminated at the Ingress Controller level. The Ingress decrypts traffic and forwards it in plaintext to Neo4j inside the cluster. Certificates are managed centrally via cert-manager.

This is the **recommended approach** for most production deployments on Kubernetes, as it follows standard cloud-native practices and integrates well with the existing Ingress ecosystem.

```mermaid
graph TB
    subgraph "Internet"
        Client[Client Browser/App]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Ingress"
            IC[Ingress Controller<br/>TLS Termination :443]
        end
        subgraph "Services"
            Neo4jHTTPS[ClusterIP Service<br/>neo4j-http :7474]
            Neo4jBolt[ClusterIP Service<br/>neo4j-bolt :7687]
        end
        subgraph "Pods"
            Neo4j[Neo4j Pod<br/>:7474 HTTP<br/>:7687 Bolt - plaintext]
        end
        subgraph "Certificate Management"
            CM[cert-manager]
        end
    end

    Client -->|HTTPS :443| IC
    Client -->|Bolt+TLS :7687| IC
    IC -->|HTTP :7474| Neo4jHTTPS
    IC -->|Bolt :7687| Neo4jBolt
    Neo4jHTTPS --> Neo4j
    Neo4jBolt --> Neo4j
    CM -.->|issues certs| IC

    style Client fill:#e1f5fe
    style IC fill:#e3f2fd
    style Neo4jHTTPS fill:#f3e5f5
    style Neo4jBolt fill:#f3e5f5
    style Neo4j fill:#e8f5e8
    style CM fill:#fff3e0
```

**Helm values:**
```yaml
neo4j:
  services:
    neo4j:
      type: ClusterIP  # disable direct public exposure

# Neo4j listens in plaintext internally
config:
  dbms.connector.https.enabled: "false"
  dbms.connector.http.enabled: "true"
  dbms.connector.bolt.tls_level: "DISABLED"
```

**Important:** Most HTTP Ingress controllers handle HTTPS natively, but Bolt (TCP) requires explicit TCP routing configuration. With Envoy Gateway or Traefik, a `TCPRoute` or `IngressRouteTCP` resource is needed.

**Pros:**
- Centralized certificate management with cert-manager and automatic rotation
- Neo4j not exposed directly to the internet
- Single entry point for the entire cluster
- WAF, rate limiting, and access policies can be applied at Ingress level
- All driver types supported (native Bolt, not limited to WebSocket)

**Cons:**
- Requires explicit TCP routing configuration for Bolt (not just a standard Ingress rule)
- Traffic between Ingress and Neo4j is unencrypted — acceptable if the cluster network is trusted, but requires attention in multi-tenant environments

---

## Production Option 2 — Ingress with TLS Passthrough

The Ingress forwards encrypted traffic as-is, without decrypting it. Neo4j handles TLS natively using its own certificates. This is a simpler alternative when you do not want to configure TCP termination at the Ingress level.

```mermaid
graph TB
    subgraph "Internet"
        Client[Client Browser/App]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Ingress"
            IC[Ingress Controller<br/>TCP Passthrough :443 / :7687]
        end
        subgraph "Services"
            Neo4jSvc[ClusterIP Service<br/>neo4j]
        end
        subgraph "Pods"
            Neo4j[Neo4j Pod<br/>:7473 HTTPS<br/>:7687 Bolt+TLS]
        end
    end

    Client -->|TLS :443 passthrough| IC
    Client -->|Bolt+TLS :7687 passthrough| IC
    IC --> Neo4jSvc
    Neo4jSvc --> Neo4j

    style Client fill:#e1f5fe
    style IC fill:#e3f2fd
    style Neo4jSvc fill:#f3e5f5
    style Neo4j fill:#e8f5e8
```

**Helm values:**
```yaml
neo4j:
  services:
    neo4j:
      type: ClusterIP

config:
  dbms.connector.https.enabled: "true"
  dbms.connector.bolt.tls_level: "REQUIRED"
  dbms.ssl.policy.bolt.enabled: "true"
  dbms.ssl.policy.https.enabled: "true"
```

**Pros:**
- End-to-end encryption — traffic is never decrypted outside the Neo4j pod
- Simpler Ingress configuration (no TCP termination needed)
- Neo4j remains autonomous regarding its own TLS stack
- Good fit for compliance requirements that mandate end-to-end encryption

**Cons:**
- Certificate management is done directly on Neo4j
- Certificate rotation must be handled per instance
- No possibility to apply WAF or L7 policies on Bolt traffic

---

## Production Option 3 — Reverse Proxy (WSS only)

Neo4j reverse proxy sits in front of Neo4j and handles SSL termination. Bolt is exposed over WebSocket Secure (WSS) on port 443 (reverse proxy).

> ⚠️ **Critical limitation :** WSS is only supported by the **JavaScript driver**. This covers Neo4j Browser, Bloom, and NeoDash. All other drivers (Python, Java, Go, .NET) and ETL tools use native Bolt and **will not work** through a reverse proxy. If your use case includes any non-JS client, do not use this option alone — see the Hybrid option below.


```mermaid
graph TB
    subgraph "Internet"
        Client[Web Browser<br/>Neo4j Browser / Bloom / NeoDash]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Services"
            RPLB[LoadBalancer Service<br/>reverse-proxy :443]
            Neo4jSvc[ClusterIP Service<br/>neo4j-internal]
        end
        subgraph "Pods"
            RP[Reverse Proxy Pod<br/>Nginx / Traefik]
            Neo4j[Neo4j Pod<br/>:7474 HTTP<br/>:7687 Bolt]
        end
    end

    Client -->|HTTPS :443| RPLB
    Client -->|WSS :443| RPLB
    RPLB --> RP
    RP -->|HTTP :7474| Neo4jSvc
    RP -->|Bolt over WSS :7687| Neo4jSvc
    Neo4jSvc --> Neo4j

    style Client fill:#e1f5fe
    style RPLB fill:#f3e5f5
    style RP fill:#fff3e0
    style Neo4jSvc fill:#f3e5f5
    style Neo4j fill:#e8f5e8
```

**Pros:**
- Single port (443) for both HTTPS and Bolt
- Good for web-only access (Browser, Bloom, NeoDash)

**Cons:**
- Only works for the JavaScript driver (WSS)
- Native Bolt drivers (Python, Java, Go, .NET, ETL tools) are not supported
- Not suitable as the sole access method if non-JS clients exist

**Hybrid variant:** If you need web access via reverse proxy *and* native Bolt for ETL or microservices, expose a separate `LoadBalancer` service for Bolt on a dedicated network or VPN:

> ⚠️ **Critical limitation:**  Neo4j reverse proxy only redirects to unsecured HTTP and Bolt. This means you won't be able to enforce TLS REQUIRED at Neo4j level but only as OPTIONAL : Reverse proxy will be unsecured while clients can **choose** wether or not to enforce SSL.

```mermaid
graph TB
    subgraph "Internet"
        WebClient[Web Browser]
    end
    subgraph "Dedicated Network / VPN"
        InternalApp[ETL / Microservices]
    end

    subgraph "Kubernetes Cluster"
        RPLB[LoadBalancer :443<br/>reverse-proxy]
        BoltLB[LoadBalancer :7687<br/>neo4j-bolt — internal network]
        RP[Reverse Proxy]
        Neo4j[Neo4j Pod]
        Neo4jSvc[ClusterIP neo4j-internal]
    end

    WebClient -->|HTTPS/WSS :443| RPLB
    InternalApp -->|Bolt :7687| BoltLB
    RPLB --> RP
    RP -->|HTTP/WSS| Neo4jSvc
    BoltLB --> Neo4j
    Neo4jSvc --> Neo4j

    style WebClient fill:#e1f5fe
    style InternalApp fill:#fff3e0
    style RPLB fill:#f3e5f5
    style BoltLB fill:#e8f5e8
    style RP fill:#fff3e0
    style Neo4jSvc fill:#f3e5f5
    style Neo4j fill:#e8f5e8
```

---

## Production Option 4 — TLS SNI with Envoy

A single port 443 serves both HTTPS and Bolt, with routing based on TLS SNI (Server Name Indication). Envoy inspects the SNI header of the TLS handshake — without decrypting the payload — and routes to the appropriate backend.

This requires DNS and valid certificates for both hostnames.

```mermaid
graph TB
    subgraph "Internet"
        Client[Client Browser/App]
    end

    subgraph "Kubernetes Cluster"
        subgraph "Envoy"
            IC[Envoy Gateway<br/>SNI routing :443]
        end
        subgraph "Services"
            Neo4jHTTPS[ClusterIP Service<br/>neo4j-https :7473]
            Neo4jBolt[ClusterIP Service<br/>neo4j-bolt :7687]
        end
        subgraph "Pods"
            Neo4j[Neo4j Pod<br/>:7473 HTTPS<br/>:7687 Bolt+TLS]
        end
        CM[cert-manager]
    end

    Client -->|TLS :443<br/>SNI: neo4j-web.domain.com| IC
    Client -->|TLS :443<br/>SNI: neo4j-bolt.domain.com| IC
    IC -->|:7473| Neo4jHTTPS
    IC -->|:7687| Neo4jBolt
    Neo4jHTTPS --> Neo4j
    Neo4jBolt --> Neo4j
    CM -.->|issues certs| IC

    style Client fill:#e1f5fe
    style IC fill:#e3f2fd
    style Neo4jHTTPS fill:#f3e5f5
    style Neo4jBolt fill:#f3e5f5
    style Neo4j fill:#e8f5e8
    style CM fill:#fff3e0
```

**Helm values:**
```yaml
neo4j:
  services:
    neo4j:
      type: ClusterIP

config:
  dbms.connector.https.enabled: "true"
  dbms.connector.bolt.tls_level: "REQUIRED"
  dbms.ssl.policy.bolt.enabled: "true"
  dbms.ssl.policy.https.enabled: "true"
```

**Pros:**
- Single port 443 (TCP) for all traffic
- All driver types supported (native Bolt, not limited to WebSocket)
- Fine-grained routing without decrypting payload
- cert-manager compatible
- Suitable for strict compliance environments (end-to-end encryption)

**Cons:**
- Requires DNS and valid certificates configured before deployment
- More complex to set up and operate than options 1 and 2
- Envoy (or a SNI-capable Ingress) required — not all Ingress controllers support SNI-based TCP routing

---

## Repository Structure

- `gke/` — Google Kubernetes Engine configurations
- `aks/` — Azure Kubernetes Service configurations  
- `local/` — Local cluster configurations (Docker Compose, kind, minikube)