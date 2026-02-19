"""Mermaid markdown renderer.

Generates Mermaid flowchart/graph definitions that can be embedded
in Markdown documents, GitHub READMEs, wikis, and documentation.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from azure_diagrammer.model.azure_types import get_resource_meta
from azure_diagrammer.model.graph import (
    ArchitectureGraph,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramPage,
    EdgeType,
)
from azure_diagrammer.renderers.base import BaseRenderer

logger = logging.getLogger(__name__)


def _sanitize_id(raw_id: str) -> str:
    """Sanitize an ID for use in Mermaid syntax."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw_id)


def _escape_label(text: str) -> str:
    """Escape special characters in Mermaid labels."""
    return text.replace('"', "'").replace("|", "/").replace("[", "(").replace("]", ")")


class MermaidRenderer(BaseRenderer):
    """Renders architecture graphs as Mermaid flowchart markdown."""

    def __init__(self, direction: str = "TB") -> None:
        """Initialize with a graph direction.

        Args:
            direction: Mermaid graph direction (TB, BT, LR, RL).
        """
        self.direction = direction

    def file_extension(self) -> str:
        return "md"

    def render(self, graph: ArchitectureGraph, output_path: Path) -> Path:
        """Generate a Mermaid markdown file from the architecture graph.

        Args:
            graph: The architecture graph to render.
            output_path: Output directory or file path.

        Returns:
            Path to the generated .md file.
        """
        out_file = self.output_file(output_path, graph.project_name)
        content = self._build_markdown(graph)
        out_file.write_text(content, encoding="utf-8")

        logger.info("Generated Mermaid file: %s", out_file)
        return out_file

    def _build_markdown(self, graph: ArchitectureGraph) -> str:
        """Build complete Mermaid markdown content."""
        sections = []
        sections.append(f"# {graph.project_name} - Azure Architecture\n")

        for page in graph.pages:
            sections.append(f"## {page.title}\n")
            sections.append("```mermaid")
            sections.append(self._build_page(page))
            sections.append("```\n")

        return "\n".join(sections)

    def _build_page(self, page: DiagramPage) -> str:
        """Build Mermaid graph definition for a single page."""
        lines: list[str] = []
        lines.append(f"graph {self.direction}")

        # Track which nodes are inside subgraphs
        grouped_node_ids: set[str] = set()
        group_map = {g.id: g for g in page.groups}

        # Find root groups (no parent)
        root_groups = [g for g in page.groups if g.parent_id is None]

        # Render groups as subgraphs (recursive)
        for group in root_groups:
            self._render_subgraph(lines, group, group_map, page.nodes, grouped_node_ids, indent=2)

        # Render ungrouped nodes
        for node in page.nodes:
            if node.id not in grouped_node_ids:
                lines.append(f"  {self._render_node(node)}")

        # Render edges
        for edge in page.edges:
            lines.append(f"  {self._render_edge(edge)}")

        # Add style classes
        lines.extend(self._render_styles(page))

        return "\n".join(lines)

    def _render_subgraph(
        self,
        lines: list[str],
        group: DiagramGroup,
        group_map: dict[str, DiagramGroup],
        all_nodes: list[DiagramNode],
        grouped_node_ids: set[str],
        indent: int = 2,
    ) -> None:
        """Recursively render a group as a Mermaid subgraph."""
        pad = " " * indent
        sid = _sanitize_id(group.id)
        label = _escape_label(group.name)

        # Add extra info to label if available
        extra = ""
        address_space = group.properties.get("addressSpace")
        if address_space:
            extra = f" ({address_space})"

        lines.append(f"{pad}subgraph {sid}[\"{label}{extra}\"]")

        node_map = {n.id: n for n in all_nodes}

        # Render child groups first
        for child_id in group.children:
            if child_id in group_map:
                child_group = group_map[child_id]
                self._render_subgraph(
                    lines, child_group, group_map, all_nodes, grouped_node_ids, indent + 2
                )

        # Render child nodes
        for child_id in group.children:
            if child_id in node_map:
                node = node_map[child_id]
                lines.append(f"{pad}  {self._render_node(node)}")
                grouped_node_ids.add(child_id)

        lines.append(f"{pad}end")

    def _render_node(self, node: DiagramNode) -> str:
        """Render a single node as a Mermaid node definition."""
        nid = _sanitize_id(node.id)
        meta = get_resource_meta(node.azure_resource_type)
        label = node.name

        if node.display_info:
            label += f"\\n{node.display_info}"

        # Use different shapes based on category
        category = meta.category.value
        if category in ("data", "storage"):
            return f'{nid}[("{_escape_label(label)}")]'  # Cylinder
        elif category == "networking":
            return f'{nid}{{{{{_escape_label(label)}}}}}'  # Hexagon
        elif category == "security":
            return f'{nid}(("{_escape_label(label)}"))'  # Double circle
        else:
            return f'{nid}["{_escape_label(label)}"]'  # Rectangle

    def _render_edge(self, edge: DiagramEdge) -> str:
        """Render an edge as a Mermaid connection."""
        src = _sanitize_id(edge.source_id)
        tgt = _sanitize_id(edge.target_id)
        label = _escape_label(edge.label) if edge.label else ""

        if edge.bidirectional:
            arrow = "<-->"
        elif edge.edge_type == EdgeType.PEERING:
            arrow = "<-.->"
        elif edge.edge_type == EdgeType.DATA_FLOW:
            arrow = "==>"
        else:
            arrow = "-->"

        if label:
            return f'{src} {arrow}|"{label}"| {tgt}'
        return f"{src} {arrow} {tgt}"

    def _render_styles(self, page: DiagramPage) -> list[str]:
        """Generate Mermaid style class definitions."""
        lines: list[str] = []

        # Collect nodes by category for class styling
        categories: dict[str, list[str]] = {}
        for node in page.nodes:
            meta = get_resource_meta(node.azure_resource_type)
            cat = meta.category.value
            nid = _sanitize_id(node.id)
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(nid)

        # Define style classes
        style_defs = {
            "compute": "fill:#0078D4,stroke:#005A9E,color:#fff",
            "networking": "fill:#44B8B1,stroke:#2D8A85,color:#fff",
            "data": "fill:#E8590C,stroke:#C44B0A,color:#fff",
            "storage": "fill:#0063B1,stroke:#004E8C,color:#fff",
            "security": "fill:#E3008C,stroke:#B8006F,color:#fff",
            "integration": "fill:#8661C5,stroke:#6B4FA0,color:#fff",
            "monitoring": "fill:#00B7C3,stroke:#009AA3,color:#fff",
        }

        for cat, node_ids in categories.items():
            if cat in style_defs and node_ids:
                ids_str = ",".join(node_ids)
                lines.append(f"  classDef {cat} {style_defs[cat]}")
                lines.append(f"  class {ids_str} {cat}")

        return lines
