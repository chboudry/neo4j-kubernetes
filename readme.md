# Neo4j Kubernetes Configurations

This repository contains different configurations for deploying Neo4j on Kubernetes with multiple network approaches.


**Note:**
- HTTPS server and Bolt access are on the same pod but they also can be split

## 1. Simple Configuration - Direct Load Balancer

**Features:**

- Direct access to Neo4j ports via LoadBalancer service
- Port 7474 for HTTPS web interface
- Port 7687 for Bolt connections
- Simplest configuration

```mermaid
graph TB
    subgraph "Internet"
        Client[Client Browser/App]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "Services"
            LB[LoadBalancer Service<br/>Neo4j:neo4j]
        end
        
        subgraph "Pods"
            Neo4j[Neo4j Pod<br/>:7474 HTTPS<br/>:7687 Bolt]
        end
    end
    
    Client -->|HTTPS :7474| LB
    Client -->|Bolt :7687| LB
    LB -->|:7474| Neo4j
    LB -->|:7687| Neo4j
    
    style Client fill:#e1f5fe
    style LB fill:#f3e5f5
    style Neo4j fill:#e8f5e8
```

## 2. Reverse Proxy Configuration

**This works only for javascript driver which is the only one to support web socket and applications built on top of it : Neo4j Browser, Bloom, NeoDash.**

Other drivers and applications built on top of it (any ETL components) do not use wss but direct neo4j/bolt access.


**Features:**
- Reverse proxy for intelligent routing
- SSL termination at proxy level
- WebSocket Secure (WSS) for Bolt : 
- Neo4j service as ClusterIP (internal)

```mermaid
graph TB
    subgraph "Internet"
        Client[Client Browser/App]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "Services"
            RPLB[LoadBalancer Service<br/>reverse-proxy]
            Neo4jSvc[ClusterIP Service<br/>Neo4j:default ]
        end
        
        subgraph "Pods"
            RP[Reverse Proxy Pod<br/>nginx/traefik]
            Neo4j[Neo4j Pod<br/>:7474 HTTPS<br/>:7687 Bolt]
        end
    end
    
    Client -->|HTTPS :443| RPLB
    Client -->|WSS :443| RPLB
    RPLB --> RP
    RP -->|HTTP/HTTPS :7474| Neo4jSvc
    RP -->|Bolt over WSS :7687| Neo4jSvc
    Neo4jSvc --> Neo4j
    
    style Client fill:#e1f5fe
    style RPLB fill:#f3e5f5
    style RP fill:#fff3e0
    style Neo4jSvc fill:#f3e5f5
    style Neo4j fill:#e8f5e8
```


## 3. TLS SNI Configuration with Nginx Controller

We are using a single port (443) to access both HTTPS and Bolt. This is only possible with a Ingress Controller that support TLS SNI.

This also implies you can't set up this configuration without certificates and DNS.

**Features:**
- Ingress Controller with TLS SNI (example are with nginx)
- Host-based routing (SNI)
- Single port 443 for both services
- Separation of HTTPS and Bolt services



```mermaid
graph TB
    subgraph "Internet"
        Client[Client Browser/App]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "Ingress"
            IC[Nginx Ingress Controller<br/>TLS SNI :443]
        end
        
        subgraph "Services"
            Neo4jHTTPS[ClusterIP Service<br/>neo4j-https-svc<br/>:7474]
            Neo4jBolt[ClusterIP Service<br/>neo4j-bolt-svc<br/>:7687]
        end
        
        subgraph "Pods"
            Neo4j[Neo4j Pod<br/>:7474 HTTPS<br/>:7687 Bolt]
        end
        
        subgraph "Ingress Rules"
            HTTPSRule[HTTPS Ingress<br/>neo4j-web.domain.com]
            BoltRule[TCP Ingress<br/>neo4j-bolt.domain.com]
        end
    end
    
    Client -->|HTTPS :443<br/>Host: neo4j-web.domain.com| IC
    Client -->|Bolt :443<br/>Host: neo4j-bolt.domain.com| IC
    
    IC --> HTTPSRule
    IC --> BoltRule
    
    HTTPSRule -->|:7474| Neo4jHTTPS
    BoltRule -->|:7687| Neo4jBolt
    
    Neo4jHTTPS --> Neo4j
    Neo4jBolt --> Neo4j
    
    style Client fill:#e1f5fe
    style IC fill:#e3f2fd
    style HTTPSRule fill:#f1f8e9
    style BoltRule fill:#f1f8e9
    style Neo4jHTTPS fill:#f3e5f5
    style Neo4jBolt fill:#f3e5f5
    style Neo4j fill:#e8f5e8
```

## 4. Hybrid Configuration - Reverse Proxy + Direct Bolt Access

**Best of both worlds: Web interface through reverse proxy for internet access, direct Bolt access for internal applications and dedicated networks.**

**This may be ideal if you want to provide access to Neo4j Browser, Bloom and Neodash through Internet, and need bolt port for ETL components or other applications/services using neo4j drivers.**

**Keep in mind database IS accessible through wss, so security is identity.**

**Features:**
- Reverse proxy for HTTPS web interface (internet access)
- Direct Bolt access via dedicated service for internal applications
- Support for all driver types (not limited to WebSocket)
- Ideal for ETL processes and internal microservices
- Clear separation between public web access and internal data access

```mermaid
graph TB
    subgraph "Internet"
        WebClient[Web Browser<br/>Neo4j Browser/Bloom]
    end
    
    subgraph "Dedicated Network/VPN"
        InternalApp[Internal Applications<br/>ETL/Microservices]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "Services"
            RPLB[LoadBalancer Service<br/>reverse-proxy<br/>:443]
            BoltLB[LoadBalancer Service<br/>neo4j-bolt<br/>:7687]
            Neo4jSvc[ClusterIP Service<br/>neo4j-internal]
        end
        
        subgraph "Pods"
            RP[Reverse Proxy Pod<br/>nginx/traefik]
            Neo4j[Neo4j Pod<br/>:7474 HTTPS<br/>:7687 Bolt]
        end
        
        subgraph "Internal Cluster"
            ClusterApp[Internal Pod<br/>Same Cluster App]
        end
    end
    
    WebClient -->|HTTPS :443| RPLB
    InternalApp -->|Bolt :7687| BoltLB
    ClusterApp -->|Bolt :7687| Neo4jSvc
    
    RPLB --> RP
    RP -->|HTTP/HTTPS :7474| Neo4jSvc
    BoltLB -->|:7687| Neo4j
    Neo4jSvc --> Neo4j
    
    style WebClient fill:#e1f5fe
    style InternalApp fill:#fff3e0
    style ClusterApp fill:#f3e5f5
    style RPLB fill:#f3e5f5
    style BoltLB fill:#e8f5e8
    style RP fill:#fff3e0
    style Neo4jSvc fill:#f3e5f5
    style Neo4j fill:#e8f5e8
```

**Use Cases:**
- **Web Interface**: Accessible from internet via reverse proxy (HTTPS only)
- **ETL Processes**: Direct Bolt access from dedicated network/VPN
- **Internal Services**: Direct cluster-internal access via ClusterIP
- **Monitoring Tools**: Can use either access method based on deployment location

## Approaches Comparison

| Aspect | Simple LB | Reverse Proxy | TLS SNI | Hybrid |
|--------|-----------|---------------|---------|---------|
| **Complexity** | Low | Medium | High | Medium-High |
| **External ports** | 2 (7474, 7687) | 1 (443) | 1 (443) | 2 (443, 7687) |
| **SSL/TLS** | Neo4j native | Proxy termination | Ingress termination | Mixed |
| **Routing** | Direct | Path/header based | SNI based | Mixed |
| **Scalability** | Limited | Good | Excellent | Excellent |
| **Driver support** | All | JS only (WSS) | All | All |
| **Use case** | Dev/Test | Web-only prod | Complex production | Enterprise production |

## Repository Structure

- `gke/` - Google Kubernetes Engine specific configurations
- `aks/` - Azure Kubernetes Service specific configurations
- `local/` - Local cluster configurations
- `neo4j/` - Custom Neo4j Helm charts