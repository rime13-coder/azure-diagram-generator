"""Azure resource type mappings, icons, and visual properties.

Maps Azure resource provider types to display metadata used for
diagram rendering (display names, icons, colors, categories).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResourceCategory(str, Enum):
    """Visual category for Azure resources."""

    COMPUTE = "compute"
    NETWORKING = "networking"
    DATA = "data"
    STORAGE = "storage"
    SECURITY = "security"
    INTEGRATION = "integration"
    MONITORING = "monitoring"
    IDENTITY = "identity"
    CONTAINER = "container"  # Group/container elements (subscriptions, RGs, VNets)
    OTHER = "other"


@dataclass(frozen=True)
class AzureResourceMeta:
    """Visual and categorical metadata for an Azure resource type."""

    display_name: str
    short_name: str
    category: ResourceCategory
    icon_file: str  # Filename in the icons/azure/ directory
    fill_color: str  # Hex fill color for shapes
    stroke_color: str  # Hex stroke/border color
    is_container: bool = False  # Whether this renders as a group/container
    default_width: float = 120.0
    default_height: float = 80.0


# Brand colors by category
CATEGORY_COLORS = {
    ResourceCategory.COMPUTE: ("#0078D4", "#005A9E"),
    ResourceCategory.NETWORKING: ("#44B8B1", "#2D8A85"),
    ResourceCategory.DATA: ("#E8590C", "#C44B0A"),
    ResourceCategory.STORAGE: ("#0063B1", "#004E8C"),
    ResourceCategory.SECURITY: ("#E3008C", "#B8006F"),
    ResourceCategory.INTEGRATION: ("#8661C5", "#6B4FA0"),
    ResourceCategory.MONITORING: ("#00B7C3", "#009AA3"),
    ResourceCategory.IDENTITY: ("#FFB900", "#D69E00"),
    ResourceCategory.CONTAINER: ("#E6E6E6", "#999999"),
    ResourceCategory.OTHER: ("#B4B4B4", "#808080"),
}

# Comprehensive Azure resource type -> metadata mapping
AZURE_RESOURCE_MAP: dict[str, AzureResourceMeta] = {
    # ── Compute ──────────────────────────────────────────────
    "microsoft.compute/virtualmachines": AzureResourceMeta(
        display_name="Virtual Machine",
        short_name="VM",
        category=ResourceCategory.COMPUTE,
        icon_file="vm.svg",
        fill_color="#0078D4",
        stroke_color="#005A9E",
    ),
    "microsoft.compute/virtualmachinescalesets": AzureResourceMeta(
        display_name="VM Scale Set",
        short_name="VMSS",
        category=ResourceCategory.COMPUTE,
        icon_file="vmss.svg",
        fill_color="#0078D4",
        stroke_color="#005A9E",
    ),
    "microsoft.web/sites": AzureResourceMeta(
        display_name="App Service",
        short_name="App",
        category=ResourceCategory.COMPUTE,
        icon_file="app-service.svg",
        fill_color="#0078D4",
        stroke_color="#005A9E",
    ),
    "microsoft.web/serverfarms": AzureResourceMeta(
        display_name="App Service Plan",
        short_name="ASP",
        category=ResourceCategory.COMPUTE,
        icon_file="app-service-plan.svg",
        fill_color="#0078D4",
        stroke_color="#005A9E",
        is_container=True,
        default_width=300.0,
        default_height=200.0,
    ),
    "microsoft.web/sites/functions": AzureResourceMeta(
        display_name="Function App",
        short_name="Func",
        category=ResourceCategory.COMPUTE,
        icon_file="function-app.svg",
        fill_color="#0078D4",
        stroke_color="#005A9E",
    ),
    "microsoft.containerservice/managedclusters": AzureResourceMeta(
        display_name="AKS Cluster",
        short_name="AKS",
        category=ResourceCategory.COMPUTE,
        icon_file="aks.svg",
        fill_color="#0078D4",
        stroke_color="#005A9E",
    ),
    "microsoft.containerinstance/containergroups": AzureResourceMeta(
        display_name="Container Instance",
        short_name="ACI",
        category=ResourceCategory.COMPUTE,
        icon_file="container-instance.svg",
        fill_color="#0078D4",
        stroke_color="#005A9E",
    ),
    "microsoft.containerregistry/registries": AzureResourceMeta(
        display_name="Container Registry",
        short_name="ACR",
        category=ResourceCategory.COMPUTE,
        icon_file="container-registry.svg",
        fill_color="#0078D4",
        stroke_color="#005A9E",
    ),
    # ── Networking ───────────────────────────────────────────
    "microsoft.network/virtualnetworks": AzureResourceMeta(
        display_name="Virtual Network",
        short_name="VNet",
        category=ResourceCategory.NETWORKING,
        icon_file="vnet.svg",
        fill_color="#CCEEFF",
        stroke_color="#44B8B1",
        is_container=True,
        default_width=500.0,
        default_height=400.0,
    ),
    "microsoft.network/virtualnetworks/subnets": AzureResourceMeta(
        display_name="Subnet",
        short_name="Subnet",
        category=ResourceCategory.NETWORKING,
        icon_file="subnet.svg",
        fill_color="#E8F5FF",
        stroke_color="#44B8B1",
        is_container=True,
        default_width=300.0,
        default_height=200.0,
    ),
    "microsoft.network/networkinterfaces": AzureResourceMeta(
        display_name="Network Interface",
        short_name="NIC",
        category=ResourceCategory.NETWORKING,
        icon_file="nic.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
        default_width=80.0,
        default_height=60.0,
    ),
    "microsoft.network/publicipaddresses": AzureResourceMeta(
        display_name="Public IP",
        short_name="PIP",
        category=ResourceCategory.NETWORKING,
        icon_file="public-ip.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/loadbalancers": AzureResourceMeta(
        display_name="Load Balancer",
        short_name="LB",
        category=ResourceCategory.NETWORKING,
        icon_file="load-balancer.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/applicationgateways": AzureResourceMeta(
        display_name="Application Gateway",
        short_name="AppGW",
        category=ResourceCategory.NETWORKING,
        icon_file="app-gateway.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/azurefirewalls": AzureResourceMeta(
        display_name="Azure Firewall",
        short_name="FW",
        category=ResourceCategory.NETWORKING,
        icon_file="firewall.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/networksecuritygroups": AzureResourceMeta(
        display_name="Network Security Group",
        short_name="NSG",
        category=ResourceCategory.SECURITY,
        icon_file="nsg.svg",
        fill_color="#E3008C",
        stroke_color="#B8006F",
    ),
    "microsoft.network/privateendpoints": AzureResourceMeta(
        display_name="Private Endpoint",
        short_name="PE",
        category=ResourceCategory.NETWORKING,
        icon_file="private-endpoint.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/virtualnetworkgateways": AzureResourceMeta(
        display_name="VNet Gateway",
        short_name="VPN GW",
        category=ResourceCategory.NETWORKING,
        icon_file="vpn-gateway.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/expressroutecircuits": AzureResourceMeta(
        display_name="ExpressRoute",
        short_name="ER",
        category=ResourceCategory.NETWORKING,
        icon_file="expressroute.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/dnszones": AzureResourceMeta(
        display_name="DNS Zone",
        short_name="DNS",
        category=ResourceCategory.NETWORKING,
        icon_file="dns-zone.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/trafficmanagerprofiles": AzureResourceMeta(
        display_name="Traffic Manager",
        short_name="TM",
        category=ResourceCategory.NETWORKING,
        icon_file="traffic-manager.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/frontdoors": AzureResourceMeta(
        display_name="Front Door",
        short_name="AFD",
        category=ResourceCategory.NETWORKING,
        icon_file="front-door.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    "microsoft.network/routetables": AzureResourceMeta(
        display_name="Route Table",
        short_name="UDR",
        category=ResourceCategory.NETWORKING,
        icon_file="route-table.svg",
        fill_color="#44B8B1",
        stroke_color="#2D8A85",
    ),
    # ── Data / Databases ─────────────────────────────────────
    "microsoft.sql/servers": AzureResourceMeta(
        display_name="SQL Server",
        short_name="SQL",
        category=ResourceCategory.DATA,
        icon_file="sql-server.svg",
        fill_color="#E8590C",
        stroke_color="#C44B0A",
    ),
    "microsoft.sql/servers/databases": AzureResourceMeta(
        display_name="SQL Database",
        short_name="SQL DB",
        category=ResourceCategory.DATA,
        icon_file="sql-database.svg",
        fill_color="#E8590C",
        stroke_color="#C44B0A",
    ),
    "microsoft.documentdb/databaseaccounts": AzureResourceMeta(
        display_name="Cosmos DB",
        short_name="Cosmos",
        category=ResourceCategory.DATA,
        icon_file="cosmos-db.svg",
        fill_color="#E8590C",
        stroke_color="#C44B0A",
    ),
    "microsoft.dbformysql/flexibleservers": AzureResourceMeta(
        display_name="MySQL Flexible Server",
        short_name="MySQL",
        category=ResourceCategory.DATA,
        icon_file="mysql.svg",
        fill_color="#E8590C",
        stroke_color="#C44B0A",
    ),
    "microsoft.dbforpostgresql/flexibleservers": AzureResourceMeta(
        display_name="PostgreSQL Flexible Server",
        short_name="PgSQL",
        category=ResourceCategory.DATA,
        icon_file="postgresql.svg",
        fill_color="#E8590C",
        stroke_color="#C44B0A",
    ),
    "microsoft.cache/redis": AzureResourceMeta(
        display_name="Redis Cache",
        short_name="Redis",
        category=ResourceCategory.DATA,
        icon_file="redis-cache.svg",
        fill_color="#E8590C",
        stroke_color="#C44B0A",
    ),
    # ── Storage ──────────────────────────────────────────────
    "microsoft.storage/storageaccounts": AzureResourceMeta(
        display_name="Storage Account",
        short_name="Storage",
        category=ResourceCategory.STORAGE,
        icon_file="storage-account.svg",
        fill_color="#0063B1",
        stroke_color="#004E8C",
    ),
    # ── Security ─────────────────────────────────────────────
    "microsoft.keyvault/vaults": AzureResourceMeta(
        display_name="Key Vault",
        short_name="KV",
        category=ResourceCategory.SECURITY,
        icon_file="key-vault.svg",
        fill_color="#E3008C",
        stroke_color="#B8006F",
    ),
    "microsoft.network/applicationgatewaywebapplicationfirewallpolicies": AzureResourceMeta(
        display_name="WAF Policy",
        short_name="WAF",
        category=ResourceCategory.SECURITY,
        icon_file="waf.svg",
        fill_color="#E3008C",
        stroke_color="#B8006F",
    ),
    # ── Integration ──────────────────────────────────────────
    "microsoft.servicebus/namespaces": AzureResourceMeta(
        display_name="Service Bus",
        short_name="SB",
        category=ResourceCategory.INTEGRATION,
        icon_file="service-bus.svg",
        fill_color="#8661C5",
        stroke_color="#6B4FA0",
    ),
    "microsoft.eventhub/namespaces": AzureResourceMeta(
        display_name="Event Hub",
        short_name="EH",
        category=ResourceCategory.INTEGRATION,
        icon_file="event-hub.svg",
        fill_color="#8661C5",
        stroke_color="#6B4FA0",
    ),
    "microsoft.eventgrid/topics": AzureResourceMeta(
        display_name="Event Grid Topic",
        short_name="EG",
        category=ResourceCategory.INTEGRATION,
        icon_file="event-grid.svg",
        fill_color="#8661C5",
        stroke_color="#6B4FA0",
    ),
    "microsoft.apimanagement/service": AzureResourceMeta(
        display_name="API Management",
        short_name="APIM",
        category=ResourceCategory.INTEGRATION,
        icon_file="api-management.svg",
        fill_color="#8661C5",
        stroke_color="#6B4FA0",
    ),
    "microsoft.logic/workflows": AzureResourceMeta(
        display_name="Logic App",
        short_name="Logic",
        category=ResourceCategory.INTEGRATION,
        icon_file="logic-app.svg",
        fill_color="#8661C5",
        stroke_color="#6B4FA0",
    ),
    # ── Monitoring ───────────────────────────────────────────
    "microsoft.insights/components": AzureResourceMeta(
        display_name="Application Insights",
        short_name="AppIns",
        category=ResourceCategory.MONITORING,
        icon_file="app-insights.svg",
        fill_color="#00B7C3",
        stroke_color="#009AA3",
    ),
    "microsoft.operationalinsights/workspaces": AzureResourceMeta(
        display_name="Log Analytics",
        short_name="LA",
        category=ResourceCategory.MONITORING,
        icon_file="log-analytics.svg",
        fill_color="#00B7C3",
        stroke_color="#009AA3",
    ),
    # ── Identity ─────────────────────────────────────────────
    "microsoft.managedidentity/userassignedidentities": AzureResourceMeta(
        display_name="Managed Identity",
        short_name="MI",
        category=ResourceCategory.IDENTITY,
        icon_file="managed-identity.svg",
        fill_color="#FFB900",
        stroke_color="#D69E00",
    ),
}

# Default metadata for unknown resource types
DEFAULT_RESOURCE_META = AzureResourceMeta(
    display_name="Azure Resource",
    short_name="Res",
    category=ResourceCategory.OTHER,
    icon_file="generic.svg",
    fill_color="#B4B4B4",
    stroke_color="#808080",
)


def get_resource_meta(resource_type: str) -> AzureResourceMeta:
    """Get visual metadata for an Azure resource type.

    Args:
        resource_type: Full Azure resource type string (e.g., 'microsoft.compute/virtualmachines')

    Returns:
        AzureResourceMeta with display properties. Falls back to DEFAULT_RESOURCE_META.
    """
    return AZURE_RESOURCE_MAP.get(resource_type.lower(), DEFAULT_RESOURCE_META)


def is_container_type(resource_type: str) -> bool:
    """Check if a resource type should be rendered as a container/group."""
    meta = get_resource_meta(resource_type)
    return meta.is_container
