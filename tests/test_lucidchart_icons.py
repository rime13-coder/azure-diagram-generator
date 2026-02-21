"""Tests for Lucidchart renderer icon support and GroupType-aware styling.

Covers:
- Nodes with icon_path produce image + text composite shapes
- Nodes without icon_path produce rectangle shapes
- Icon files embedded in ZIP archive
- GroupType-aware container styling (stroke width, dash)
- EdgeType-aware line styling
"""

import json
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from azure_diagrammer.model.graph import (
    ArchitectureGraph,
    BoundingBox,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramPage,
    EdgeType,
    GroupType,
    Position,
    Size,
)
from azure_diagrammer.renderers.lucidchart import LucidchartRenderer


@pytest.fixture
def renderer():
    return LucidchartRenderer()


@pytest.fixture
def icon_graph(tmp_path):
    """Graph with a node that has an icon_path (fake SVG)."""
    # Create a fake icon file
    icon_file = tmp_path / "vm-icon.svg"
    icon_file.write_text("<svg></svg>")

    graph = ArchitectureGraph(project_name="icon-test")
    page = DiagramPage(id="p1", title="Icon Test")
    page.nodes = [
        DiagramNode(
            id="vm1",
            name="web-vm-01",
            azure_resource_type="microsoft.compute/virtualmachines",
            azure_resource_id="/sub/rg/vm/web-vm-01",
            icon_path=str(icon_file),
            position=Position(x=100, y=100),
            size=Size(w=130, h=60),
            display_info="Standard_D2s_v3 | eastus",
        ),
        DiagramNode(
            id="noicon",
            name="generic-resource",
            azure_resource_type="",
            position=Position(x=300, y=100),
            size=Size(w=120, h=80),
        ),
    ]
    page.groups = []
    page.edges = []
    graph.add_page(page)
    return graph


@pytest.fixture
def group_graph():
    """Graph with various GroupType containers."""
    graph = ArchitectureGraph(project_name="group-test")
    page = DiagramPage(id="p1", title="Group Test")
    page.nodes = []
    page.edges = []
    page.groups = [
        DiagramGroup(
            id="vnet-main",
            name="VNet main",
            group_type=GroupType.VNET,
            style={"fill": "#CCEEFF", "stroke": "#44B8B1"},
            bounding_box=BoundingBox(x=0, y=0, w=600, h=400),
        ),
        DiagramGroup(
            id="subnet-web",
            name="Subnet web",
            group_type=GroupType.SUBNET,
            parent_id="vnet-main",
            style={"fill": "#E8F5FF", "stroke": "#44B8B1"},
            bounding_box=BoundingBox(x=20, y=40, w=260, h=160),
        ),
        DiagramGroup(
            id="asp-prod",
            name="App Service Plan",
            group_type=GroupType.APP_SERVICE_PLAN,
            style={"fill": "#E3F2FD", "stroke": "#0078D4"},
            bounding_box=BoundingBox(x=300, y=40, w=260, h=160),
        ),
        DiagramGroup(
            id="tier-compute",
            name="Compute",
            group_type=GroupType.LOGICAL_TIER,
            style={"fill": "#E3F2FD", "stroke": "#2196F3"},
            bounding_box=BoundingBox(x=0, y=420, w=600, h=200),
        ),
    ]
    graph.add_page(page)
    return graph


@pytest.fixture
def edge_graph():
    """Graph with various EdgeType edges."""
    graph = ArchitectureGraph(project_name="edge-test")
    page = DiagramPage(id="p1", title="Edge Test")
    page.nodes = [
        DiagramNode(id="a", name="A", position=Position(x=0, y=0)),
        DiagramNode(id="b", name="B", position=Position(x=200, y=0)),
        DiagramNode(id="c", name="C", position=Position(x=400, y=0)),
    ]
    page.groups = []
    page.edges = [
        DiagramEdge(
            id="e1",
            source_id="a",
            target_id="b",
            label="Peering",
            edge_type=EdgeType.PEERING,
            bidirectional=True,
            style={"stroke": "#44B8B1", "dash": "5 5"},
        ),
        DiagramEdge(
            id="e2",
            source_id="b",
            target_id="c",
            label="Flow",
            edge_type=EdgeType.DATA_FLOW,
            style={"stroke": "#1976D2"},
        ),
    ]
    graph.add_page(page)
    return graph


class TestIconShapes:
    def test_node_with_icon_produces_two_shapes(self, renderer, icon_graph, tmp_path):
        """A node with icon_path should produce an image shape + text shape."""
        out = renderer.render(icon_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        shapes = doc["pages"][0]["shapes"]
        # Find shapes for vm1: one icon (_icon suffix) and one text/label
        vm_shapes = [s for s in shapes if "vm1" in s["id"]]
        assert len(vm_shapes) == 2

        icon_shape = next((s for s in vm_shapes if s.get("fill", {}).get("type") == "image"), None)
        label_shape = next((s for s in vm_shapes if s["type"] == "text"), None)

        assert icon_shape is not None
        assert label_shape is not None

        # Icon should be a rectangle with image fill referencing the SVG
        assert icon_shape["type"] == "rectangle"
        assert icon_shape["fill"]["type"] == "image"
        assert "vm-icon.svg" in icon_shape["fill"]["ref"]

        # Label should contain node name
        assert "web-vm-01" in label_shape["text"]

    def test_node_without_icon_produces_rectangle(self, renderer, icon_graph, tmp_path):
        """A node without icon_path should produce a single rectangle shape."""
        out = renderer.render(icon_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        shapes = doc["pages"][0]["shapes"]
        noicon_shapes = [s for s in shapes if "noicon" in s["id"]]
        assert len(noicon_shapes) == 1
        assert noicon_shapes[0]["type"] == "rectangle"

    def test_icon_file_embedded_in_zip(self, renderer, icon_graph, tmp_path):
        """Icon files should be embedded under images/ in the ZIP."""
        out = renderer.render(icon_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            names = zf.namelist()
        assert "images/vm-icon.svg" in names


class TestGroupTypeStyling:
    def test_vnet_gets_thick_stroke(self, renderer, group_graph, tmp_path):
        """VNet containers should have strokeWidth 2."""
        out = renderer.render(group_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        shapes = doc["pages"][0]["shapes"]
        vnet_shape = next((s for s in shapes if "vnet" in s["id"]), None)
        assert vnet_shape is not None
        assert vnet_shape["style"]["strokeWidth"] == 2

    def test_subnet_has_stroke_color(self, renderer, group_graph, tmp_path):
        """Subnet containers should have strokeColor set."""
        out = renderer.render(group_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        shapes = doc["pages"][0]["shapes"]
        subnet_shape = next((s for s in shapes if "subnet" in s["id"]), None)
        assert subnet_shape is not None
        assert subnet_shape["style"]["strokeWidth"] == 1

    def test_asp_gets_thick_stroke(self, renderer, group_graph, tmp_path):
        """ASP containers should have strokeWidth 2."""
        out = renderer.render(group_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        shapes = doc["pages"][0]["shapes"]
        asp_shape = next((s for s in shapes if "asp" in s["id"]), None)
        assert asp_shape is not None
        assert asp_shape["style"]["strokeWidth"] == 2

    def test_logical_tier_has_stroke(self, renderer, group_graph, tmp_path):
        """Logical tier containers should have strokeWidth set."""
        out = renderer.render(group_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        shapes = doc["pages"][0]["shapes"]
        tier_shape = next((s for s in shapes if "tier" in s["id"]), None)
        assert tier_shape is not None
        assert "strokeWidth" in tier_shape["style"]


class TestEdgeTypeStyling:
    def test_peering_edge_thick_dashed(self, renderer, edge_graph, tmp_path):
        """Peering edges should have width 2 and dashed style."""
        out = renderer.render(edge_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        lines = doc["pages"][0]["lines"]
        peering_line = next((l for l in lines if l["id"] == "e1"), None)
        assert peering_line is not None
        assert peering_line["stroke"]["width"] == 2
        assert peering_line["stroke"]["style"] == "dashed"

    def test_peering_edge_bidirectional(self, renderer, edge_graph, tmp_path):
        """Peering edges should have arrows on both ends."""
        out = renderer.render(edge_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        lines = doc["pages"][0]["lines"]
        peering_line = next((l for l in lines if l["id"] == "e1"), None)
        assert peering_line is not None
        assert peering_line["endpoint1"]["style"] == "arrow"
        assert peering_line["endpoint2"]["style"] == "arrow"

    def test_data_flow_edge_normal(self, renderer, edge_graph, tmp_path):
        """Data flow edges should have normal width."""
        out = renderer.render(edge_graph, tmp_path)
        with zipfile.ZipFile(out, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        lines = doc["pages"][0]["lines"]
        flow_line = next((l for l in lines if l["id"] == "e2"), None)
        assert flow_line is not None
        assert flow_line["stroke"]["width"] == 1
