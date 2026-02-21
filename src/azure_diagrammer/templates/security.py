"""Security posture diagram template.

Shows subnets color-coded by risk level based on NSG coverage and
public exposure. Resources labeled with exposure status (PUBLIC,
PE-covered, private).
"""

from __future__ import annotations

from typing import Any

from azure_diagrammer.discovery.ip_resolver import IPResolver
from azure_diagrammer.discovery.relationships import ResourceRelationship
from azure_diagrammer.templates.display_info import resolve_icon
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


# Risk levels with corresponding styles
_RISK_STYLES = {
    "green": {"fill": "#C8E6C9", "stroke": "#2E7D32"},   # Private, NSG present
    "yellow": {"fill": "#FFF9C4", "stroke": "#F9A825"},   # Limited public or no NSG but no public
    "red": {"fill": "#FFCDD2", "stroke": "#C62828"},       # No NSG + public-facing
}


def build_security_page(
    resources: list[dict[str, Any]],
    network_resources: dict[str, list[dict[str, Any]]],
    relationships: list[ResourceRelationship],
    nsg_rules: list[dict[str, Any]] | None = None,
) -> DiagramPage:
    """Build a security posture diagram page.

    Subnets are color-coded by risk:
    - GREEN: Has NSG, no public-facing resources
    - YELLOW: Has NSG + public resources, or no NSG but no public
    - RED: No NSG + public-facing resources

    Args:
        resources: All discovered resources.
        network_resources: Network resources keyed by type.
        relationships: Inferred resource relationships.
        nsg_rules: NSG rule data.

    Returns:
        A DiagramPage ready for rendering.
    """
    page = DiagramPage(id="security", title="Security Posture")
    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    groups: list[DiagramGroup] = []

    ip_resolver = IPResolver(resources)

    # Build indexes
    nsg_to_subnets = _build_nsg_subnet_index(relationships, network_resources)
    subnet_nsg_map = _invert_nsg_subnet_index(nsg_to_subnets)
    open_ports_by_nsg = _build_open_ports_index(nsg_rules or [])
    resource_subnet_map = _build_resource_subnet_map(resources, relationships)
    pe_covered_resources = _build_pe_covered_set(relationships)

    # Build VNet -> Subnet groups
    for vnet in network_resources.get("vnets", []):
        vnet_id = vnet.get("id", "").lower()
        vnet_name = vnet.get("name", "")
        props = vnet.get("properties", {}) or {}

        vnet_group = DiagramGroup(
            id=f"sec-vnet-{vnet_name}",
            name=f"VNet: {vnet_name}",
            group_type=GroupType.VNET,
            azure_resource_id=vnet_id,
            style={"fill": "#ECEFF1", "stroke": "#607D8B"},
        )
        groups.append(vnet_group)

        for subnet in props.get("subnets", []):
            subnet_name = subnet.get("name", "")
            subnet_id = subnet.get("id", "").lower()
            subnet_props = subnet.get("properties", {}) or {}
            subnet_prefix = subnet_props.get("addressPrefix", "")

            has_nsg = subnet_id in subnet_nsg_map
            has_public = _subnet_has_public_resources(
                subnet_id, resources, resource_subnet_map, ip_resolver,
            )

            risk = _classify_risk(has_nsg, has_public)

            subnet_group = DiagramGroup(
                id=f"sec-subnet-{vnet_name}-{subnet_name}",
                name=f"Subnet: {subnet_name} ({subnet_prefix})",
                group_type=GroupType.SUBNET,
                parent_id=vnet_group.id,
                azure_resource_id=subnet_id,
                style=_RISK_STYLES[risk],
            )
            vnet_group.children.append(subnet_group.id)

            # Add NSG node if present
            if has_nsg:
                nsg_id = subnet_nsg_map[subnet_id]
                nsg_name = nsg_id.rstrip("/").split("/")[-1] if nsg_id else "NSG"
                open_ports = open_ports_by_nsg.get(nsg_id, [])
                port_text = ", ".join(sorted(open_ports)[:5]) if open_ports else "no open inbound"
                if len(open_ports) > 5:
                    port_text += f" (+{len(open_ports) - 5})"

                nsg_node = DiagramNode(
                    id=f"sec-nsg-{subnet_name}",
                    name=nsg_name,
                    azure_resource_type="microsoft.network/networksecuritygroups",
                    display_info=f"Open ports: {port_text}",
                    group_id=subnet_group.id,
                    size=Size(w=120, h=50),
                    style={"fill": "#E8EAF6", "stroke": "#3F51B5"},
                )
                nodes.append(nsg_node)
                subnet_group.children.append(nsg_node.id)

            # Add resource nodes in this subnet
            for resource in resources:
                rid = (resource.get("id") or "").lower()
                rtype = (resource.get("type") or "").lower()

                # Skip infrastructure types
                if rtype in (
                    "microsoft.network/networkinterfaces",
                    "microsoft.network/virtualnetworks",
                    "microsoft.network/virtualnetworks/subnets",
                    "microsoft.network/networksecuritygroups",
                    "microsoft.network/routetables",
                    "microsoft.network/publicipaddresses",
                    "microsoft.network/privateendpoints",
                ):
                    continue

                res_subnet = resource_subnet_map.get(rid)
                if res_subnet != subnet_id:
                    continue

                rname = resource.get("name", "")
                is_public = ip_resolver.has_public_ip(resource)
                is_pe_covered = rid in pe_covered_resources

                # Determine exposure label
                if is_public:
                    exposure = "PUBLIC"
                    ip_display = ip_resolver.get_resource_ip_display(resource)
                    if ip_display:
                        exposure = f"PUBLIC | {ip_display}"
                    node_style = {"fill": "#FFCDD2", "stroke": "#C62828"}
                elif is_pe_covered:
                    exposure = "PE-covered"
                    node_style = {"fill": "#FFF9C4", "stroke": "#F9A825"}
                else:
                    exposure = "private"
                    node_style = {"fill": "#C8E6C9", "stroke": "#2E7D32"}

                node = DiagramNode(
                    id=f"sec-{rname}",
                    name=rname,
                    azure_resource_type=rtype,
                    azure_resource_id=rid,
                    display_info=exposure,
                    group_id=subnet_group.id,
                    size=Size(w=130, h=55),
                    style=node_style,
                )
                icon = resolve_icon(rtype)
                if icon:
                    node.icon_path = icon
                nodes.append(node)
                subnet_group.children.append(node.id)

            groups.append(subnet_group)

    # Add edges from NSG to subnet
    edge_idx = 0
    for nsg_id, subnet_ids in nsg_to_subnets.items():
        nsg_short = nsg_id.rstrip("/").split("/")[-1] if nsg_id else "nsg"
        for subnet_id in subnet_ids:
            # Find the matching subnet group
            for g in groups:
                if g.azure_resource_id == subnet_id:
                    edges.append(
                        DiagramEdge(
                            id=f"sec-nsg-edge-{edge_idx}",
                            source_id=f"sec-nsg-{subnet_id.rstrip('/').split('/')[-1]}",
                            target_id=g.id,
                            label="NSG",
                            edge_type=EdgeType.ASSOCIATION,
                            style={"stroke": "#3F51B5", "dash": "5 3"},
                        )
                    )
                    edge_idx += 1
                    break

    page.nodes = nodes
    page.edges = edges
    page.groups = groups

    return layout_page(page, LayoutStrategy.HIERARCHICAL)


def _build_nsg_subnet_index(
    relationships: list[ResourceRelationship],
    network_resources: dict[str, list[dict[str, Any]]],
) -> dict[str, list[str]]:
    """Build NSG ID -> list of subnet IDs from relationships and VNet properties."""
    nsg_subnets: dict[str, list[str]] = {}

    # From relationships (applied_to)
    for rel in relationships:
        if rel.relationship_type == "applied_to":
            src = rel.source_id.lower() if rel.source_id else ""
            tgt = rel.target_id.lower() if rel.target_id else ""
            if "/networksecuritygroups/" in src:
                nsg_subnets.setdefault(src, []).append(tgt)

    # Also check VNet subnet properties for NSG references
    for vnet in network_resources.get("vnets", []):
        props = vnet.get("properties", {}) or {}
        for subnet in props.get("subnets", []):
            subnet_id = (subnet.get("id") or "").lower()
            subnet_props = subnet.get("properties", {}) or {}
            nsg_ref = subnet_props.get("networkSecurityGroup") or {}
            nsg_id = (nsg_ref.get("id") or "").lower()
            if nsg_id and subnet_id:
                nsg_subnets.setdefault(nsg_id, [])
                if subnet_id not in nsg_subnets[nsg_id]:
                    nsg_subnets[nsg_id].append(subnet_id)

    return nsg_subnets


def _invert_nsg_subnet_index(nsg_to_subnets: dict[str, list[str]]) -> dict[str, str]:
    """Build subnet ID -> NSG ID mapping."""
    result: dict[str, str] = {}
    for nsg_id, subnet_ids in nsg_to_subnets.items():
        for sid in subnet_ids:
            result[sid] = nsg_id
    return result


def _build_open_ports_index(nsg_rules: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build NSG ID -> list of open inbound ports."""
    result: dict[str, list[str]] = {}
    for rule in nsg_rules:
        access = (rule.get("access") or "").lower()
        direction = (rule.get("direction") or "").lower()
        if access != "allow" or direction != "inbound":
            continue
        nsg_id = (rule.get("nsgId") or "").lower()
        port = str(rule.get("destinationPortRange", "*"))
        if port and port != "*":
            result.setdefault(nsg_id, [])
            if port not in result[nsg_id]:
                result[nsg_id].append(port)
    return result


def _build_resource_subnet_map(
    resources: list[dict[str, Any]],
    relationships: list[ResourceRelationship],
) -> dict[str, str]:
    """Build resource ID -> subnet ID mapping via NIC relationships."""
    nic_to_subnet: dict[str, str] = {}
    resource_to_nic: dict[str, str] = {}

    for rel in relationships:
        if rel.relationship_type == "in_subnet":
            nic_to_subnet[rel.source_id] = rel.target_id
        elif rel.relationship_type == "has_nic":
            resource_to_nic[rel.source_id] = rel.target_id

    result: dict[str, str] = {}
    # Direct in_subnet (e.g. private endpoints)
    for rel in relationships:
        if rel.relationship_type == "in_subnet":
            result[rel.source_id] = rel.target_id

    # VM -> NIC -> subnet
    for rid, nic_id in resource_to_nic.items():
        if nic_id in nic_to_subnet:
            result[rid] = nic_to_subnet[nic_id]

    return result


def _build_pe_covered_set(relationships: list[ResourceRelationship]) -> set[str]:
    """Find resources covered by private endpoints."""
    pe_covered: set[str] = set()
    for rel in relationships:
        if rel.relationship_type == "private_link_to":
            pe_covered.add(rel.target_id)
        elif rel.relationship_type == "has_private_endpoint":
            pe_covered.add(rel.source_id)
    return pe_covered


def _subnet_has_public_resources(
    subnet_id: str,
    resources: list[dict[str, Any]],
    resource_subnet_map: dict[str, str],
    ip_resolver: IPResolver,
) -> bool:
    """Check if any resource in the subnet has a public IP."""
    for resource in resources:
        rid = (resource.get("id") or "").lower()
        if resource_subnet_map.get(rid) == subnet_id:
            if ip_resolver.has_public_ip(resource):
                return True
    return False


def _classify_risk(has_nsg: bool, has_public: bool) -> str:
    """Classify subnet risk level."""
    if has_nsg and not has_public:
        return "green"
    elif not has_nsg and has_public:
        return "red"
    else:
        # NSG + public = yellow, no NSG + no public = yellow
        return "yellow"
