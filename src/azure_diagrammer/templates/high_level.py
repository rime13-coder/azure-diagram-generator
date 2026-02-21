"""High-level overview diagram template.

Shows subscriptions, resource groups, regions, and resource counts.
Intended for executive presentations and project overviews.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from azure_diagrammer.model.azure_types import get_resource_meta
from azure_diagrammer.model.graph import (
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramPage,
    GroupType,
    Position,
    Size,
)
from azure_diagrammer.model.layout import LayoutStrategy, layout_page


def build_high_level_page(
    resources: list[dict[str, Any]],
    resource_groups: list[dict[str, Any]],
    subscriptions: list[dict[str, Any]],
) -> DiagramPage:
    """Build a high-level overview diagram page.

    Groups resources by subscription -> resource group and shows
    summarized resource counts by type within each RG.

    Args:
        resources: All discovered resources.
        resource_groups: Discovered resource groups.
        subscriptions: Discovered subscriptions.

    Returns:
        A DiagramPage ready for rendering.
    """
    page = DiagramPage(id="high-level", title="High-Level Architecture Overview")
    nodes: list[DiagramNode] = []
    groups: list[DiagramGroup] = []

    # Index subscriptions
    sub_names: dict[str, str] = {}
    for sub in subscriptions:
        sub_id = sub.get("subscriptionId", "")
        sub_names[sub_id] = sub.get("name", sub_id[:8])

    # Index resources by RG
    rg_resources: dict[str, list[dict[str, Any]]] = {}
    for r in resources:
        rg = r.get("resourceGroup", "").lower()
        sub = r.get("subscriptionId", "")
        key = f"{sub}/{rg}"
        if key not in rg_resources:
            rg_resources[key] = []
        rg_resources[key].append(r)

    # Build subscription groups
    sub_ids_seen: set[str] = set()
    for rg in resource_groups:
        sub_id = rg.get("subscriptionId", "")
        if sub_id and sub_id not in sub_ids_seen:
            sub_ids_seen.add(sub_id)
            sub_group = DiagramGroup(
                id=f"sub-{sub_id[:8]}",
                name=sub_names.get(sub_id, f"Subscription {sub_id[:8]}"),
                group_type=GroupType.SUBSCRIPTION,
                style={"fill": "#F0F0F0", "stroke": "#999999"},
            )
            groups.append(sub_group)

    # Build RG groups and summary nodes
    for rg in resource_groups:
        sub_id = rg.get("subscriptionId", "")
        rg_name = rg.get("name", "unknown")
        rg_location = rg.get("location", "")
        rg_key = f"{sub_id}/{rg_name.lower()}"

        rg_group = DiagramGroup(
            id=f"rg-{rg_name}",
            name=f"RG: {rg_name} ({rg_location})" if rg_location else f"RG: {rg_name}",
            group_type=GroupType.RESOURCE_GROUP,
            parent_id=f"sub-{sub_id[:8]}" if sub_id else None,
            style={"fill": "#E8F4FD", "stroke": "#0078D4"},
            properties={"location": rg_location},
        )

        # Count resources by type in this RG
        rg_res = rg_resources.get(rg_key, [])
        type_counts: Counter[str] = Counter()
        for r in rg_res:
            rtype = r.get("type", "").lower()
            meta = get_resource_meta(rtype)
            type_counts[meta.short_name] += 1

        # Create summary nodes for each resource type
        for short_name, count in type_counts.most_common():
            node_id = f"summary-{rg_name}-{short_name}"
            label = f"{count}x {short_name}" if count > 1 else short_name
            node = DiagramNode(
                id=node_id,
                name=label,
                group_id=rg_group.id,
                size=Size(w=100, h=50),
                style={"fill": "#0078D4", "stroke": "#005A9E"},
            )
            nodes.append(node)
            rg_group.children.append(node_id)

        # Find parent subscription group and add RG as child
        for g in groups:
            if g.id == f"sub-{sub_id[:8]}":
                g.children.append(rg_group.id)
                break

        groups.append(rg_group)

    page.nodes = nodes
    page.groups = groups

    return layout_page(page, LayoutStrategy.GRID)
