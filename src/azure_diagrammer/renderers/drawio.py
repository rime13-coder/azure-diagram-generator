"""Draw.io (diagrams.net) XML renderer.

Generates .drawio files in mxGraph XML format that can be opened
in the free diagrams.net editor. Uses Azure icon stencils.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

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

# Draw.io Azure stencil prefix for shape references
AZURE_STENCIL_PREFIX = "mxgraph.azure"

# Map resource categories to draw.io Azure stencil names
_DRAWIO_STENCIL_MAP = {
    "microsoft.compute/virtualmachines": "mxgraph.azure.virtual_machine",
    "microsoft.compute/virtualmachinescalesets": "mxgraph.azure.virtual_machine_scale_set",
    "microsoft.web/sites": "mxgraph.azure.app_service",
    "microsoft.web/serverfarms": "mxgraph.azure.app_service_plan",
    "microsoft.containerservice/managedclusters": "mxgraph.azure.kubernetes_service",
    "microsoft.network/virtualnetworks": "mxgraph.azure.virtual_network",
    "microsoft.network/loadbalancers": "mxgraph.azure.load_balancer",
    "microsoft.network/applicationgateways": "mxgraph.azure.application_gateway",
    "microsoft.network/azurefirewalls": "mxgraph.azure.firewall",
    "microsoft.network/networksecuritygroups": "mxgraph.azure.network_security_group",
    "microsoft.network/publicipaddresses": "mxgraph.azure.public_ip_address",
    "microsoft.network/privateendpoints": "mxgraph.azure.private_endpoint",
    "microsoft.sql/servers": "mxgraph.azure.sql_server",
    "microsoft.sql/servers/databases": "mxgraph.azure.sql_database",
    "microsoft.documentdb/databaseaccounts": "mxgraph.azure.cosmos_db",
    "microsoft.storage/storageaccounts": "mxgraph.azure.storage",
    "microsoft.keyvault/vaults": "mxgraph.azure.key_vault",
    "microsoft.servicebus/namespaces": "mxgraph.azure.service_bus",
    "microsoft.eventhub/namespaces": "mxgraph.azure.event_hub",
    "microsoft.apimanagement/service": "mxgraph.azure.api_management",
    "microsoft.cache/redis": "mxgraph.azure.redis_cache",
}


class DrawioRenderer(BaseRenderer):
    """Renders architecture graphs as Draw.io XML files."""

    def file_extension(self) -> str:
        return "drawio"

    def render(self, graph: ArchitectureGraph, output_path: Path) -> Path:
        """Generate a .drawio XML file from the architecture graph.

        Args:
            graph: The architecture graph to render.
            output_path: Output directory or file path.

        Returns:
            Path to the generated .drawio file.
        """
        out_file = self.output_file(output_path, graph.project_name)
        root = self._build_mxfile(graph)

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(str(out_file), encoding="utf-8", xml_declaration=True)

        logger.info("Generated Draw.io file: %s", out_file)
        return out_file

    def _build_mxfile(self, graph: ArchitectureGraph) -> ET.Element:
        """Build the root mxfile XML element."""
        mxfile = ET.Element("mxfile", attrib={
            "host": "azure-diagrammer",
            "type": "device",
        })

        for page in graph.pages:
            diagram = ET.SubElement(mxfile, "diagram", attrib={
                "id": page.id,
                "name": page.title,
            })
            graph_model = ET.SubElement(diagram, "mxGraphModel", attrib={
                "dx": "1200",
                "dy": "900",
                "grid": "1",
                "gridSize": "10",
                "guides": "1",
                "tooltips": "1",
                "connect": "1",
                "arrows": "1",
                "fold": "1",
                "page": "1",
                "pageScale": "1",
                "math": "0",
            })
            root = ET.SubElement(graph_model, "root")

            # Required default cells
            ET.SubElement(root, "mxCell", attrib={"id": "0"})
            ET.SubElement(root, "mxCell", attrib={"id": "1", "parent": "0"})

            # Render groups as containers
            for group in page.groups:
                self._add_group(root, group)

            # Render nodes
            for node in page.nodes:
                self._add_node(root, node)

            # Render edges
            for edge in page.edges:
                self._add_edge(root, edge)

        return mxfile

    def _add_group(self, root: ET.Element, group: DiagramGroup) -> None:
        """Add a group/container cell to the XML."""
        fill = group.style.get("fill", "#DAE8FC")
        stroke = group.style.get("stroke", "#6C8EBF")

        style = (
            f"rounded=1;whiteSpace=wrap;html=1;arcSize=4;"
            f"fillColor={fill};strokeColor={stroke};"
            f"dashed=1;dashPattern=5 5;verticalAlign=top;"
            f"fontStyle=1;fontSize=13;fontColor=#333333;"
            f"container=1;collapsible=0;"
        )

        parent_id = group.parent_id or "1"

        cell = ET.SubElement(root, "mxCell", attrib={
            "id": group.id,
            "value": group.name,
            "style": style,
            "vertex": "1",
            "parent": parent_id,
            "connectable": "0",
        })
        ET.SubElement(cell, "mxGeometry", attrib={
            "x": str(group.bounding_box.x),
            "y": str(group.bounding_box.y),
            "width": str(group.bounding_box.w),
            "height": str(group.bounding_box.h),
            "as": "geometry",
        })

    def _add_node(self, root: ET.Element, node: DiagramNode) -> None:
        """Add a resource node cell to the XML."""
        meta = get_resource_meta(node.azure_resource_type)
        stencil = _DRAWIO_STENCIL_MAP.get(node.azure_resource_type.lower(), "")

        fill = node.style.get("fill", meta.fill_color)
        stroke = node.style.get("stroke", meta.stroke_color)

        if stencil:
            style = (
                f"shape={stencil};whiteSpace=wrap;html=1;"
                f"fillColor={fill};strokeColor={stroke};"
                f"fontColor=#FFFFFF;fontSize=11;rounded=1;arcSize=4;"
            )
        else:
            style = (
                f"rounded=1;whiteSpace=wrap;html=1;"
                f"fillColor={fill};strokeColor={stroke};"
                f"fontColor=#FFFFFF;fontSize=11;arcSize=4;"
            )

        label = node.name
        if node.display_info:
            label += f"<br><font style='font-size:9px'>{node.display_info}</font>"

        parent_id = node.group_id or "1"

        cell = ET.SubElement(root, "mxCell", attrib={
            "id": node.id,
            "value": label,
            "style": style,
            "vertex": "1",
            "parent": parent_id,
        })
        ET.SubElement(cell, "mxGeometry", attrib={
            "x": str(node.position.x),
            "y": str(node.position.y),
            "width": str(node.size.w),
            "height": str(node.size.h),
            "as": "geometry",
        })

    def _add_edge(self, root: ET.Element, edge: DiagramEdge) -> None:
        """Add a connection edge cell to the XML."""
        stroke = edge.style.get("stroke", "#666666")
        dash = "1" if edge.style.get("dash") else "0"

        end_arrow = "classic" if not edge.bidirectional else "classic"
        start_arrow = "classic" if edge.bidirectional else "none"

        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=1;"
            f"orthogonalLoop=1;jettySize=auto;html=1;"
            f"strokeColor={stroke};strokeWidth=1.5;"
            f"endArrow={end_arrow};startArrow={start_arrow};"
            f"dashed={dash};"
        )

        cell = ET.SubElement(root, "mxCell", attrib={
            "id": edge.id,
            "value": edge.label,
            "style": style,
            "edge": "1",
            "source": edge.source_id,
            "target": edge.target_id,
            "parent": "1",
        })
        ET.SubElement(cell, "mxGeometry", attrib={
            "relative": "1",
            "as": "geometry",
        })
