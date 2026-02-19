"""Tests for the core graph model and Azure type mappings."""

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
from azure_diagrammer.model.azure_types import (
    AZURE_RESOURCE_MAP,
    DEFAULT_RESOURCE_META,
    ResourceCategory,
    get_resource_meta,
    is_container_type,
)
from azure_diagrammer.model.layout import LayoutStrategy, layout_page


class TestDiagramNode:
    def test_default_node(self):
        node = DiagramNode(id="n1", name="Test VM")
        assert node.id == "n1"
        assert node.name == "Test VM"
        assert node.position.x == 0.0
        assert node.size.w == 120.0
        assert node.group_id is None

    def test_node_with_properties(self):
        node = DiagramNode(
            id="n2",
            name="web-vm",
            azure_resource_type="microsoft.compute/virtualmachines",
            azure_resource_id="/subscriptions/sub1/providers/Microsoft.Compute/virtualMachines/web-vm",
            position=Position(x=100, y=200),
            size=Size(w=150, h=100),
            group_id="group-1",
            display_info="Standard_D2s_v3",
        )
        assert node.position.x == 100
        assert node.size.h == 100
        assert node.group_id == "group-1"
        assert node.display_info == "Standard_D2s_v3"


class TestDiagramEdge:
    def test_default_edge(self):
        edge = DiagramEdge(id="e1", source_id="n1", target_id="n2")
        assert edge.edge_type == EdgeType.DEPENDENCY
        assert not edge.bidirectional
        assert edge.label == ""

    def test_data_flow_edge(self):
        edge = DiagramEdge(
            id="e2",
            source_id="n1",
            target_id="n2",
            label="SQL 1433",
            edge_type=EdgeType.DATA_FLOW,
        )
        assert edge.label == "SQL 1433"
        assert edge.edge_type == EdgeType.DATA_FLOW


class TestDiagramGroup:
    def test_default_group(self):
        group = DiagramGroup(id="g1", name="My VNet")
        assert group.group_type == GroupType.RESOURCE_GROUP
        assert group.children == []
        assert group.parent_id is None

    def test_nested_group(self):
        parent = DiagramGroup(
            id="g1",
            name="VNet",
            group_type=GroupType.VNET,
            children=["g2", "n1"],
        )
        child = DiagramGroup(
            id="g2",
            name="Subnet",
            group_type=GroupType.SUBNET,
            parent_id="g1",
            children=["n1"],
        )
        assert "g2" in parent.children
        assert child.parent_id == "g1"


class TestArchitectureGraph:
    def test_empty_graph(self):
        graph = ArchitectureGraph(project_name="test")
        assert graph.project_name == "test"
        assert graph.pages == []
        assert graph.all_nodes() == []
        assert graph.all_edges() == []

    def test_add_page(self):
        graph = ArchitectureGraph(project_name="test")
        page = DiagramPage(id="p1", title="Network")
        page.nodes.append(DiagramNode(id="n1", name="VM"))
        page.edges.append(DiagramEdge(id="e1", source_id="n1", target_id="n2"))
        graph.add_page(page)

        assert len(graph.pages) == 1
        assert graph.get_page("p1") is not None
        assert graph.get_page("nonexistent") is None
        assert len(graph.all_nodes()) == 1
        assert len(graph.all_edges()) == 1

    def test_multiple_pages(self):
        graph = ArchitectureGraph()
        graph.add_page(DiagramPage(id="p1", title="Page 1"))
        graph.add_page(DiagramPage(id="p2", title="Page 2"))
        assert len(graph.pages) == 2


class TestAzureTypes:
    def test_known_resource_type(self):
        meta = get_resource_meta("microsoft.compute/virtualmachines")
        assert meta.display_name == "Virtual Machine"
        assert meta.short_name == "VM"
        assert meta.category == ResourceCategory.COMPUTE
        assert not meta.is_container

    def test_case_insensitive(self):
        meta = get_resource_meta("Microsoft.Compute/VirtualMachines")
        assert meta.display_name == "Virtual Machine"

    def test_unknown_resource_type(self):
        meta = get_resource_meta("microsoft.unknown/something")
        assert meta == DEFAULT_RESOURCE_META
        assert meta.category == ResourceCategory.OTHER

    def test_container_types(self):
        assert is_container_type("microsoft.network/virtualnetworks")
        assert is_container_type("microsoft.network/virtualnetworks/subnets")
        assert not is_container_type("microsoft.compute/virtualmachines")

    def test_all_mapped_types_have_required_fields(self):
        for rtype, meta in AZURE_RESOURCE_MAP.items():
            assert meta.display_name, f"{rtype} missing display_name"
            assert meta.short_name, f"{rtype} missing short_name"
            assert meta.fill_color.startswith("#"), f"{rtype} invalid fill_color"
            assert meta.stroke_color.startswith("#"), f"{rtype} invalid stroke_color"
            assert meta.icon_file, f"{rtype} missing icon_file"


class TestLayout:
    def test_hierarchical_layout_positions_nodes(self):
        page = DiagramPage(id="test", title="Test")
        page.nodes = [
            DiagramNode(id="n1", name="Node 1"),
            DiagramNode(id="n2", name="Node 2"),
        ]
        result = layout_page(page, LayoutStrategy.HIERARCHICAL)
        # Nodes should have been positioned (not at 0,0 or at different positions)
        positions = [(n.position.x, n.position.y) for n in result.nodes]
        assert len(positions) == 2

    def test_hierarchical_layout_with_groups(self):
        page = DiagramPage(id="test", title="Test")
        group = DiagramGroup(
            id="g1", name="Group", children=["n1", "n2"]
        )
        page.groups = [group]
        page.nodes = [
            DiagramNode(id="n1", name="Node 1"),
            DiagramNode(id="n2", name="Node 2"),
        ]
        result = layout_page(page, LayoutStrategy.HIERARCHICAL)
        assert result.groups[0].bounding_box.w > 0
        assert result.groups[0].bounding_box.h > 0

    def test_grid_layout(self):
        page = DiagramPage(id="test", title="Test")
        for i in range(4):
            group = DiagramGroup(id=f"g{i}", name=f"Group {i}", children=[f"n{i}"])
            page.groups.append(group)
            page.nodes.append(DiagramNode(id=f"n{i}", name=f"Node {i}"))

        result = layout_page(page, LayoutStrategy.GRID)
        # Groups should be positioned in a grid
        xs = [g.bounding_box.x for g in result.groups]
        assert len(set(xs)) > 1  # Not all in the same column

    def test_left_to_right_layout(self):
        page = DiagramPage(id="test", title="Test")
        page.groups = [
            DiagramGroup(id="g1", name="Tier 1", children=["n1"]),
            DiagramGroup(id="g2", name="Tier 2", children=["n2"]),
        ]
        page.nodes = [
            DiagramNode(id="n1", name="Frontend"),
            DiagramNode(id="n2", name="Backend"),
        ]
        result = layout_page(page, LayoutStrategy.LEFT_TO_RIGHT)
        # Second group should be to the right of the first
        assert result.groups[1].bounding_box.x > result.groups[0].bounding_box.x
