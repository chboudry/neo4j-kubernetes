# Neo4j Kubernetes Network Configurations (clarified)

This page documents common ways to expose **Neo4j Web (HTTP/HTTPS)** and **Neo4j Drivers (Bolt)** from Kubernetes.
It aims to avoid the most common confusion: **Web access ≠ Bolt access**, and **browser clients ≠ backend drivers**.

> Terminology note: Kubernetes **Ingress** is an **HTTP(S) router** (Layer 7). It is not a generic TCP router.

---

## 0) Quick mental model (web clients vs backend drivers)

- **Web clients** (Neo4j Browser / Bloom / NeoDash in a web browser) use:
  - **HTTPS** to load the UI, and
  - often **WSS (WebSocket)** to carry Bolt from inside the browser (because browsers can't open raw TCP sockets).
- **Backend drivers** (Python/Java/Go/.NET, cypher-shell) typically use **Bolt over TCP/TLS**.

```mermaid
flowchart LR
  WEB[Web clients\n(Browser/Bloom/NeoDash)] -->|HTTPS 443 + WSS| L7[LB7 / Ingress\n(HTTP/S + WebSocket)]
  APP[Backend apps\n(Python/Java/Go/.NET drivers)] -->|Bolt TCP 7687| L4[LB4 (TCP)]
  L7 -->|HTTP/S (+WS tunnel)| N[Neo4j\nWeb 7473/7474 + Bolt 7687]
  L4 -->|Bolt TCP| N
```

PNG fallback: ![Web vs drivers](./diagram-a-web-vs-drivers.png)

---

## 1) Simple configuration — Direct Load Balancer (LB4 + LB7 via Service)

**Features**
- Direct access to Neo4j ports via `Service type: LoadBalancer` (or external LB)
- Port **7473** for **HTTPS** web interface (Neo4j UI / web endpoints)
- Port **7687** for **Bolt** connections (drivers, cypher-shell)
- Simplest configuration (also easiest to troubleshoot)

```mermaid
graph TB
  subgraph Internet
    Client[Client (Browser or App)]
  end

  subgraph Kubernetes Cluster
    LB[Service type LoadBalancer]
    Neo4j[Neo4j Pod/Service\n:7473 HTTPS\n:7687 Bolt]
  end

  Client -->|HTTPS :7473| LB
  Client -->|Bolt :7687| LB
  LB --> Neo4j
```

PNG fallback: ![Direct LB](./diagram-1-direct-lb.png)

---

## 2) Reverse proxy for **Web UI** (and WebSocket for browser clients)

This pattern is commonly used to expose **web UI** on a single standard port (**443**).
It can also support **WSS** (WebSocket upgrade) so that browser-based tools (Browser/Bloom/NeoDash) can talk to Neo4j.

**Important clarification**
- This pattern **does not** make backend drivers use WSS.
- Backend drivers usually still require **Bolt TCP** (or an alternative such as Query API).
- If you want to expose Bolt TCP without a separate LB4, you typically need either:
  - a TCP-capable exposure (LB4 / TCP services), or
  - a dedicated “Neo4j reverse-proxy” component that rewrites Bolt addresses/ports (see official docs).

**Features**
- SSL termination at proxy/LB7 level (optional)
- Supports WebSocket upgrade for browser clients
- Neo4j service can remain `ClusterIP` (internal)

```mermaid
flowchart TB
  WEB[Web clients\n(Browser/Bloom/NeoDash)] -->|HTTPS/WSS :443| L7[LB7 / Reverse proxy\n(HTTP/S + WS)]
  L7 -->|HTTP/S + WS tunnel| N[Neo4j\n7473 HTTPS\n7687 Bolt]

  APP[Backend apps\n(drivers)] -->|Bolt TCP :7687| L4[LB4 (TCP)\n(or TCP services mapping)]
  L4 -->|Bolt TCP| N
```

PNG fallback: ![Reverse proxy for web + WS](./diagram-2-reverse-proxy-web-ws.png)

---

## 3) TLS SNI on port 443 (advanced TCP routing)

Goal: use a **single port (443)** and route traffic to either:
- **Neo4j Web** (HTTPS) or
- **Neo4j Bolt** (Bolt over TCP/TLS)

based on **TLS SNI** (different hostnames).

**Notes**
- This requires **DNS + certificates** (SNI is evaluated during TLS handshake).
- This is not Kubernetes `Ingress` (HTTP). It typically uses a TCP/TLS router (e.g., NGINX *stream* or HAProxy).

```mermaid
flowchart TB
  C[Client] -->|TLS :443\nSNI: neo4j-web.example.com| SNI[TCP/TLS router\n(SNI-based)]
  C -->|TLS :443\nSNI: neo4j-bolt.example.com| SNI
  SNI -->|to 7473| WEB[Neo4j Web service]
  SNI -->|to 7687| BOLT[Neo4j Bolt service]
```

PNG fallback: ![TLS SNI](./diagram-3-tls-sni.png)

---

## 4) Hybrid configuration — Reverse proxy for web + direct Bolt for internal apps

**Use when**
- You want to expose **web UI** to the internet (443, web-friendly),
- and you want **direct Bolt** for internal apps/ETL over a dedicated network/VPN.

**Features**
- Web interface through LB7/reverse proxy for internet access
- Direct Bolt access via LB4 for internal applications
- Clear separation between public web access and internal driver access

```mermaid
flowchart TB
  WEB[Internet users\n(Web UI)] -->|HTTPS/WSS :443| L7[LB7 / Reverse proxy]
  INT[Internal apps\n(Drivers)] -->|Bolt TCP :7687| L4[LB4 (TCP)]
  L7 -->|HTTP/S + WS tunnel| N[Neo4j\n7473 HTTPS\n7687 Bolt]
  L4 -->|Bolt TCP| N
```

PNG fallback: ![Hybrid](./diagram-4-hybrid.png)

---

## Approaches comparison (balanced)

| Aspect | Direct LB (7473+7687) | LB7 for Web + LB4 for Bolt | TLS SNI (443) | Hybrid |
|---|---|---|---|---|
| Complexity | Low | Medium | High | Medium-High |
| External ports | 2 (7473, 7687) | 2 (443 + 7687) | 1 (443) | 2 (443, 7687) |
| Web access | Direct | Via LB7 | Via SNI route | Via LB7 |
| Driver access | Direct | Via LB4 | Via SNI route | Via LB4 |
| Fits “443-only” networks | No | Sometimes | Yes (if allowed) | Sometimes |
| Main risk | Port governance | More components | Operational complexity | More components |

---

## Official references
- Neo4j on Kubernetes: accessing via Ingress (Ingress is HTTP; cypher-shell expects TCP; TCP services mapping):  
  https://neo4j.com/docs/operations-manual/current/kubernetes/accessing-neo4j-ingress/
- Neo4j ports & advertised addresses (why “addresses must be reachable” matters for routing):  
  https://neo4j.com/docs/operations-manual/current/configuration/ports/
- Bolt protocol transport (Bolt over TCP or WebSocket):  
  https://neo4j.com/docs/bolt/current/bolt/
- JavaScript driver in browser (WebSockets):  
  https://neo4j.com/docs/javascript-manual/current/browser-websockets/
