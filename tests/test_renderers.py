"""Tests for diagram renderers (Mermaid, Draw.io, Lucidchart)."""

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

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
from azure_diagrammer.renderers.mermaid import MermaidRenderer
from azure_diagrammer.renderers.drawio import DrawioRenderer
from azure_diagrammer.renderers.lucidchart import LucidchartRenderer


@pytest.fixture
def sample_graph() -> ArchitectureGraph:
    """Create a sample architecture graph for renderer tests."""
    graph = ArchitectureGraph(project_name="test-project")

    page = DiagramPage(id="p1", title="Test Diagram")

    # Groups
    vnet_group = DiagramGroup(
        id="vnet-main",
        name="VNet: main-vnet (10.0.0.0/16)",
        group_type=GroupType.VNET,
        children=["subnet-web", "subnet-data"],
        bounding_box=BoundingBox(x=40, y=40, w=600, h=500),
        style={"fill": "#CCEEFF", "stroke": "#44B8B1"},
        properties={"addressSpace": "10.0.0.0/16"},
    )
    subnet_web = DiagramGroup(
        id="subnet-web",
        name="Subnet: web (10.0.1.0/24)",
        group_type=GroupType.SUBNET,
        parent_id="vnet-main",
        children=["vm1", "vm2"],
        bounding_box=BoundingBox(x=80, y=100, w=250, h=200),
        style={"fill": "#E8F5FF", "stroke": "#44B8B1"},
    )
    subnet_data = DiagramGroup(
        id="subnet-data",
        name="Subnet: data (10.0.2.0/24)",
        group_type=GroupType.SUBNET,
        parent_id="vnet-main",
        children=["sql1"],
        bounding_box=BoundingBox(x=350, y=100, w=250, h=200),
        style={"fill": "#E8F5FF", "stroke": "#44B8B1"},
    )
    page.groups = [vnet_group, subnet_web, subnet_data]

    # Nodes
    vm1 = DiagramNode(
        id="vm1",
        name="web-vm-01",
        azure_resource_type="microsoft.compute/virtualmachines",
        azure_resource_id="/subscriptions/sub1/providers/Microsoft.Compute/virtualMachines/web-vm-01",
        position=Position(x=100, y=150),
        size=Size(w=120, h=80),
        group_id="subnet-web",
        display_info="Standard_D2s_v3",
    )
    vm2 = DiagramNode(
        id="vm2",
        name="web-vm-02",
        azure_resource_type="microsoft.compute/virtualmachines",
        position=Position(x=100, y=260),
        size=Size(w=120, h=80),
        group_id="subnet-web",
    )
    sql1 = DiagramNode(
        id="sql1",
        name="prod-db",
        azure_resource_type="microsoft.sql/servers/databases",
        position=Position(x=380, y=150),
        size=Size(w=120, h=80),
        group_id="subnet-data",
    )
    page.nodes = [vm1, vm2, sql1]

    # Edges
    page.edges = [
        DiagramEdge(
            id="e1",
            source_id="vm1",
            target_id="sql1",
            label="SQL 1433",
            edge_type=EdgeType.DATA_FLOW,
        ),
        DiagramEdge(
            id="e2",
            source_id="vm2",
            target_id="sql1",
            label="SQL 1433",
            edge_type=EdgeType.DATA_FLOW,
        ),
    ]

    graph.add_page(page)
    return graph


class TestMermaidRenderer:
    def test_renders_markdown_file(self, sample_graph, tmp_path):
        renderer = MermaidRenderer()
        output = renderer.render(sample_graph, tmp_path)
        assert output.exists()
        assert output.suffix == ".md"

    def test_contains_mermaid_block(self, sample_graph, tmp_path):
        renderer = MermaidRenderer()
        output = renderer.render(sample_graph, tmp_path)
        content = output.read_text(encoding="utf-8")
        assert "```mermaid" in content
        assert "graph TB" in content

    def test_contains_subgraphs(self, sample_graph, tmp_path):
        renderer = MermaidRenderer()
        output = renderer.render(sample_graph, tmp_path)
        content = output.read_text(encoding="utf-8")
        assert "subgraph" in content
        assert "VNet" in content
        assert "end" in content

    def test_contains_nodes(self, sample_graph, tmp_path):
        renderer = MermaidRenderer()
        output = renderer.render(sample_graph, tmp_path)
        content = output.read_text(encoding="utf-8")
        assert "web-vm-01" in content or "web_vm_01" in content
        assert "prod-db" in content or "prod_db" in content

    def test_contains_edges(self, sample_graph, tmp_path):
        renderer = MermaidRenderer()
        output = renderer.render(sample_graph, tmp_path)
        content = output.read_text(encoding="utf-8")
        assert "SQL 1433" in content
        # Data flow edges use ==>
        assert "==>" in content

    def test_contains_style_classes(self, sample_graph, tmp_path):
        renderer = MermaidRenderer()
        output = renderer.render(sample_graph, tmp_path)
        content = output.read_text(encoding="utf-8")
        assert "classDef" in content

    def test_lr_direction(self, sample_graph, tmp_path):
        renderer = MermaidRenderer(direction="LR")
        output = renderer.render(sample_graph, tmp_path)
        content = output.read_text(encoding="utf-8")
        assert "graph LR" in content

    def test_project_name_in_title(self, sample_graph, tmp_path):
        renderer = MermaidRenderer()
        output = renderer.render(sample_graph, tmp_path)
        content = output.read_text(encoding="utf-8")
        assert "test-project" in content


class TestDrawioRenderer:
    def test_renders_xml_file(self, sample_graph, tmp_path):
        renderer = DrawioRenderer()
        output = renderer.render(sample_graph, tmp_path)
        assert output.exists()
        assert output.suffix == ".drawio"

    def test_valid_xml(self, sample_graph, tmp_path):
        renderer = DrawioRenderer()
        output = renderer.render(sample_graph, tmp_path)
        tree = ET.parse(str(output))
        root = tree.getroot()
        assert root.tag == "mxfile"

    def test_contains_diagram_element(self, sample_graph, tmp_path):
        renderer = DrawioRenderer()
        output = renderer.render(sample_graph, tmp_path)
        tree = ET.parse(str(output))
        root = tree.getroot()
        diagrams = root.findall("diagram")
        assert len(diagrams) == 1
        assert diagrams[0].get("name") == "Test Diagram"

    def test_contains_shapes_and_edges(self, sample_graph, tmp_path):
        renderer = DrawioRenderer()
        output = renderer.render(sample_graph, tmp_path)
        tree = ET.parse(str(output))
        root = tree.getroot()

        cells = root.findall(".//mxCell")
        # 2 default cells + 3 groups + 3 nodes + 2 edges = 10
        assert len(cells) >= 8

    def test_vertex_cells_have_geometry(self, sample_graph, tmp_path):
        renderer = DrawioRenderer()
        output = renderer.render(sample_graph, tmp_path)
        tree = ET.parse(str(output))
        root = tree.getroot()

        for cell in root.findall(".//mxCell[@vertex='1']"):
            geom = cell.find("mxGeometry")
            assert geom is not None, f"Cell {cell.get('id')} missing geometry"

    def test_edge_cells_have_source_target(self, sample_graph, tmp_path):
        renderer = DrawioRenderer()
        output = renderer.render(sample_graph, tmp_path)
        tree = ET.parse(str(output))
        root = tree.getroot()

        for cell in root.findall(".//mxCell[@edge='1']"):
            assert cell.get("source"), f"Edge {cell.get('id')} missing source"
            assert cell.get("target"), f"Edge {cell.get('id')} missing target"


class TestLucidchartRenderer:
    def test_renders_zip_file(self, sample_graph, tmp_path):
        renderer = LucidchartRenderer()
        output = renderer.render(sample_graph, tmp_path)
        assert output.exists()
        assert output.suffix == ".lucid"
        assert zipfile.is_zipfile(str(output))

    def test_zip_contains_document_json(self, sample_graph, tmp_path):
        renderer = LucidchartRenderer()
        output = renderer.render(sample_graph, tmp_path)
        with zipfile.ZipFile(output, "r") as zf:
            assert "document.json" in zf.namelist()

    def test_document_json_structure(self, sample_graph, tmp_path):
        renderer = LucidchartRenderer()
        output = renderer.render(sample_graph, tmp_path)
        with zipfile.ZipFile(output, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        assert "pages" in doc
        assert len(doc["pages"]) == 1

        page = doc["pages"][0]
        assert "shapes" in page
        assert "lines" in page

    def test_shapes_have_bounding_box(self, sample_graph, tmp_path):
        renderer = LucidchartRenderer()
        output = renderer.render(sample_graph, tmp_path)
        with zipfile.ZipFile(output, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        page = doc["pages"][0]
        for shape in page["shapes"]:
            bb = shape.get("boundingBox", {})
            assert "x" in bb
            assert "y" in bb
            assert "w" in bb
            assert "h" in bb

    def test_lines_have_endpoints(self, sample_graph, tmp_path):
        renderer = LucidchartRenderer()
        output = renderer.render(sample_graph, tmp_path)
        with zipfile.ZipFile(output, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        page = doc["pages"][0]
        for line in page["lines"]:
            assert "endpoint1" in line
            assert "endpoint2" in line
            assert line["endpoint1"]["type"] == "shapeEndpoint"

    def test_container_shapes_exist(self, sample_graph, tmp_path):
        renderer = LucidchartRenderer()
        output = renderer.render(sample_graph, tmp_path)
        with zipfile.ZipFile(output, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        page = doc["pages"][0]
        containers = [s for s in page["shapes"] if "Container" in s.get("type", "")]
        assert len(containers) == 3  # vnet + 2 subnets

    def test_node_shapes_have_custom_data(self, sample_graph, tmp_path):
        renderer = LucidchartRenderer()
        output = renderer.render(sample_graph, tmp_path)
        with zipfile.ZipFile(output, "r") as zf:
            doc = json.loads(zf.read("document.json"))

        page = doc["pages"][0]
        node_shapes = [s for s in page["shapes"] if s.get("type") == "rectangle"]
        for shape in node_shapes:
            custom_data = shape.get("customData", [])
            keys = [d["key"] for d in custom_data]
            assert "resourceType" in keys


class TestRendererOutputPath:
    def test_directory_output(self, tmp_path):
        renderer = MermaidRenderer()
        result = renderer.output_file(tmp_path, "my-project")
        assert result == tmp_path / "my-project.md"

    def test_file_output(self, tmp_path):
        renderer = MermaidRenderer()
        file_path = tmp_path / "custom.md"
        result = renderer.output_file(file_path, "my-project")
        assert result == file_path
