# Metrics

Neo4j supports multiple ways to expose metrics. The full list of available options is documented in the [official documentation](https://neo4j.com/docs/operations-manual/current/monitoring/metrics/expose/).

This guide focuses on the **Prometheus** integration.

The principle is straightforward. Prometheus uses a **pull model**: Neo4j is configured to expose a `/metrics` endpoint on a dedicated port, typically exposed through the `neo4j-admin` Kubernetes service, using the Prometheus exposition format.

Prometheus then scrapes this endpoint at regular intervals to collect metrics. The collected data can subsequently be visualized in tools such as Grafana.

# Logs

## Strategy

Two collection strategies are available: Sidecar and DaemonSet.

DaemonSet is the platform standard for collecting `stdout`/`stderr` logs. 

However, Neo4j exposes startup/runtime logs through stdout/stderr, but detailed operational logs
(e.g. `query.log`, `debug.log`, `security.log`) are written to `/logs`.

For DaemonSets, collecting logs directly from `/logs` is more complex:
the storage backend must allow simultaneous access from Neo4j and the log collector. In Kubernetes, this generally means using a PersistentVolume with the `ReadWriteMany` (`RWX`) access mode. This becomes more complex when multiple Neo4j pods are scheduled on the same node,
as the collector must correctly map each log directory to the corresponding instance.

Solution will then depend on your need:

| Strategy | Use when you need |
| -------- | ----------------- |
| **DaemonSet** | Kubernetes-standard logging, startup/runtime diagnostics, crash investigation, main error visibility |
| **Sidecar** | Cypher audit, slow query analysis, forensic / cluster debug, security investigation, advanced troubleshooting |

### Sidecar

A dedicated log collector container runs alongside the Neo4j container in the same pod, sharing the `/logs` volume directly.

| Pros | Cons |
| ---- | ---- |
| Direct access to the `/logs` volume | One collector per pod — higher CPU/RAM overhead |
| Instance-specific configuration | Costs scale with Neo4j replicas |
| Easy to add Neo4j-specific parsers and filters | Configuration managed inside the Neo4j chart, share the same lifecycle |
| No dependency on the platform team | Can impact the pod if under-resourced |

### DaemonSet

A single log collector agent runs on each Kubernetes node and collects logs from all pods on that node.

| Pros | Cons |
| ---- | ---- |
| One agent per node — less resource duplication | Requires volume/node-level log access |
| Platform standard (Fluent Bit, Fluentd, Logstash) | Less Neo4j-specific |
| Centralized for all workloads | More dependent on the platform team |
| Clear separation between app and observability | Multi-tenant — configuration is more generic |

## Tools

The same deployment models apply to Fluentd, Fluent Bit, Filebeat, Logstash, or Elastic Agent:
they can run either as sidecar containers or as DaemonSets.

In practice, lightweight collectors such as Fluent Bit, Filebeat, or Elastic Agent are commonly used as DaemonSets
for Kubernetes-wide log collection.

Fluentd and Logstash are more often used when advanced parsing, enrichment, routing,
or centralized log processing pipelines are required, whether as sidecars or centralized services.

Then these collectors typically forward logs to specialized log storage and analysis platforms such as Loki, Elasticsearch/OpenSearch, Splunk, or other centralized observability systems.


