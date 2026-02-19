"""Auto-layout algorithms for positioning diagram elements.

Implements hierarchical and flow-based layout strategies for
different diagram types, with collision avoidance and group nesting.
"""

from __future__ import annotations

from enum import Enum

from azure_diagrammer.model.graph import (
    ArchitectureGraph,
    BoundingBox,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramPage,
    GroupType,
    Position,
    Size,
)

# Layout constants
PADDING = 40.0
GROUP_PADDING = 50.0
NODE_SPACING_X = 160.0
NODE_SPACING_Y = 120.0
GROUP_HEADER_HEIGHT = 30.0


class LayoutStrategy(str, Enum):
    """Available layout strategies."""

    HIERARCHICAL = "hierarchical"
    LEFT_TO_RIGHT = "left_to_right"
    GRID = "grid"
    FORCE_DIRECTED = "force_directed"


def layout_page(page: DiagramPage, strategy: LayoutStrategy) -> DiagramPage:
    """Apply a layout strategy to position all elements on a page.

    Args:
        page: The page with unpositioned nodes, edges, and groups.
        strategy: The layout algorithm to apply.

    Returns:
        The same page with updated positions and bounding boxes.
    """
    if strategy == LayoutStrategy.HIERARCHICAL:
        return _layout_hierarchical(page)
    elif strategy == LayoutStrategy.LEFT_TO_RIGHT:
        return _layout_left_to_right(page)
    elif strategy == LayoutStrategy.GRID:
        return _layout_grid(page)
    else:
        return _layout_hierarchical(page)


def layout_graph(graph: ArchitectureGraph, strategy: LayoutStrategy) -> ArchitectureGraph:
    """Apply layout to all pages in the graph."""
    for i, page in enumerate(graph.pages):
        graph.pages[i] = layout_page(page, strategy)
    return graph


# ── Hierarchical Layout (top-down, used for network diagrams) ────────


def _layout_hierarchical(page: DiagramPage) -> DiagramPage:
    """Top-down hierarchical layout with group nesting.

    Groups are laid out from top to bottom by nesting depth.
    Nodes inside groups are arranged in rows within the group.
    """
    node_map = {n.id: n for n in page.nodes}
    group_map = {g.id: g for g in page.groups}

    # Find root groups (no parent)
    root_groups = [g for g in page.groups if g.parent_id is None]
    # Find ungrouped nodes
    grouped_node_ids = set()
    for g in page.groups:
        grouped_node_ids.update(g.children)
    ungrouped_nodes = [n for n in page.nodes if n.id not in grouped_node_ids]

    current_x = PADDING
    current_y = PADDING

    # Layout root groups side by side
    for group in root_groups:
        _layout_group_recursive(
            group, group_map, node_map, current_x, current_y
        )
        current_x += group.bounding_box.w + PADDING

    # Layout ungrouped nodes in a row below all groups
    if ungrouped_nodes:
        max_group_bottom = PADDING
        for g in root_groups:
            bottom = g.bounding_box.y + g.bounding_box.h
            if bottom > max_group_bottom:
                max_group_bottom = bottom

        ux = PADDING
        uy = max_group_bottom + PADDING
        for node in ungrouped_nodes:
            node.position = Position(x=ux, y=uy)
            ux += node.size.w + NODE_SPACING_X

    return page


def _layout_group_recursive(
    group: DiagramGroup,
    group_map: dict[str, DiagramGroup],
    node_map: dict[str, DiagramNode],
    start_x: float,
    start_y: float,
) -> None:
    """Recursively layout a group and its children."""
    inner_x = start_x + GROUP_PADDING
    inner_y = start_y + GROUP_PADDING + GROUP_HEADER_HEIGHT

    child_groups = []
    child_nodes = []

    for child_id in group.children:
        if child_id in group_map:
            child_groups.append(group_map[child_id])
        elif child_id in node_map:
            child_nodes.append(node_map[child_id])

    # Layout child groups first (side by side)
    cx = inner_x
    max_child_height = 0.0
    for child_group in child_groups:
        _layout_group_recursive(child_group, group_map, node_map, cx, inner_y)
        cx += child_group.bounding_box.w + PADDING
        if child_group.bounding_box.h > max_child_height:
            max_child_height = child_group.bounding_box.h

    # Layout child nodes in rows below child groups
    node_y = inner_y + (max_child_height + PADDING if child_groups else 0)
    node_x = inner_x
    row_height = 0.0
    max_row_width = 0.0
    nodes_per_row = max(3, int(800 / NODE_SPACING_X))
    col = 0

    for node in child_nodes:
        if col >= nodes_per_row:
            node_y += row_height + NODE_SPACING_Y
            node_x = inner_x
            row_height = 0.0
            col = 0

        node.position = Position(x=node_x, y=node_y)
        node_x += node.size.w + NODE_SPACING_X
        if node.size.h > row_height:
            row_height = node.size.h
        if node_x - inner_x > max_row_width:
            max_row_width = node_x - inner_x
        col += 1

    # Calculate group bounding box
    content_width = max(
        cx - inner_x,  # Width from child groups
        max_row_width,  # Width from child nodes
        200.0,  # Minimum width
    )
    content_bottom = node_y + row_height if child_nodes else inner_y + max_child_height
    content_height = content_bottom - start_y + GROUP_PADDING

    group.bounding_box = BoundingBox(
        x=start_x,
        y=start_y,
        w=content_width + GROUP_PADDING * 2,
        h=max(content_height, 100.0),
    )


# ── Left-to-Right Flow Layout (used for application architecture) ────


def _layout_left_to_right(page: DiagramPage) -> DiagramPage:
    """Left-to-right flow layout with logical tiers.

    Nodes flow from left (ingress) to right (data stores).
    Groups are arranged as vertical swim lanes.
    """
    node_map = {n.id: n for n in page.nodes}
    group_map = {g.id: g for g in page.groups}

    # Arrange groups as columns left to right
    col_x = PADDING
    for group in page.groups:
        child_nodes = [node_map[cid] for cid in group.children if cid in node_map]

        node_y = PADDING + GROUP_PADDING + GROUP_HEADER_HEIGHT
        max_node_width = 0.0
        for node in child_nodes:
            node.position = Position(x=col_x + GROUP_PADDING, y=node_y)
            node_y += node.size.h + NODE_SPACING_Y
            if node.size.w > max_node_width:
                max_node_width = node.size.w

        group_width = max(max_node_width + GROUP_PADDING * 2, 200.0)
        group_height = max(node_y - PADDING + GROUP_PADDING, 150.0)
        group.bounding_box = BoundingBox(
            x=col_x, y=PADDING, w=group_width, h=group_height
        )
        col_x += group_width + PADDING

    # Position any ungrouped nodes to the right
    grouped_ids = set()
    for g in page.groups:
        grouped_ids.update(g.children)
    ungrouped = [n for n in page.nodes if n.id not in grouped_ids]
    uy = PADDING
    for node in ungrouped:
        node.position = Position(x=col_x, y=uy)
        uy += node.size.h + NODE_SPACING_Y

    return page


# ── Grid Layout (used for high-level overviews) ─────────────────────


def _layout_grid(page: DiagramPage) -> DiagramPage:
    """Grid layout for high-level overview diagrams.

    Root groups arranged in a grid. Resources summarized inside.
    """
    node_map = {n.id: n for n in page.nodes}
    group_map = {g.id: g for g in page.groups}
    root_groups = [g for g in page.groups if g.parent_id is None]

    cols = max(1, min(4, len(root_groups)))
    col_width = 350.0
    row_height = 250.0

    for idx, group in enumerate(root_groups):
        row = idx // cols
        col = idx % cols
        gx = PADDING + col * (col_width + PADDING)
        gy = PADDING + row * (row_height + PADDING)

        group.bounding_box = BoundingBox(x=gx, y=gy, w=col_width, h=row_height)

        # Position child nodes inside the group
        child_nodes = [node_map[cid] for cid in group.children if cid in node_map]
        nx = gx + GROUP_PADDING
        ny = gy + GROUP_PADDING + GROUP_HEADER_HEIGHT
        for node in child_nodes:
            node.position = Position(x=nx, y=ny)
            nx += node.size.w + 20
            if nx > gx + col_width - GROUP_PADDING:
                nx = gx + GROUP_PADDING
                ny += node.size.h + 20

        # Recursively layout child groups
        child_groups = [group_map[cid] for cid in group.children if cid in group_map]
        cgx = gx + GROUP_PADDING
        cgy = ny + PADDING if child_nodes else gy + GROUP_PADDING + GROUP_HEADER_HEIGHT
        for cg in child_groups:
            _layout_group_recursive(cg, group_map, node_map, cgx, cgy)
            cgx += cg.bounding_box.w + PADDING

    return page
