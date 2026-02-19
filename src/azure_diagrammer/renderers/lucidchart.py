"""Lucidchart renderer — builds .lucid ZIP files and uploads via REST API.

The .lucid format is a ZIP archive containing:
  - document.json: Shapes, lines, groups, pages, and styling
  - images/: Embedded icon images (PNG/SVG)

Upload uses the Lucidchart Standard Import REST API.
"""

from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path
from typing import Any

import requests

from azure_diagrammer.model.azure_types import get_resource_meta
from azure_diagrammer.model.graph import (
    ArchitectureGraph,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramPage,
)
from azure_diagrammer.renderers.base import BaseRenderer

logger = logging.getLogger(__name__)


class LucidchartRenderer(BaseRenderer):
    """Renders architecture graphs as Lucidchart .lucid files."""

    def file_extension(self) -> str:
        return "lucid"

    def render(self, graph: ArchitectureGraph, output_path: Path) -> Path:
        """Build a .lucid ZIP file from the architecture graph.

        Args:
            graph: The architecture graph to render.
            output_path: Output directory or file path.

        Returns:
            Path to the generated .lucid file.
        """
        out_file = self.output_file(output_path, graph.project_name)
        document = self._build_document(graph)

        with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("document.json", json.dumps(document, indent=2))
            # Embed icon images if they exist
            self._embed_icons(zf, graph)

        logger.info("Generated Lucidchart file: %s", out_file)
        return out_file

    def _build_document(self, graph: ArchitectureGraph) -> dict[str, Any]:
        """Build the document.json structure for the .lucid format."""
        pages = []
        for page in graph.pages:
            pages.append(self._build_page(page))

        return {
            "version": 1,
            "type": "page",
            "title": graph.project_name,
            "pages": pages,
        }

    def _build_page(self, page: DiagramPage) -> dict[str, Any]:
        """Build a single page definition."""
        shapes = []
        lines = []
        containers = []

        # Render groups as container shapes
        for group in page.groups:
            containers.append(self._group_to_shape(group))

        # Render nodes as shapes
        for node in page.nodes:
            shapes.append(self._node_to_shape(node))

        # Render edges as lines
        for edge in page.edges:
            lines.append(self._edge_to_line(edge))

        return {
            "id": page.id,
            "title": page.title,
            "shapes": containers + shapes,
            "lines": lines,
        }

    def _node_to_shape(self, node: DiagramNode) -> dict[str, Any]:
        """Convert a DiagramNode to a Lucidchart shape."""
        meta = get_resource_meta(node.azure_resource_type)

        text = node.name
        if node.display_info:
            text += f"\n{node.display_info}"

        fill_color = node.style.get("fill", meta.fill_color)
        stroke_color = node.style.get("stroke", meta.stroke_color)

        shape: dict[str, Any] = {
            "id": node.id,
            "type": "rectangle",
            "boundingBox": {
                "x": node.position.x,
                "y": node.position.y,
                "w": node.size.w,
                "h": node.size.h,
            },
            "text": text,
            "style": {
                "fill": fill_color,
                "stroke": stroke_color,
                "fontColor": "#FFFFFF",
                "fontSize": 11,
                "fontFamily": "Segoe UI",
                "rounding": 4,
            },
            "customData": [
                {"key": "resourceId", "value": node.azure_resource_id},
                {"key": "resourceType", "value": node.azure_resource_type},
            ],
        }

        # Add icon reference if available
        if node.icon_path:
            shape["image"] = {
                "src": f"images/{Path(node.icon_path).name}",
                "position": "top",
                "size": {"w": 32, "h": 32},
            }

        # Set parent container if grouped
        if node.group_id:
            shape["containedBy"] = node.group_id

        return shape

    def _group_to_shape(self, group: DiagramGroup) -> dict[str, Any]:
        """Convert a DiagramGroup to a Lucidchart container shape."""
        fill_color = group.style.get("fill", "#F5F5F5")
        stroke_color = group.style.get("stroke", "#CCCCCC")

        return {
            "id": group.id,
            "type": "container",
            "boundingBox": {
                "x": group.bounding_box.x,
                "y": group.bounding_box.y,
                "w": group.bounding_box.w,
                "h": group.bounding_box.h,
            },
            "text": group.name,
            "style": {
                "fill": fill_color,
                "stroke": stroke_color,
                "fontColor": "#333333",
                "fontSize": 13,
                "fontFamily": "Segoe UI",
                "fontWeight": "bold",
                "rounding": 8,
                "dashArray": "none",
            },
            "containedBy": group.parent_id,
            "customData": [
                {"key": "resourceId", "value": group.azure_resource_id},
                {"key": "groupType", "value": group.group_type.value},
            ],
        }

    def _edge_to_line(self, edge: DiagramEdge) -> dict[str, Any]:
        """Convert a DiagramEdge to a Lucidchart line."""
        end_style = "none" if edge.bidirectional else "arrow"
        start_style = "arrow" if edge.bidirectional else "none"

        stroke_color = edge.style.get("stroke", "#666666")
        dash = edge.style.get("dash", "none")

        line: dict[str, Any] = {
            "id": edge.id,
            "lineType": "elbow",
            "endpoint1": {
                "type": "shapeEndpoint",
                "shapeId": edge.source_id,
                "style": start_style,
                "position": {"x": 1, "y": 0.5},
            },
            "endpoint2": {
                "type": "shapeEndpoint",
                "shapeId": edge.target_id,
                "style": end_style,
                "position": {"x": 0, "y": 0.5},
            },
            "style": {
                "stroke": stroke_color,
                "strokeWidth": 1.5,
                "dashArray": dash,
            },
        }

        if edge.label:
            line["text"] = [
                {"text": edge.label, "position": 0.5, "side": "top"}
            ]

        return line

    def _embed_icons(
        self, zf: zipfile.ZipFile, graph: ArchitectureGraph
    ) -> None:
        """Embed referenced icon files into the ZIP archive."""
        embedded: set[str] = set()
        for node in graph.all_nodes():
            if node.icon_path and node.icon_path not in embedded:
                icon_file = Path(node.icon_path)
                if icon_file.exists():
                    zf.write(icon_file, f"images/{icon_file.name}")
                    embedded.add(node.icon_path)


class LucidchartUploader:
    """Uploads .lucid files to Lucidchart via the Standard Import REST API."""

    def __init__(self, api_key: str, base_url: str = "https://api.lucid.co") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def upload(self, lucid_file: Path, title: str | None = None) -> str:
        """Upload a .lucid file and return the document URL.

        Args:
            lucid_file: Path to the .lucid ZIP file.
            title: Optional document title override.

        Returns:
            URL of the created Lucidchart document.

        Raises:
            requests.HTTPError: If the upload fails.
        """
        url = f"{self.base_url}/documents"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Lucid-Api-Version": "1",
        }

        with open(lucid_file, "rb") as f:
            files = {"file": (lucid_file.name, f, "application/zip")}
            data = {}
            if title:
                data["title"] = title

            response = requests.post(
                url, headers=headers, files=files, data=data, timeout=60
            )

        response.raise_for_status()
        result = response.json()
        doc_url = result.get("editUrl") or result.get("url", "")
        logger.info("Uploaded to Lucidchart: %s", doc_url)
        return doc_url
