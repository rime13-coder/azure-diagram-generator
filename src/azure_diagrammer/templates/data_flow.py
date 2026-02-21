"""Data flow diagram template.

Shows directional arrows indicating data movement between resources,
sourced from NSG rules, private endpoints, and service endpoints.
Swim lanes organized by subnet or resource group.
"""

from __future__ import annotations

from typing import Any

from azure_diagrammer.discovery.data_flow import DataFlow
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


def build_data_flow_page(
    data_flows: list[DataFlow],
    resources: list[dict[str, Any]],
) -> DiagramPage:
    """Build a data flow diagram page.

    Shows directional flows between endpoints with protocol/port
    annotations. Endpoints are grouped into swim lanes by subnet or RG.

    Args:
        data_flows: Discovered data flows.
        resources: All discovered resources (for name lookups).

    Returns:
        A DiagramPage ready for rendering.
    """
    page = DiagramPage(id="data-flow", title="Data Flow Diagram")
    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    groups: list[DiagramGroup] = []

    # Collect unique endpoints
    endpoint_set: set[str] = set()
    for flow in data_flows:
        endpoint_set.add(flow.source)
        endpoint_set.add(flow.destination)

    # Resource name lookup
    name_to_resource: dict[str, dict[str, Any]] = {}
    for r in resources:
        name_to_resource[r.get("name", "").lower()] = r

    # Classify endpoints into swim lanes by flow_type
    lane_map: dict[str, str] = {
        "network": "Network Flows",
        "private_link": "Private Link",
        "service_endpoint": "Service Endpoints",
        "diagnostic": "Diagnostics",
    }

    # Create swim lane groups
    flow_type_endpoints: dict[str, set[str]] = {}
    for flow in data_flows:
        ft = flow.flow_type
        if ft not in flow_type_endpoints:
            flow_type_endpoints[ft] = set()
        flow_type_endpoints[ft].add(flow.source)
        flow_type_endpoints[ft].add(flow.destination)

    lane_styles = {
        "Network Flows": {"fill": "#E3F2FD", "stroke": "#1976D2"},
        "Private Link": {"fill": "#E8F5E9", "stroke": "#388E3C"},
        "Service Endpoints": {"fill": "#FFF8E1", "stroke": "#FFA000"},
        "Diagnostics": {"fill": "#F3E5F5", "stroke": "#7B1FA2"},
    }

    # Create endpoint nodes
    node_id_map: dict[str, str] = {}
    endpoint_to_lane: dict[str, str] = {}

    for flow_type, endpoints in flow_type_endpoints.items():
        lane_name = lane_map.get(flow_type, "Other")

        for endpoint in endpoints:
            if endpoint not in node_id_map:
                node_id = _make_endpoint_node_id(endpoint)
                node_id_map[endpoint] = node_id
                endpoint_to_lane[endpoint] = lane_name

                # Try to find resource metadata
                resource = name_to_resource.get(endpoint.lower())
                rtype = ""
                if resource:
                    rtype = (resource.get("type") or "").lower()

                display_text = ""
                if resource:
                    display_text = build_display_info(
                        resource, show_sku=True, show_location=True,
                    )

                node = DiagramNode(
                    id=node_id,
                    name=endpoint,
                    azure_resource_type=rtype,
                    display_info=display_text,
                    size=Size(w=140, h=60),
                )
                if rtype:
                    icon = resolve_icon(rtype)
                    if icon:
                        node.icon_path = icon
                nodes.append(node)

    # Build swim lane groups from endpoints
    lane_endpoints: dict[str, list[str]] = {}
    for endpoint, lane in endpoint_to_lane.items():
        if lane not in lane_endpoints:
            lane_endpoints[lane] = []
        lane_endpoints[lane].append(node_id_map[endpoint])

    for lane_name, node_ids in lane_endpoints.items():
        group = DiagramGroup(
            id=f"lane-{lane_name.lower().replace(' ', '-')}",
            name=lane_name,
            group_type=GroupType.LOGICAL_TIER,
            children=node_ids,
            style=lane_styles.get(lane_name, {"fill": "#F5F5F5", "stroke": "#999"}),
        )
        for nid in node_ids:
            # Set group_id on the node
            for n in nodes:
                if n.id == nid:
                    n.group_id = group.id
                    break
        groups.append(group)

    # Create flow edges
    for idx, flow in enumerate(data_flows):
        src_node = node_id_map.get(flow.source)
        dst_node = node_id_map.get(flow.destination)

        if src_node and dst_node and src_node != dst_node:
            # Style based on flow type and access/direction
            style = {}
            if hasattr(flow, "access") and flow.access and flow.access.lower() == "deny":
                style = {"stroke": "#D32F2F", "dash": "3 3"}  # Red dashed for deny
            elif flow.flow_type == "private_link":
                style = {"stroke": "#388E3C"}
            elif flow.flow_type == "service_endpoint":
                style = {"stroke": "#FFA000"}
            elif flow.flow_type == "diagnostic":
                style = {"stroke": "#7B1FA2", "dash": "5 3"}
            elif hasattr(flow, "direction") and flow.direction == "Inbound":
                style = {"stroke": "#1565C0"}  # Dark blue for inbound
            elif hasattr(flow, "direction") and flow.direction == "Outbound":
                style = {"stroke": "#00838F"}  # Teal for outbound
            else:
                style = {"stroke": "#1976D2"}

            edges.append(
                DiagramEdge(
                    id=f"flow-{idx}",
                    source_id=src_node,
                    target_id=dst_node,
                    label=flow.label,
                    edge_type=EdgeType.DATA_FLOW,
                    style=style,
                )
            )

    page.nodes = nodes
    page.edges = edges
    page.groups = groups

    return layout_page(page, LayoutStrategy.LEFT_TO_RIGHT)


def _make_endpoint_node_id(endpoint: str) -> str:
    """Create a safe node ID from an endpoint identifier."""
    import re

    safe = re.sub(r"[^a-zA-Z0-9]", "_", endpoint)
    return f"ep-{safe}"[:64]
