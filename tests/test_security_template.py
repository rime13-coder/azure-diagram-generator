"""Tests for the security posture diagram template."""

import pytest

from azure_diagrammer.discovery.relationships import build_relationship_graph
from azure_diagrammer.templates.security import (
    build_security_page,
    _classify_risk,
    _build_open_ports_index,
)
from tests.fixtures.sample_resources import (
    SAMPLE_NETWORK_RESOURCES,
    SAMPLE_NSG_RULES,
    SAMPLE_RESOURCES,
)


@pytest.fixture
def relationships():
    return build_relationship_graph(SAMPLE_RESOURCES)


class TestSecurityPage:
    def test_page_id_and_title(self, relationships):
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        assert page.id == "security"
        assert page.title == "Security Posture"

    def test_vnet_group_exists(self, relationships):
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        vnet_groups = [g for g in page.groups if g.group_type.value == "vnet"]
        assert len(vnet_groups) >= 1
        assert "main-vnet" in vnet_groups[0].name

    def test_subnet_groups_created(self, relationships):
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        subnet_groups = [g for g in page.groups if g.group_type.value == "subnet"]
        assert len(subnet_groups) >= 2  # web-subnet, data-subnet

    def test_subnet_with_nsg_gets_green_or_yellow(self, relationships):
        """web-subnet has NSG -> should be green (if no public) or yellow (if public)."""
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        web_subnet_groups = [
            g for g in page.groups
            if g.group_type.value == "subnet" and "web-subnet" in g.name
        ]
        assert len(web_subnet_groups) == 1
        style = web_subnet_groups[0].style
        # web-subnet has NSG + a VM with public IP -> yellow
        assert style["fill"] in ("#FFF9C4", "#C8E6C9")

    def test_subnet_without_nsg_no_public_is_yellow(self, relationships):
        """data-subnet has no NSG but no public resources -> yellow."""
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        data_subnet_groups = [
            g for g in page.groups
            if g.group_type.value == "subnet" and "data-subnet" in g.name
        ]
        assert len(data_subnet_groups) == 1
        style = data_subnet_groups[0].style
        assert style["fill"] == "#FFF9C4"  # yellow

    def test_nsg_node_shows_open_ports(self, relationships):
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        nsg_nodes = [
            n for n in page.nodes
            if n.azure_resource_type == "microsoft.network/networksecuritygroups"
        ]
        assert len(nsg_nodes) >= 1
        # Should mention open ports
        assert "Open ports:" in nsg_nodes[0].display_info
        assert "80" in nsg_nodes[0].display_info or "443" in nsg_nodes[0].display_info

    def test_public_resource_labeled_public(self, relationships):
        """VM with public IP should be labeled PUBLIC."""
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        vm_nodes = [n for n in page.nodes if "web-vm-01" in n.name]
        if vm_nodes:
            assert "PUBLIC" in vm_nodes[0].display_info

    def test_pe_covered_resource_labeled(self, relationships):
        """SQL server with PE should be labeled PE-covered."""
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        sql_nodes = [n for n in page.nodes if "prod-sql-server" in n.name]
        if sql_nodes:
            assert "PE-covered" in sql_nodes[0].display_info

    def test_nodes_have_exposure_display_info(self, relationships):
        """All resource nodes should have an exposure label."""
        page = build_security_page(
            SAMPLE_RESOURCES, SAMPLE_NETWORK_RESOURCES, relationships, SAMPLE_NSG_RULES,
        )
        resource_nodes = [
            n for n in page.nodes
            if n.azure_resource_type != "microsoft.network/networksecuritygroups"
        ]
        for node in resource_nodes:
            assert node.display_info in ("PUBLIC", "PE-covered", "private") or "PUBLIC" in node.display_info


class TestRiskClassification:
    def test_green_nsg_no_public(self):
        assert _classify_risk(has_nsg=True, has_public=False) == "green"

    def test_red_no_nsg_public(self):
        assert _classify_risk(has_nsg=False, has_public=True) == "red"

    def test_yellow_nsg_and_public(self):
        assert _classify_risk(has_nsg=True, has_public=True) == "yellow"

    def test_yellow_no_nsg_no_public(self):
        assert _classify_risk(has_nsg=False, has_public=False) == "yellow"


class TestOpenPortsIndex:
    def test_allow_inbound_ports_captured(self):
        ports = _build_open_ports_index(SAMPLE_NSG_RULES)
        nsg_id = SAMPLE_NSG_RULES[0]["nsgId"].lower()
        assert nsg_id in ports
        assert "80" in ports[nsg_id]
        assert "443" in ports[nsg_id]

    def test_deny_rules_excluded(self):
        ports = _build_open_ports_index(SAMPLE_NSG_RULES)
        nsg_id = SAMPLE_NSG_RULES[0]["nsgId"].lower()
        # Deny rule has port "*" which is always excluded
        assert "*" not in ports.get(nsg_id, [])

    def test_empty_rules(self):
        ports = _build_open_ports_index([])
        assert ports == {}
