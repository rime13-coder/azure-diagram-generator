"""Tests for the shared display_info builder."""

import pytest

from azure_diagrammer.templates.display_info import (
    build_display_info,
    _format_sku,
    _format_tags,
)


class TestFormatSku:
    def test_sku_with_name(self):
        result = _format_sku({"sku": {"name": "Standard_D2s_v3"}})
        assert "Standard_D2s_v3" in result

    def test_sku_with_name_and_tier(self):
        result = _format_sku({"sku": {"name": "GP_Gen5_2", "tier": "GeneralPurpose"}})
        assert "GP_Gen5_2" in result
        assert "GeneralPurpose" in result

    def test_sku_with_capacity(self):
        result = _format_sku({"sku": {"name": "Standard", "capacity": 2}})
        assert "cap:2" in result

    def test_sku_with_kind(self):
        result = _format_sku({"sku": {"name": "Standard_LRS"}, "kind": "StorageV2"})
        assert "StorageV2" in result

    def test_sku_none(self):
        assert _format_sku({"sku": None}) == ""

    def test_sku_missing(self):
        assert _format_sku({}) == ""

    def test_sku_same_name_tier(self):
        """Tier should be omitted if same as name."""
        result = _format_sku({"sku": {"name": "Standard", "tier": "Standard"}})
        assert result == "Standard"


class TestFormatTags:
    def test_basic_tags(self):
        result = _format_tags({"tags": {"env": "prod", "team": "platform"}})
        assert "env=prod" in result
        assert "team=platform" in result
        assert result.startswith("[")
        assert result.endswith("]")

    def test_max_tags_limit(self):
        tags = {f"key{i}": f"val{i}" for i in range(5)}
        result = _format_tags({"tags": tags}, max_tags=2)
        assert "+3 more" in result

    def test_empty_tags(self):
        assert _format_tags({"tags": {}}) == ""

    def test_none_tags(self):
        assert _format_tags({"tags": None}) == ""

    def test_hidden_tags_filtered(self):
        result = _format_tags({"tags": {"hidden-link:foo": "bar", "env": "prod"}})
        assert "hidden" not in result
        assert "env=prod" in result


class TestBuildDisplayInfo:
    def test_sku_only(self):
        resource = {"sku": {"name": "Standard_D2s_v3"}, "location": "eastus"}
        result = build_display_info(resource, show_sku=True, show_location=False)
        assert "Standard_D2s_v3" in result
        assert "eastus" not in result

    def test_location_only(self):
        resource = {"location": "eastus"}
        result = build_display_info(resource, show_sku=False, show_location=True)
        assert "eastus" in result

    def test_combined(self):
        resource = {
            "sku": {"name": "GP_Gen5_2"},
            "location": "eastus",
            "tags": {"env": "prod"},
        }
        result = build_display_info(
            resource, show_sku=True, show_location=True, show_tags=True
        )
        assert "GP_Gen5_2" in result
        assert "eastus" in result
        assert "env=prod" in result
        assert " | " in result

    def test_empty_resource(self):
        result = build_display_info({})
        assert result == ""

    def test_with_ip_resolver(self):
        from azure_diagrammer.discovery.ip_resolver import IPResolver
        from tests.fixtures.sample_resources import SAMPLE_RESOURCES

        resolver = IPResolver(SAMPLE_RESOURCES)
        vm = SAMPLE_RESOURCES[0]
        result = build_display_info(vm, ip_resolver=resolver, show_ips=True)
        assert "10.0.1.4" in result
