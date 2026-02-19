"""Cross-resource relationship inference engine.

Parses Azure resource properties to discover relationships between
resources (e.g., VM -> NIC -> Subnet -> VNet, LB -> Backend VMs).
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ResourceRelationship:
    """A discovered relationship between two Azure resources."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        label: str = "",
    ) -> None:
        self.source_id = source_id.lower()
        self.target_id = target_id.lower()
        self.relationship_type = relationship_type
        self.label = label

    def __repr__(self) -> str:
        return (
            f"Relationship({self.source_id} "
            f"--[{self.relationship_type}]--> {self.target_id})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ResourceRelationship):
            return NotImplemented
        return (
            self.source_id == other.source_id
            and self.target_id == other.target_id
            and self.relationship_type == other.relationship_type
        )

    def __hash__(self) -> int:
        return hash((self.source_id, self.target_id, self.relationship_type))


def _safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely navigate nested dictionaries."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def _extract_id(ref: Any) -> str | None:
    """Extract a resource ID from a property value (dict with 'id' or string)."""
    if isinstance(ref, dict):
        return ref.get("id")
    if isinstance(ref, str) and ref.startswith("/subscriptions/"):
        return ref
    return None


def build_relationship_graph(
    resources: list[dict[str, Any]],
) -> list[ResourceRelationship]:
    """Infer relationships between resources from their properties.

    Examines the `properties` field of each resource to find cross-references
    to other resources (by resource ID).

    Args:
        resources: List of resource dicts from Azure Resource Graph.

    Returns:
        List of inferred relationships.
    """
    relationships: set[ResourceRelationship] = set()
    resource_index = {r["id"].lower(): r for r in resources if "id" in r}

    for resource in resources:
        rid = resource.get("id", "").lower()
        rtype = resource.get("type", "").lower()
        props = resource.get("properties", {}) or {}

        if rtype == "microsoft.compute/virtualmachines":
            relationships.update(_infer_vm_relationships(rid, props))

        elif rtype == "microsoft.network/networkinterfaces":
            relationships.update(_infer_nic_relationships(rid, props))

        elif rtype == "microsoft.network/virtualnetworks":
            relationships.update(_infer_vnet_relationships(rid, props))

        elif rtype == "microsoft.network/networksecuritygroups":
            relationships.update(_infer_nsg_relationships(rid, props))

        elif rtype == "microsoft.network/loadbalancers":
            relationships.update(_infer_lb_relationships(rid, props))

        elif rtype == "microsoft.network/applicationgateways":
            relationships.update(_infer_appgw_relationships(rid, props))

        elif rtype == "microsoft.network/privateendpoints":
            relationships.update(_infer_pe_relationships(rid, props))

        elif rtype == "microsoft.web/sites":
            relationships.update(_infer_app_service_relationships(rid, props))

        elif rtype in (
            "microsoft.sql/servers",
            "microsoft.documentdb/databaseaccounts",
            "microsoft.cache/redis",
        ):
            relationships.update(_infer_data_resource_relationships(rid, props))

    logger.info("Inferred %d resource relationships", len(relationships))
    return list(relationships)


def _infer_vm_relationships(
    vm_id: str, props: dict
) -> list[ResourceRelationship]:
    """VM -> NIC (via networkProfile.networkInterfaces)."""
    rels = []
    nics = _safe_get(props, "networkProfile", "networkInterfaces", default=[])
    for nic_ref in nics:
        nic_id = _extract_id(nic_ref)
        if nic_id:
            rels.append(ResourceRelationship(vm_id, nic_id, "has_nic", "NIC"))
    return rels


def _infer_nic_relationships(
    nic_id: str, props: dict
) -> list[ResourceRelationship]:
    """NIC -> Subnet, NSG, Public IP."""
    rels = []

    # NIC -> NSG
    nsg_ref = _safe_get(props, "networkSecurityGroup")
    nsg_id = _extract_id(nsg_ref)
    if nsg_id:
        rels.append(ResourceRelationship(nic_id, nsg_id, "secured_by", "NSG"))

    # NIC -> Subnet, Public IP (via ipConfigurations)
    ip_configs = _safe_get(props, "ipConfigurations", default=[])
    for ip_config in ip_configs:
        ip_props = ip_config.get("properties", {}) or {}

        subnet_ref = ip_props.get("subnet")
        subnet_id = _extract_id(subnet_ref)
        if subnet_id:
            rels.append(
                ResourceRelationship(nic_id, subnet_id, "in_subnet", "Subnet")
            )

        pip_ref = ip_props.get("publicIPAddress")
        pip_id = _extract_id(pip_ref)
        if pip_id:
            rels.append(
                ResourceRelationship(nic_id, pip_id, "has_public_ip", "Public IP")
            )

    return rels


def _infer_vnet_relationships(
    vnet_id: str, props: dict
) -> list[ResourceRelationship]:
    """VNet -> Peered VNets (via virtualNetworkPeerings)."""
    rels = []
    peerings = _safe_get(props, "virtualNetworkPeerings", default=[])
    for peering in peerings:
        peering_props = peering.get("properties", {}) or {}
        remote_vnet = _safe_get(peering_props, "remoteVirtualNetwork")
        remote_id = _extract_id(remote_vnet)
        if remote_id:
            rels.append(
                ResourceRelationship(
                    vnet_id, remote_id, "peered_with", "VNet Peering"
                )
            )
    return rels


def _infer_nsg_relationships(
    nsg_id: str, props: dict
) -> list[ResourceRelationship]:
    """NSG -> Subnets, NICs it is associated with."""
    rels = []

    subnets = _safe_get(props, "subnets", default=[])
    for subnet_ref in subnets:
        subnet_id = _extract_id(subnet_ref)
        if subnet_id:
            rels.append(
                ResourceRelationship(nsg_id, subnet_id, "applied_to", "NSG -> Subnet")
            )

    nics = _safe_get(props, "networkInterfaces", default=[])
    for nic_ref in nics:
        nic_id = _extract_id(nic_ref)
        if nic_id:
            rels.append(
                ResourceRelationship(nsg_id, nic_id, "applied_to", "NSG -> NIC")
            )

    return rels


def _infer_lb_relationships(
    lb_id: str, props: dict
) -> list[ResourceRelationship]:
    """Load Balancer -> Backend NICs/IPs."""
    rels = []
    backend_pools = _safe_get(props, "backendAddressPools", default=[])
    for pool in backend_pools:
        pool_props = pool.get("properties", {}) or {}
        interfaces = pool_props.get("backendIPConfigurations", [])
        for iface in interfaces:
            iface_id = _extract_id(iface)
            if iface_id:
                # The reference is to an IP config; extract the NIC ID
                nic_id = _ip_config_to_nic_id(iface_id)
                if nic_id:
                    rels.append(
                        ResourceRelationship(
                            lb_id, nic_id, "load_balances", "Backend"
                        )
                    )
    return rels


def _infer_appgw_relationships(
    appgw_id: str, props: dict
) -> list[ResourceRelationship]:
    """Application Gateway -> Backend Pool targets."""
    rels = []
    backend_pools = _safe_get(props, "backendAddressPools", default=[])
    for pool in backend_pools:
        pool_props = pool.get("properties", {}) or {}
        addresses = pool_props.get("backendAddresses", [])
        for addr in addresses:
            fqdn = addr.get("fqdn", "")
            if fqdn:
                rels.append(
                    ResourceRelationship(
                        appgw_id, fqdn, "routes_to", f"Backend: {fqdn}"
                    )
                )

    # Gateway IP -> Subnet association
    gw_ip_configs = _safe_get(props, "gatewayIPConfigurations", default=[])
    for gw_ip in gw_ip_configs:
        gw_props = gw_ip.get("properties", {}) or {}
        subnet_ref = gw_props.get("subnet")
        subnet_id = _extract_id(subnet_ref)
        if subnet_id:
            rels.append(
                ResourceRelationship(appgw_id, subnet_id, "in_subnet", "AppGW Subnet")
            )

    return rels


def _infer_pe_relationships(
    pe_id: str, props: dict
) -> list[ResourceRelationship]:
    """Private Endpoint -> Target Service, Subnet."""
    rels = []

    # PE -> Target service
    connections = _safe_get(props, "privateLinkServiceConnections", default=[])
    connections += _safe_get(
        props, "manualPrivateLinkServiceConnections", default=[]
    )
    for conn in connections:
        conn_props = conn.get("properties", {}) or {}
        service_id = conn_props.get("privateLinkServiceId")
        if service_id:
            rels.append(
                ResourceRelationship(
                    pe_id, service_id, "private_link_to", "Private Link"
                )
            )

    # PE -> Subnet
    subnet_ref = _safe_get(props, "subnet")
    subnet_id = _extract_id(subnet_ref)
    if subnet_id:
        rels.append(
            ResourceRelationship(pe_id, subnet_id, "in_subnet", "PE Subnet")
        )

    return rels


def _infer_app_service_relationships(
    app_id: str, props: dict
) -> list[ResourceRelationship]:
    """App Service -> VNet integration subnet, server farm."""
    rels = []

    # VNet integration
    vnet_subnet_id = _safe_get(
        props, "virtualNetworkSubnetId"
    )
    if vnet_subnet_id:
        rels.append(
            ResourceRelationship(
                app_id, vnet_subnet_id, "vnet_integrated", "VNet Integration"
            )
        )

    # Server farm (App Service Plan)
    server_farm_id = _safe_get(props, "serverFarmId")
    if server_farm_id:
        rels.append(
            ResourceRelationship(
                app_id, server_farm_id, "hosted_on", "App Service Plan"
            )
        )

    return rels


def _infer_data_resource_relationships(
    resource_id: str, props: dict
) -> list[ResourceRelationship]:
    """Data resources -> Private endpoints, VNet rules."""
    rels = []

    # Private endpoint connections
    pe_connections = _safe_get(
        props, "privateEndpointConnections", default=[]
    )
    for pe_conn in pe_connections:
        pe_props = pe_conn.get("properties", {}) or {}
        pe_ref = _safe_get(pe_props, "privateEndpoint")
        pe_id = _extract_id(pe_ref)
        if pe_id:
            rels.append(
                ResourceRelationship(
                    resource_id, pe_id, "has_private_endpoint", "Private Endpoint"
                )
            )

    # Virtual network rules (e.g., SQL Server, Cosmos DB)
    vnet_rules = _safe_get(props, "virtualNetworkRules", default=[])
    for rule in vnet_rules:
        rule_props = rule.get("properties", {}) if isinstance(rule, dict) else {}
        subnet_id = rule_props.get("virtualNetworkSubnetId") or rule.get(
            "id", ""
        )
        if subnet_id and "/subnets/" in subnet_id.lower():
            rels.append(
                ResourceRelationship(
                    resource_id, subnet_id, "vnet_rule", "VNet Service Endpoint"
                )
            )

    return rels


def _ip_config_to_nic_id(ip_config_id: str) -> str | None:
    """Extract NIC resource ID from an IP configuration resource ID.

    IP config ID format: /subscriptions/.../networkInterfaces/<nic>/ipConfigurations/<config>
    """
    match = re.match(
        r"(.*/microsoft\.network/networkinterfaces/[^/]+)",
        ip_config_id,
        re.IGNORECASE,
    )
    return match.group(1) if match else None
