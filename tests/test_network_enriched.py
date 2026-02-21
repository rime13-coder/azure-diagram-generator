"""Tests for enriched network template features.

Covers:
- NSG names inline in subnet labels
- Subnet delegation nodes
- Route table placement and edges
- icon_path set on nodes
"""

import pytest

from azure_diagrammer.discovery.relationships import build_relationship_graph
from azure_diagrammer.templates.network import build_network_page
from tests.fixtures.sample_resources import (
    SAMPLE_NETWORK_RESOURCES,
    SAMPLE_RESOURCES,
)


@pytest.fixture
def network_page():
    """Build a network page from sample data."""
    relationships = build_relationship_graph(SAMPLE_RESOURCES)
    return build_network_page(
        SAMPLE_NETWORK_RESOURCES,
        relationships,
        all_resources=SAMPLE_RESOURCES,
    )


class TestNsgInlineInSubnetLabel:
    def test_web_subnet_label_includes_nsg_name(self, network_page):
        """web-subnet has web-nsg associated; label should contain NSG name."""
        subnet_group = next(
            (g for g in network_page.groups if "web-subnet" in (g.azure_resource_id or "")),
            None,
        )
        assert subnet_group is not None
        assert "web-nsg" in subnet_group.name.lower()

    def test_data_subnet_label_no_nsg(self, network_page):
        """data-subnet has no NSG; label should NOT mention NSG."""
        subnet_group = next(
            (g for g in network_page.groups if "data-subnet" in (g.azure_resource_id or "")),
            None,
        )
        assert subnet_group is not None
        # Should be "Subnet data-subnet ..." without NSG
        assert "nsg" not in subnet_group.name.lower()

    def test_inlined_nsg_not_rendered_as_separate_node(self, network_page):
        """NSGs shown inline should not also appear as a separate node."""
        nsg_nodes = [
            n for n in network_page.nodes
            if n.azure_resource_type == "microsoft.network/networksecuritygroups"
            and "web-nsg" in n.name.lower()
        ]
        # web-nsg is inlined in the subnet label, so no separate node
        assert len(nsg_nodes) == 0


class TestSubnetDelegation:
    def test_delegation_node_present_in_data_subnet(self, network_page):
        """data-subnet has a delegation; there should be a delegation text node."""
        delegation_nodes = [
            n for n in network_page.nodes
            if "delegation" in n.id.lower() and "data-subnet" in n.id.lower()
        ]
        assert len(delegation_nodes) == 1
        assert "Microsoft.DBforPostgreSQL" in delegation_nodes[0].name

    def test_no_delegation_in_web_subnet(self, network_page):
        """web-subnet has no delegation; no delegation node should exist."""
        delegation_nodes = [
            n for n in network_page.nodes
            if "delegation" in n.id.lower() and "web-subnet" in n.id.lower()
        ]
        assert len(delegation_nodes) == 0


class TestRouteTable:
    def test_route_table_node_exists(self, network_page):
        """Route table should be rendered as a node."""
        rt_nodes = [
            n for n in network_page.nodes
            if "web-rt" in n.name.lower()
        ]
        assert len(rt_nodes) == 1

    def test_route_table_placed_in_vnet(self, network_page):
        """Route table should be placed inside VNet group (not subnet)."""
        rt_node = next(
            (n for n in network_page.nodes if "web-rt" in n.name.lower()),
            None,
        )
        assert rt_node is not None
        # The group_id should reference the VNet group
        if rt_node.group_id:
            vnet_groups = [g for g in network_page.groups if "vnet" in g.id.lower()]
            vnet_group_ids = {g.id for g in vnet_groups}
            assert rt_node.group_id in vnet_group_ids

    def test_route_table_edge_to_subnet(self, network_page):
        """Route table should have a UDR edge to associated subnet."""
        udr_edges = [
            e for e in network_page.edges
            if "udr" in e.label.lower()
        ]
        assert len(udr_edges) >= 1


class TestVnetLabel:
    def test_vnet_label_includes_address_space(self, network_page):
        """VNet label should include the address space."""
        vnet_group = next(
            (g for g in network_page.groups
             if g.group_type.value == "vnet" and "main-vnet" in g.id.lower()),
            None,
        )
        assert vnet_group is not None
        assert "10.0.0.0/16" in vnet_group.name


class TestSubnetPrefix:
    def test_web_subnet_label_includes_cidr(self, network_page):
        """Subnet label should include the CIDR prefix."""
        subnet_group = next(
            (g for g in network_page.groups if "web-subnet" in (g.azure_resource_id or "")),
            None,
        )
        assert subnet_group is not None
        assert "10.0.1.0/24" in subnet_group.name
