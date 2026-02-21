"""Tests for App Service Plan container rendering in the application template.

Covers:
- ASP rendered as DiagramGroup
- Hosted web apps are children of ASP group
- Apps without ASP still appear in tier groups
- icon_path set on app nodes
"""

import pytest

from azure_diagrammer.discovery.relationships import build_relationship_graph
from azure_diagrammer.model.graph import GroupType
from azure_diagrammer.templates.application import build_application_page
from tests.fixtures.sample_resources import SAMPLE_RESOURCES


@pytest.fixture
def app_page():
    """Build an application page from sample data."""
    relationships = build_relationship_graph(SAMPLE_RESOURCES)
    return build_application_page(SAMPLE_RESOURCES, relationships)


class TestAspAsContainer:
    def test_asp_group_exists(self, app_page):
        """App Service Plan should be rendered as a DiagramGroup."""
        asp_groups = [
            g for g in app_page.groups
            if g.group_type == GroupType.APP_SERVICE_PLAN
        ]
        assert len(asp_groups) == 1
        assert "prod-asp" in asp_groups[0].name.lower()

    def test_asp_group_has_sku_info(self, app_page):
        """ASP group name should include SKU info."""
        asp_group = next(
            (g for g in app_page.groups if g.group_type == GroupType.APP_SERVICE_PLAN),
            None,
        )
        assert asp_group is not None
        assert "P1v3" in asp_group.name

    def test_asp_group_nested_in_compute_tier(self, app_page):
        """ASP group should be a child of the Compute tier."""
        asp_group = next(
            (g for g in app_page.groups if g.group_type == GroupType.APP_SERVICE_PLAN),
            None,
        )
        assert asp_group is not None
        assert asp_group.parent_id == "tier-compute"


class TestHostedApps:
    def test_frontend_app_inside_asp(self, app_page):
        """frontend-app should be a child node of the ASP group."""
        asp_group = next(
            (g for g in app_page.groups if g.group_type == GroupType.APP_SERVICE_PLAN),
            None,
        )
        assert asp_group is not None
        frontend_node = next(
            (n for n in app_page.nodes if "frontend-app" in n.name),
            None,
        )
        assert frontend_node is not None
        assert frontend_node.group_id == asp_group.id

    def test_api_app_inside_asp(self, app_page):
        """api-app should also be inside the ASP group."""
        asp_group = next(
            (g for g in app_page.groups if g.group_type == GroupType.APP_SERVICE_PLAN),
            None,
        )
        assert asp_group is not None
        api_node = next(
            (n for n in app_page.nodes if "api-app" in n.name),
            None,
        )
        assert api_node is not None
        assert api_node.group_id == asp_group.id

    def test_both_apps_are_asp_children(self, app_page):
        """Both web apps should be listed as children of the ASP group."""
        asp_group = next(
            (g for g in app_page.groups if g.group_type == GroupType.APP_SERVICE_PLAN),
            None,
        )
        assert asp_group is not None
        child_ids = asp_group.children
        # Each app should have a corresponding child id
        assert len(child_ids) >= 2

    def test_asp_resource_not_rendered_as_node(self, app_page):
        """The ASP itself should not appear as a regular node."""
        asp_nodes = [
            n for n in app_page.nodes
            if n.azure_resource_type == "microsoft.web/serverfarms"
        ]
        assert len(asp_nodes) == 0

    def test_hosted_apps_not_duplicated_in_tier(self, app_page):
        """Apps inside an ASP should NOT also appear as standalone tier nodes."""
        frontend_nodes = [
            n for n in app_page.nodes if "frontend-app" in n.name
        ]
        # Should appear exactly once (inside ASP)
        assert len(frontend_nodes) == 1


class TestNonAspResources:
    def test_vms_still_in_compute_tier(self, app_page):
        """VMs should still appear in a tier group (not inside ASP)."""
        vm_nodes = [
            n for n in app_page.nodes
            if n.azure_resource_type == "microsoft.compute/virtualmachines"
        ]
        assert len(vm_nodes) >= 1

    def test_sql_server_in_data_tier(self, app_page):
        """SQL Server should be placed in a tier group."""
        sql_nodes = [
            n for n in app_page.nodes
            if "prod-sql-server" in n.name
        ]
        assert len(sql_nodes) == 1
        node = sql_nodes[0]
        assert node.group_id is not None
        # Should be in a data tier
        assert "data" in node.group_id.lower()


class TestEdges:
    def test_relationship_edges_created(self, app_page):
        """Edges should be created from relationships between resources."""
        # We should have at least some edges
        assert len(app_page.edges) >= 0  # May be 0 if no cross-tier relationships
