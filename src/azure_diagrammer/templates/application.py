"""Application architecture diagram template.

Shows app services, functions, VMs, databases, storage, caches,
messaging, and API management in a left-to-right flow layout.
Groups resources by logical tier: Ingress, Compute, Data, Integration.
App Service Plans rendered as containers with hosted apps inside.
"""

from __future__ import annotations

from typing import Any

from azure_diagrammer.discovery.ip_resolver import IPResolver
from azure_diagrammer.model.azure_types import ResourceCategory, get_resource_meta
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
    Integration, Data) and laid out left to right. App Service Plans
    are rendered as containers with their hosted apps inside.

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

    ip_resolver = IPResolver(resources)
    node_id_map: dict[str, str] = {}  # resource_id -> node_id

    # Build ASP -> hosted apps mapping
    asp_resources: dict[str, dict[str, Any]] = {}  # asp_id -> asp resource
    asp_hosted_apps: dict[str, list[str]] = {}  # asp_id -> [app_id, ...]

    for resource in resources:
        rtype = (resource.get("type") or "").lower()
        rid = (resource.get("id") or "").lower()
        if rtype == "microsoft.web/serverfarms":
            asp_resources[rid] = resource

    for rel in relationships:
        if rel.relationship_type == "hosted_on":
            asp_id = rel.target_id
            if asp_id in asp_resources:
                asp_hosted_apps.setdefault(asp_id, []).append(rel.source_id)

    # Track app IDs that are inside ASP containers (skip normal placement)
    apps_in_asp: set[str] = set()
    for app_ids in asp_hosted_apps.values():
        apps_in_asp.update(app_ids)

    # Classify resources into tiers
    tier_resources: dict[str, list[dict[str, Any]]] = {
        tier: [] for tier in _TIER_ORDER
    }

    for resource in resources:
        rtype = (resource.get("type") or "").lower()
        rid = (resource.get("id") or "").lower()
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

        # Skip ASPs (will be rendered as groups) and apps inside ASPs
        if rtype == "microsoft.web/serverfarms":
            continue
        if rid in apps_in_asp:
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

    for tier in _TIER_ORDER:
        tier_res = tier_resources[tier]
        if not tier_res and tier != "Compute":
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

            display_text = build_display_info(
                resource, ip_resolver=ip_resolver,
                show_sku=True, show_location=True, show_ips=True,
            )

            node_id = f"app-{rname}"
            node = DiagramNode(
                id=node_id,
                name=rname,
                azure_resource_type=rtype,
                azure_resource_id=rid,
                display_info=display_text,
                group_id=group.id,
                size=Size(w=meta.default_width, h=meta.default_height),
            )
            icon = resolve_icon(rtype)
            if icon:
                node.icon_path = icon

            nodes.append(node)
            group.children.append(node_id)
            node_id_map[rid] = node_id

        groups.append(group)

    # Create ASP groups inside the Compute tier
    compute_group = next((g for g in groups if g.id == "tier-compute"), None)
    if not compute_group:
        compute_group = DiagramGroup(
            id="tier-compute",
            name="Compute",
            group_type=GroupType.LOGICAL_TIER,
            style=tier_styles["Compute"],
        )
        groups.append(compute_group)

    for asp_id, asp_resource in asp_resources.items():
        asp_name = asp_resource.get("name", "")
        sku_text = ""
        sku = asp_resource.get("sku")
        if sku and isinstance(sku, dict):
            sku_text = sku.get("name", "")

        asp_group = DiagramGroup(
            id=f"asp-{asp_name}",
            name=f"App Service Plan\n{asp_name}" + (f" ({sku_text})" if sku_text else ""),
            group_type=GroupType.APP_SERVICE_PLAN,
            parent_id="tier-compute",
            azure_resource_id=asp_id,
            style={"fill": "#E3F2FD", "stroke": "#0078D4"},
        )

        # Add hosted apps as children
        for app_id in asp_hosted_apps.get(asp_id, []):
            app_resource = next(
                (r for r in resources if (r.get("id") or "").lower() == app_id),
                None,
            )
            if app_resource:
                app_name = app_resource.get("name", "")
                app_rtype = (app_resource.get("type") or "").lower()
                app_node_id = f"app-{app_name}"

                display_text = build_display_info(
                    app_resource, ip_resolver=ip_resolver,
                    show_sku=False, show_location=True, show_ips=True,
                )

                app_node = DiagramNode(
                    id=app_node_id,
                    name=app_name,
                    azure_resource_type=app_rtype,
                    azure_resource_id=app_id,
                    display_info=display_text,
                    group_id=asp_group.id,
                    size=Size(w=120, h=60),
                )
                icon = resolve_icon(app_rtype)
                if icon:
                    app_node.icon_path = icon

                nodes.append(app_node)
                asp_group.children.append(app_node_id)
                node_id_map[app_id] = app_node_id

        groups.append(asp_group)
        compute_group.children.append(asp_group.id)

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
