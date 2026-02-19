"""Application architecture diagram template.

Shows app services, functions, VMs, databases, storage, caches,
messaging, and API management in a left-to-right flow layout.
Groups resources by logical tier: Ingress, Compute, Data, Integration.
"""

from __future__ import annotations

from typing import Any

from azure_diagrammer.model.azure_types import ResourceCategory, get_resource_meta
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

# Tier classification for application architecture
_TIER_ORDER = ["Ingress", "Compute", "Integration", "Data"]

_CATEGORY_TO_TIER: dict[ResourceCategory, str] = {
    ResourceCategory.NETWORKING: "Ingress",
    ResourceCategory.COMPUTE: "Compute",
    ResourceCategory.INTEGRATION: "Integration",
    ResourceCategory.DATA: "Data",
    ResourceCategory.STORAGE: "Data",
    ResourceCategory.SECURITY: "Ingress",
    ResourceCategory.MONITORING: "Integration",
}

# Resource types that belong in the Ingress tier
_INGRESS_TYPES = {
    "microsoft.network/applicationgateways",
    "microsoft.network/frontdoors",
    "microsoft.network/loadbalancers",
    "microsoft.network/azurefirewalls",
    "microsoft.network/trafficmanagerprofiles",
    "microsoft.apimanagement/service",
    "microsoft.network/applicationgatewaywebapplicationfirewallpolicies",
}


def build_application_page(
    resources: list[dict[str, Any]],
    relationships: list[ResourceRelationship],
) -> DiagramPage:
    """Build an application architecture diagram page.

    Resources are grouped into logical tiers (Ingress, Compute,
    Integration, Data) and laid out left to right.

    Args:
        resources: All discovered resources.
        relationships: Inferred resource relationships.

    Returns:
        A DiagramPage ready for rendering.
    """
    page = DiagramPage(id="application", title="Application Architecture")
    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    groups: list[DiagramGroup] = []

    # Classify resources into tiers
    tier_resources: dict[str, list[dict[str, Any]]] = {
        tier: [] for tier in _TIER_ORDER
    }

    for resource in resources:
        rtype = (resource.get("type") or "").lower()
        meta = get_resource_meta(rtype)

        # Skip NICs, subnets, VNets (not relevant to app architecture view)
        if rtype in (
            "microsoft.network/networkinterfaces",
            "microsoft.network/virtualnetworks",
            "microsoft.network/virtualnetworks/subnets",
            "microsoft.network/networksecuritygroups",
            "microsoft.network/routetables",
            "microsoft.network/publicipaddresses",
        ):
            continue

        # Override tier for specific ingress resources
        if rtype in _INGRESS_TYPES:
            tier = "Ingress"
        else:
            tier = _CATEGORY_TO_TIER.get(meta.category, "Compute")

        tier_resources[tier].append(resource)

    # Create tier groups and nodes
    tier_styles = {
        "Ingress": {"fill": "#FFF3E0", "stroke": "#FF9800"},
        "Compute": {"fill": "#E3F2FD", "stroke": "#2196F3"},
        "Integration": {"fill": "#F3E5F5", "stroke": "#9C27B0"},
        "Data": {"fill": "#FBE9E7", "stroke": "#E8590C"},
    }

    node_id_map: dict[str, str] = {}  # resource_id -> node_id

    for tier in _TIER_ORDER:
        tier_res = tier_resources[tier]
        if not tier_res:
            continue

        group = DiagramGroup(
            id=f"tier-{tier.lower()}",
            name=tier,
            group_type=GroupType.LOGICAL_TIER,
            style=tier_styles.get(tier, {"fill": "#F5F5F5", "stroke": "#999999"}),
        )

        for resource in tier_res:
            rid = (resource.get("id") or "").lower()
            rname = resource.get("name", "")
            rtype = (resource.get("type") or "").lower()
            meta = get_resource_meta(rtype)

            # Build display info (SKU, kind, etc.)
            display_parts = []
            sku = resource.get("sku", {})
            if isinstance(sku, dict) and sku.get("name"):
                display_parts.append(str(sku["name"]))
            kind = resource.get("kind", "")
            if kind:
                display_parts.append(kind)

            node_id = f"app-{rname}"
            node = DiagramNode(
                id=node_id,
                name=rname,
                azure_resource_type=rtype,
                azure_resource_id=rid,
                display_info=", ".join(display_parts),
                group_id=group.id,
                size=Size(w=meta.default_width, h=meta.default_height),
            )
            nodes.append(node)
            group.children.append(node_id)
            node_id_map[rid] = node_id

        groups.append(group)

    # Build edges from relationships
    edge_count = 0
    for rel in relationships:
        src_node = node_id_map.get(rel.source_id)
        tgt_node = node_id_map.get(rel.target_id)

        if src_node and tgt_node and src_node != tgt_node:
            # Determine edge type from relationship
            if rel.relationship_type in ("private_link_to", "vnet_rule"):
                edge_type = EdgeType.DATA_FLOW
            elif rel.relationship_type in ("load_balances", "routes_to"):
                edge_type = EdgeType.NETWORK
            else:
                edge_type = EdgeType.DEPENDENCY

            edges.append(
                DiagramEdge(
                    id=f"app-edge-{edge_count}",
                    source_id=src_node,
                    target_id=tgt_node,
                    label=rel.label,
                    edge_type=edge_type,
                )
            )
            edge_count += 1

    page.nodes = nodes
    page.edges = edges
    page.groups = groups

    return layout_page(page, LayoutStrategy.LEFT_TO_RIGHT)
