# Supported Diagram Types

## High-Level Overview

**Command:** `azure-diagrammer run --type high-level`

Shows subscriptions, resource groups, regions, and resource counts by type. Resources are summarized (e.g., "3 VMs", "2 SQL DBs") rather than shown individually.

**Use cases:**
- Executive presentations
- Project overviews
- Multi-subscription environment maps

**Layout:** Grid — subscriptions as rows, resource groups in columns.

---

## Network Topology

**Command:** `azure-diagrammer run --type network`

Shows VNets, subnets, peerings, NSGs, load balancers, application gateways, firewalls, private endpoints, and public IPs.

**Use cases:**
- Network architecture review
- Security audit documentation
- Connectivity troubleshooting

**Layout:** Hierarchical top-down — VNets at top, subnets below, resources inside subnets. Hub-spoke detected automatically.

**Details shown:**
- VNet address spaces
- Subnet CIDR ranges
- VNet peering connections (bidirectional dashed lines)
- NSG associations (annotated on subnet boundaries)
- Private endpoint connections to PaaS services

---

## Application Architecture

**Command:** `azure-diagrammer run --type app`

Shows application services, functions, VMs, databases, storage, caches, messaging, and API management grouped by logical tier.

**Use cases:**
- Application design review
- Onboarding documentation
- Architecture decision records

**Layout:** Left-to-right flow — Ingress → Compute → Integration → Data

**Tiers:**
| Tier | Resource Types |
|------|---------------|
| Ingress | App Gateway, Front Door, Load Balancer, Firewall, WAF, APIM |
| Compute | VMs, VMSS, App Services, Functions, AKS, Container Instances |
| Integration | Service Bus, Event Hub, Event Grid, Logic Apps |
| Data | SQL, Cosmos DB, Storage, Redis Cache |

---

## Data Flow

**Command:** `azure-diagrammer run --type dataflow`

Shows directional arrows indicating data movement between resources with protocol and port annotations.

**Use cases:**
- Compliance documentation
- Data governance review
- Network traffic analysis

**Layout:** Left-to-right with swim lanes by flow type.

**Data sources:**
- NSG allow rules (port-based traffic patterns)
- Private endpoint connections (secure PaaS connectivity)
- VNet service endpoints
- Diagnostic settings (log/metric flow)

---

## All Diagrams

**Command:** `azure-diagrammer run --type all`

Generates all four diagram types in a single document (multi-page for Lucidchart and Draw.io, multiple sections for Mermaid).
