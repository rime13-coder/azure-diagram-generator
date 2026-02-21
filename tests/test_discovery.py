"""Tests for the Azure discovery engine (relationship inference and data flow)."""

import pytest

from azure_diagrammer.discovery.relationships import (
    ResourceRelationship,
    build_relationship_graph,
)
from azure_diagrammer.discovery.data_flow import (
    DataFlow,
    discover_data_flows,
)
from tests.fixtures.sample_resources import (
    SAMPLE_NSG_RULES,
    SAMPLE_RESOURCES,
)


class TestRelationshipInference:
    def test_vm_to_nic(self):
        """VM should have a has_nic relationship to its NIC."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        vm_nic_rels = [
            r for r in rels
            if r.relationship_type == "has_nic"
            and "web-vm-01" in r.source_id
        ]
        assert len(vm_nic_rels) == 1
        assert "web-vm-01-nic" in vm_nic_rels[0].target_id

    def test_nic_to_subnet(self):
        """NIC should have an in_subnet relationship."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        nic_subnet_rels = [
            r for r in rels
            if r.relationship_type == "in_subnet"
            and "web-vm-01-nic" in r.source_id
        ]
        assert len(nic_subnet_rels) == 1
        assert "web-subnet" in nic_subnet_rels[0].target_id

    def test_nic_to_public_ip(self):
        """NIC with public IP should have has_public_ip relationship."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        pip_rels = [
            r for r in rels
            if r.relationship_type == "has_public_ip"
        ]
        assert len(pip_rels) >= 1
        assert "web-vm-01-pip" in pip_rels[0].target_id

    def test_nic_to_nsg(self):
        """NIC with NSG should have secured_by relationship."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        nsg_rels = [
            r for r in rels
            if r.relationship_type == "secured_by"
        ]
        assert len(nsg_rels) >= 1

    def test_vnet_peering(self):
        """VNet with peering should have peered_with relationship."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        peering_rels = [
            r for r in rels
            if r.relationship_type == "peered_with"
        ]
        assert len(peering_rels) >= 1
        assert "hub-vnet" in peering_rels[0].target_id

    def test_private_endpoint_to_service(self):
        """Private endpoint should link to its target service."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        pe_rels = [
            r for r in rels
            if r.relationship_type == "private_link_to"
        ]
        assert len(pe_rels) >= 1
        assert "prod-sql-server" in pe_rels[0].target_id

    def test_private_endpoint_to_subnet(self):
        """Private endpoint should be associated with a subnet."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        pe_subnet_rels = [
            r for r in rels
            if r.relationship_type == "in_subnet"
            and "privateendpoints" in r.source_id
        ]
        assert len(pe_subnet_rels) >= 1
        assert "data-subnet" in pe_subnet_rels[0].target_id

    def test_nsg_applied_to_subnet(self):
        """NSG should be applied to its subnet."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        nsg_subnet_rels = [
            r for r in rels
            if r.relationship_type == "applied_to"
            and "web-nsg" in r.source_id
        ]
        assert len(nsg_subnet_rels) >= 1

    def test_load_balancer_to_backends(self):
        """Load balancer should link to backend NICs."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        lb_rels = [
            r for r in rels
            if r.relationship_type == "load_balances"
        ]
        assert len(lb_rels) == 2  # Two backend NICs

    def test_sql_to_private_endpoint(self):
        """SQL Server should have has_private_endpoint relationship."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        sql_pe_rels = [
            r for r in rels
            if r.relationship_type == "has_private_endpoint"
            and "prod-sql-server" in r.source_id
        ]
        assert len(sql_pe_rels) >= 1

    def test_relationship_equality(self):
        r1 = ResourceRelationship("a", "b", "test")
        r2 = ResourceRelationship("a", "b", "test")
        r3 = ResourceRelationship("a", "c", "test")
        assert r1 == r2
        assert r1 != r3
        assert hash(r1) == hash(r2)

    def test_empty_resources(self):
        rels = build_relationship_graph([])
        assert rels == []


class TestDataFlowDiscovery:
    def test_nsg_allow_rules_generate_flows(self):
        """NSG allow rules should generate data flow entries."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        flows = discover_data_flows(SAMPLE_RESOURCES, rels, SAMPLE_NSG_RULES)

        # Should have flows from the HTTP and HTTPS allow rules
        nsg_flows = [f for f in flows if f.flow_type == "network"]
        assert len(nsg_flows) >= 2

        # Check that port info is captured
        http_flows = [f for f in nsg_flows if "80" in f.port]
        assert len(http_flows) >= 1

    def test_deny_rules_included_with_deny_access(self):
        """NSG deny rules should generate data flows with access='Deny'."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        flows = discover_data_flows(SAMPLE_RESOURCES, rels, SAMPLE_NSG_RULES)
        deny_flows = [f for f in flows if f.access == "Deny"]
        assert len(deny_flows) >= 1
        # Deny flows should have DENY in their label
        for df in deny_flows:
            assert "DENY" in df.label

    def test_private_endpoint_flows(self):
        """Private endpoints should generate private_link flows."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        flows = discover_data_flows(SAMPLE_RESOURCES, rels)
        pe_flows = [f for f in flows if f.flow_type == "private_link"]
        assert len(pe_flows) >= 1

    def test_service_endpoint_flows(self):
        """VNet service endpoints should generate flows."""
        rels = build_relationship_graph(SAMPLE_RESOURCES)
        flows = discover_data_flows(SAMPLE_RESOURCES, rels)
        se_flows = [f for f in flows if f.flow_type == "service_endpoint"]
        assert len(se_flows) >= 2  # Microsoft.Sql and Microsoft.Storage

    def test_data_flow_label(self):
        flow = DataFlow(source="a", destination="b", protocol="TCP", port="443")
        assert flow.label == "TCP 443"

    def test_data_flow_empty_label(self):
        flow = DataFlow(source="a", destination="b")
        assert flow.label == ""
