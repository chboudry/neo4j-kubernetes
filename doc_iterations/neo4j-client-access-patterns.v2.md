# Neo4j Client Access Patterns (Enterprise / On‑Prem)

This document explains **how to expose Neo4j securely in enterprise environments** while staying flexible across customer constraints.
It focuses on:
- **Web vs Driver access** (HTTP/HTTPS vs Bolt)
- Two **complementary** enterprise patterns:
  - **Option 1: Front door + Neo4j-aware proxy** (max isolation, 443-only friendly)
  - **Option 2: Trusted subnet direct Bolt** (performance path inside a controlled network)

> Kubernetes terms (Ingress/Service) are implementation details. The patterns below apply to on‑prem, OpenShift, and cloud networks.

---

## 1) Protocols: what talks to what

### Web channel (HTTP/HTTPS)
Used to serve the web UI and web endpoints.

### Driver channel (Bolt)
Used by official drivers and `cypher-shell` (Bolt over TCP/TLS).

### Browser detail: Bolt over WebSocket
Browser-based clients can carry Bolt over **WebSocket** (WSS) because browsers can’t open raw TCP sockets.

```mermaid
flowchart LR
  B[Web browser\n(Browser/Bloom/NeoDash)] -->|HTTPS 443 + WSS| L7[LB7 / Ingress\nHTTP(S)+WebSocket]
  A[Backend apps\n(drivers, cypher-shell)] -->|Bolt TCP 7687| L4[LB4 / TCP exposure]
  L7 -->|HTTP/S + WS tunnel| N[Neo4j\nWeb 7473/7474\nBolt 7687]
  L4 -->|Bolt| N
```

PNG fallback: ![Protocols](./diagram-protocols.png)

---

## 2) Two complementary enterprise options (recommended together)

Many security-conscious enterprises use **both**:
- a **governed front door** for “everything that is not fully trusted” (users, tools, partners, 443-only zones),
- and a **direct Bolt path** for trusted applications inside an isolated subnet.

```mermaid
flowchart LR
  EXT[External/less-trusted clients\n443-only] -->|HTTPS 443| FD[Enterprise front door\nF5 / Gateway]
  FD -->|HTTPS 443| P[Neo4j-aware proxy (HA)\noptional]
  P -->|Bolt/HTTP internal| C[Neo4j cluster\ninternal]

  APP[Trusted app subnet] -->|Bolt TCP 7687| L4[Internal LB4 / TCP exposure\n(or direct routing)]
  L4 -->|Bolt| C
```

PNG fallback: ![Two options](./diagram-two-options.png)

---

## 3) Option 1 — Front door + Neo4j-aware proxy (max isolation)

**Goal:** keep **all cluster nodes private**, expose **one controlled entry point**, and satisfy **443-only** requirements.

Typical when:
- clients are outside the platform network (outside OpenShift / outside the DB subnet),
- security requires a single audited ingress point (TLS policy, allowlists, logging),
- exposing node endpoints is not acceptable.

**Pros**
- Minimizes exposed surface: one hostname / one entry point
- Strong governance: policy enforcement at the edge
- Avoids publishing internal addresses / ports

**Cons**
- Extra hop and component to operate (must be HA)
- Requires a Neo4j-aware proxy if you need to hide/transform routing details for clients

**Implementation notes**
- In Kubernetes, this maps well to the **Neo4j reverse-proxy chart** described in the official docs (routes HTTP vs Bolt and rewrites Bolt port to 80/443).  
  Reference: Neo4j “Accessing Neo4j using Kubernetes Ingress” (reverse proxy section).

---

## 4) Option 2 — Trusted subnet direct Bolt (performance path)

**Goal:** allow a *restricted* “trusted application zone” to connect directly to Bolt (TCP/TLS) without going through the front door.

Typical when:
- an application runs in a protected subnet/VLAN/VPC that is explicitly allowed to reach the DB subnet,
- you want the simplest / lowest-latency path for high-throughput workloads.

**Pros**
- Most direct path (best latency/throughput baseline)
- Fewer moving parts
- Aligns with classic DB patterns (drivers over TCP)

**Cons**
- Requires explicit network allowlisting between subnets
- Requires that whatever the driver learns from routing is reachable from that subnet (advertised addresses)

---

## 5) Decision guide (quick)

Use **Option 1** when:
- “443-only” is strict and clients are outside the platform network, and/or
- node endpoints must remain fully isolated.

Use **Option 2** when:
- a trusted application subnet can reach the DB subnet directly (strict firewall rules),
- you want a performance path without extra proxy hops.

Most large enterprises use **both**:
- **Option 1** for governed access,
- **Option 2** for specific trusted workloads.

---

## 6) Official references (Neo4j)

- Kubernetes ingress limitations for Bolt (Ingress is HTTP; cypher-shell expects TCP) and reverse proxy chart behavior:  
  https://neo4j.com/docs/operations-manual/current/kubernetes/accessing-neo4j-ingress/
- Ports & advertised addresses (routing reachability):  
  https://neo4j.com/docs/operations-manual/current/configuration/ports/
- Bolt transport over TCP or WebSocket:  
  https://neo4j.com/docs/bolt/current/bolt/
- JS driver usage in browser (WebSockets):  
  https://neo4j.com/docs/javascript-manual/current/browser-websockets/
