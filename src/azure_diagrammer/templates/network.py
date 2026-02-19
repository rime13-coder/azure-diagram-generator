"""Network topology diagram template.

Shows VNets, subnets, peerings, NSGs, load balancers, app gateways,
firewalls, private endpoints, and public IPs in a hierarchical layout.
"""

from __future__ import annotations

from typing import Any

from azure_diagrammer.model.azure_types import get_resource_meta
from azure_diagrammer.model.graph import (
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramPage,
    EdgeType,
    GroupType,
    Size,
)
from azure_diagrammer.model.layout import LayoutStrategy, layout_page
from azure_diagrammer.discovery.relationships import ResourceRelationship


def build_network_page(
    network_resources: dict[str, list[dict[str, Any]]],
    relationships: list[ResourceRelationship],
) -> DiagramPage:
    """Build a network topology diagram page.

    VNets are large containers with subnets inside. Resources are placed
    inside their subnet. VNet peering shown as bidirectional dashed lines.

    Args:
        network_resources: Network resources keyed by type (from resource_graph).
        relationships: Inferred resource relationships.

    Returns:
        A DiagramPage ready for rendering.
    """
    page = DiagramPage(id="network", title="Network Topology")
    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    groups: list[DiagramGroup] = []

    # Index resources by ID for lookups
    all_resources: dict[str, dict[str, Any]] = {}
    for resources in network_resources.values():
        for r in resources:
            if "id" in r:
                all_resources[r["id"].lower()] = r

    # Build VNet groups
    vnet_groups: dict[str, DiagramGroup] = {}
    for vnet in network_resources.get("vnets", []):
        vnet_id = vnet.get("id", "").lower()
        vnet_name = vnet.get("name", "")
        props = vnet.get("properties", {}) or {}

        # Extract address space
        addr_space = ""
        addr_prefixes = (props.get("addressSpace") or {}).get("addressPrefixes", [])
        if addr_prefixes:
            addr_space = ", ".join(addr_prefixes)

        vnet_group = DiagramGroup(
            id=f"vnet-{vnet_name}",
            name=f"VNet: {vnet_name}",
            group_type=GroupType.VNET,
            azure_resource_id=vnet_id,
            style={"fill": "#CCEEFF", "stroke": "#44B8B1"},
            properties={"addressSpace": addr_space},
        )
        vnet_groups[vnet_id] = vnet_group
        groups.append(vnet_group)

    # Build subnet groups inside VNets
    subnet_groups: dict[str, DiagramGroup] = {}
    for vnet in network_resources.get("vnets", []):
        vnet_id = vnet.get("id", "").lower()
        vnet_name = vnet.get("name", "")
        props = vnet.get("properties", {}) or {}

        for subnet in props.get("subnets", []):
            subnet_name = subnet.get("name", "")
            subnet_props = subnet.get("properties", {}) or {}
            subnet_prefix = subnet_props.get("addressPrefix", "")
            subnet_id = subnet.get("id", "").lower()

            subnet_group = DiagramGroup(
                id=f"subnet-{vnet_name}-{subnet_name}",
                name=f"Subnet: {subnet_name} ({subnet_prefix})",
                group_type=GroupType.SUBNET,
                parent_id=f"vnet-{vnet_name}",
                azure_resource_id=subnet_id,
                style={"fill": "#E8F5FF", "stroke": "#44B8B1"},
                properties={"addressPrefix": subnet_prefix},
            )
            subnet_groups[subnet_id] = subnet_group

            # Add subnet to VNet group's children
            if vnet_id in vnet_groups:
                vnet_groups[vnet_id].children.append(subnet_group.id)

            groups.append(subnet_group)

    # Build relationship index for placing resources in subnets
    nic_to_subnet: dict[str, str] = {}
    resource_to_nic: dict[str, list[str]] = {}
    for rel in relationships:
        if rel.relationship_type == "in_subnet":
            nic_to_subnet[rel.source_id] = rel.target_id
        elif rel.relationship_type == "has_nic":
            if rel.source_id not in resource_to_nic:
                resource_to_nic[rel.source_id] = []
            resource_to_nic[rel.source_id].append(rel.target_id)

    # Place networking-relevant resources as nodes
    placed_ids: set[str] = set()

    # Load balancers, app gateways, firewalls, public IPs, private endpoints
    for rtype_key in ("load_balancers", "app_gateways", "firewalls", "public_ips", "private_endpoints", "vnet_gateways"):
        for resource in network_resources.get(rtype_key, []):
            rid = resource.get("id", "").lower()
            rname = resource.get("name", "")
            rtype = resource.get("type", "").lower()
            meta = get_resource_meta(rtype)

            node = DiagramNode(
                id=_make_node_id(rid),
                name=rname,
                azure_resource_type=rtype,
                azure_resource_id=rid,
                size=Size(w=meta.default_width, h=meta.default_height),
            )

            # Try to place in a subnet via relationships
            subnet_id = _find_subnet_for_resource(rid, relationships, nic_to_subnet)
            if subnet_id and subnet_id in subnet_groups:
                node.group_id = subnet_groups[subnet_id].id
                subnet_groups[subnet_id].children.append(node.id)

            nodes.append(node)
            placed_ids.add(rid)

    # NSGs as nodes (placed alongside subnets)
    for nsg in network_resources.get("nsgs", []):
        nsg_id = nsg.get("id", "").lower()
        nsg_name = nsg.get("name", "")
        props = nsg.get("properties", {}) or {}

        node = DiagramNode(
            id=_make_node_id(nsg_id),
            name=nsg_name,
            azure_resource_type="microsoft.network/networksecuritygroups",
            azure_resource_id=nsg_id,
            size=Size(w=100, h=60),
        )
        nodes.append(node)
        placed_ids.add(nsg_id)

        # Create edges from NSG to its associated subnets
        for rel in relationships:
            if rel.source_id == nsg_id and rel.relationship_type == "applied_to":
                target_node_id = _make_node_id(rel.target_id)
                # Check if target is a subnet group
                if rel.target_id in subnet_groups:
                    edges.append(
                        DiagramEdge(
                            id=f"edge-nsg-{nsg_name}-{rel.target_id[-12:]}",
                            source_id=node.id,
                            target_id=subnet_groups[rel.target_id].id,
                            label="NSG",
                            edge_type=EdgeType.ASSOCIATION,
                            style={"stroke": "#E3008C", "dash": "5 3"},
                        )
                    )

    # VNet peering edges
    for peering in network_resources.get("peerings", []):
        vnet_id = (peering.get("vnetId") or "").lower()
        remote_vnet_id = (peering.get("remoteVnetId") or "").lower()
        peering_state = peering.get("peeringState", "")

        if vnet_id in vnet_groups and remote_vnet_id in vnet_groups:
            edges.append(
                DiagramEdge(
                    id=f"peering-{vnet_id[-8:]}-{remote_vnet_id[-8:]}",
                    source_id=vnet_groups[vnet_id].id,
                    target_id=vnet_groups[remote_vnet_id].id,
                    label=f"Peering ({peering_state})",
                    edge_type=EdgeType.PEERING,
                    bidirectional=True,
                    style={"stroke": "#44B8B1", "dash": "5 5"},
                )
            )

    page.nodes = nodes
    page.edges = edges
    page.groups = groups

    return layout_page(page, LayoutStrategy.HIERARCHICAL)


def _make_node_id(resource_id: str) -> str:
    """Create a short node ID from a full Azure resource ID."""
    parts = resource_id.rstrip("/").split("/")
    if len(parts) >= 2:
        return f"node-{parts[-2]}-{parts[-1]}"[:64]
    return f"node-{parts[-1]}" if parts else "node-unknown"


def _find_subnet_for_resource(
    resource_id: str,
    relationships: list[ResourceRelationship],
    nic_to_subnet: dict[str, str],
) -> str | None:
    """Try to find the subnet a resource belongs to."""
    # Direct in_subnet relationship
    for rel in relationships:
        if rel.source_id == resource_id and rel.relationship_type == "in_subnet":
            return rel.target_id

    # Via NIC -> subnet
    for rel in relationships:
        if rel.source_id == resource_id and rel.relationship_type == "has_nic":
            nic_id = rel.target_id
            if nic_id in nic_to_subnet:
                return nic_to_subnet[nic_id]

    return None
