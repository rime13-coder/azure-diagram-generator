"""Network topology diagram template.

Shows VNets, subnets, peerings, NSGs, load balancers, app gateways,
firewalls, private endpoints, route tables, and public IPs in a
hierarchical layout. NSG names shown inline in subnet labels.
"""

from __future__ import annotations

from typing import Any

from azure_diagrammer.discovery.ip_resolver import IPResolver
from azure_diagrammer.model.azure_types import get_resource_meta
from azure_diagrammer.templates.display_info import build_display_info, resolve_icon
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
    all_resources: list[dict[str, Any]] | None = None,
) -> DiagramPage:
    """Build a network topology diagram page.

    VNets are large containers with subnets inside. Resources are placed
    inside their subnet. VNet peering shown as bidirectional dashed lines.
    NSG names are shown inline in subnet labels when associated.

    Args:
        network_resources: Network resources keyed by type (from resource_graph).
        relationships: Inferred resource relationships.
        all_resources: All resources for IP resolution.

    Returns:
        A DiagramPage ready for rendering.
    """
    page = DiagramPage(id="network", title="Network Topology")
    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    groups: list[DiagramGroup] = []

    # Build IP resolver from all resources if provided
    ip_resolver: IPResolver | None = None
    if all_resources:
        ip_resolver = IPResolver(all_resources)

    # Index resources by ID for lookups
    resources_by_id: dict[str, dict[str, Any]] = {}
    for resources in network_resources.values():
        for r in resources:
            if "id" in r:
                resources_by_id[r["id"].lower()] = r

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
            name=f"Vnet {vnet_name}  {addr_space}" if addr_space else f"Vnet {vnet_name}",
            group_type=GroupType.VNET,
            azure_resource_id=vnet_id,
            style={"fill": "#CCEEFF", "stroke": "#44B8B1"},
            properties={"addressSpace": addr_space},
        )
        vnet_groups[vnet_id] = vnet_group
        groups.append(vnet_group)

    # Build subnet groups inside VNets (with inline NSG + delegation)
    subnet_groups: dict[str, DiagramGroup] = {}
    inlined_nsg_ids: set[str] = set()

    for vnet in network_resources.get("vnets", []):
        vnet_id = vnet.get("id", "").lower()
        vnet_name = vnet.get("name", "")
        props = vnet.get("properties", {}) or {}

        for subnet in props.get("subnets", []):
            subnet_name = subnet.get("name", "")
            subnet_props = subnet.get("properties", {}) or {}
            subnet_prefix = subnet_props.get("addressPrefix", "")
            subnet_id = subnet.get("id", "").lower()

            # Extract inline NSG name
            subnet_nsg_name = ""
            nsg_ref = subnet_props.get("networkSecurityGroup")
            if nsg_ref and isinstance(nsg_ref, dict):
                nsg_id_ref = (nsg_ref.get("id") or "").lower()
                if nsg_id_ref:
                    nsg_name_parts = nsg_id_ref.rstrip("/").split("/")
                    subnet_nsg_name = nsg_name_parts[-1] if nsg_name_parts else ""
                    inlined_nsg_ids.add(nsg_id_ref)

            # Build subnet label
            if subnet_nsg_name:
                label = f"Subnet + NSG {subnet_nsg_name}  {subnet_prefix}"
            else:
                label = f"Subnet {subnet_name}  {subnet_prefix}"

            subnet_group = DiagramGroup(
                id=f"subnet-{vnet_name}-{subnet_name}",
                name=label,
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

            # Extract subnet delegation
            delegations = subnet_props.get("delegations", [])
            if delegations:
                service_names = []
                for d in delegations:
                    d_props = d.get("properties") or {}
                    svc = d_props.get("serviceName", "")
                    if svc:
                        service_names.append(svc)
                if service_names:
                    delegation_node = DiagramNode(
                        id=f"delegation-{vnet_name}-{subnet_name}",
                        name=f"Subnet Delegation\nDelegate subnet to a service  {', '.join(service_names)}",
                        size=Size(w=250, h=40),
                        group_id=subnet_group.id,
                        style={"fill": "#FFFFFF", "stroke": "#CCCCCC"},
                    )
                    nodes.append(delegation_node)
                    subnet_group.children.append(delegation_node.id)

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

    for rtype_key in (
        "load_balancers", "app_gateways", "firewalls", "public_ips",
        "private_endpoints", "vnet_gateways", "route_tables",
    ):
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

            # Set icon
            icon = resolve_icon(rtype)
            if icon:
                node.icon_path = icon

            # Add IP and SKU info
            if ip_resolver:
                display = build_display_info(
                    resource, ip_resolver=ip_resolver,
                    show_sku=True, show_location=False, show_ips=True,
                )
                if display:
                    node.display_info = display

            # Try to place in a subnet via relationships
            subnet_id = _find_subnet_for_resource(rid, relationships, nic_to_subnet)
            if subnet_id and subnet_id in subnet_groups:
                node.group_id = subnet_groups[subnet_id].id
                subnet_groups[subnet_id].children.append(node.id)
            elif rtype_key == "route_tables":
                # Route tables go inside VNet (not subnet) — find via routes_for
                for rel in relationships:
                    if rel.source_id == rid and rel.relationship_type == "routes_for":
                        if rel.target_id in subnet_groups:
                            parent_vnet_id = subnet_groups[rel.target_id].parent_id
                            if parent_vnet_id:
                                node.group_id = parent_vnet_id
                                for g in groups:
                                    if g.id == parent_vnet_id:
                                        g.children.append(node.id)
                                break

            nodes.append(node)
            placed_ids.add(rid)

            # Create edges from route tables to their associated subnets
            if rtype_key == "route_tables":
                for rel in relationships:
                    if rel.source_id == rid and rel.relationship_type == "routes_for":
                        if rel.target_id in subnet_groups:
                            edges.append(
                                DiagramEdge(
                                    id=f"edge-rt-{rname}-{rel.target_id[-12:]}",
                                    source_id=node.id,
                                    target_id=subnet_groups[rel.target_id].id,
                                    label="UDR",
                                    edge_type=EdgeType.ASSOCIATION,
                                    style={"stroke": "#44B8B1", "dash": "5 3"},
                                )
                            )

    # NSGs as nodes — only for NSGs NOT already inlined in subnet labels
    for nsg in network_resources.get("nsgs", []):
        nsg_id = nsg.get("id", "").lower()
        nsg_name = nsg.get("name", "")

        if nsg_id in inlined_nsg_ids:
            placed_ids.add(nsg_id)
            continue

        node = DiagramNode(
            id=_make_node_id(nsg_id),
            name=nsg_name,
            azure_resource_type="microsoft.network/networksecuritygroups",
            azure_resource_id=nsg_id,
            size=Size(w=100, h=60),
        )
        icon = resolve_icon("microsoft.network/networksecuritygroups")
        if icon:
            node.icon_path = icon

        nodes.append(node)
        placed_ids.add(nsg_id)

        # Create edges from NSG to its associated subnets
        for rel in relationships:
            if rel.source_id == nsg_id and rel.relationship_type == "applied_to":
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
