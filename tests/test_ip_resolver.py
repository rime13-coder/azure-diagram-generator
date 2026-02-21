"""Tests for IP address resolver."""

import pytest

from azure_diagrammer.discovery.ip_resolver import IPResolver
from tests.fixtures.sample_resources import SAMPLE_RESOURCES


class TestIPResolver:
    """Tests for the IPResolver class."""

    def setup_method(self):
        self.resolver = IPResolver(SAMPLE_RESOURCES)

    def test_vm_private_ip(self):
        """VM should resolve private IP from its NIC."""
        vm = SAMPLE_RESOURCES[0]  # web-vm-01
        ips = self.resolver.get_vm_ips(vm)
        assert "priv: 10.0.1.4" in ips

    def test_vm_public_ip(self):
        """VM should resolve public IP from its NIC -> PIP reference."""
        vm = SAMPLE_RESOURCES[0]  # web-vm-01
        ips = self.resolver.get_vm_ips(vm)
        assert "pub: 20.185.100.42" in ips

    def test_vm_without_public_ip(self):
        """VM without public IP should only have private IP."""
        vm = SAMPLE_RESOURCES[1]  # web-vm-02 (no public IP ref)
        ips = self.resolver.get_vm_ips(vm)
        assert "priv: 10.0.1.5" in ips
        assert not any(ip.startswith("pub:") for ip in ips)

    def test_lb_frontend_ip(self):
        """Load Balancer should resolve frontend IPs."""
        lb = SAMPLE_RESOURCES[9]  # web-lb
        ips = self.resolver.get_lb_frontend_ips(lb)
        assert "fe: 10.0.1.100" in ips

    def test_public_ip_resource(self):
        """Public IP resource should return its address."""
        pip = SAMPLE_RESOURCES[10]  # web-vm-01-pip
        display = self.resolver.get_resource_ip_display(pip)
        assert "20.185.100.42" in display

    def test_resource_ip_display_vm(self):
        """get_resource_ip_display should work for VMs."""
        vm = SAMPLE_RESOURCES[0]
        display = self.resolver.get_resource_ip_display(vm)
        assert "10.0.1.4" in display
        assert "20.185.100.42" in display

    def test_resource_ip_display_no_ip(self):
        """Resources without IPs should return empty string."""
        kv = SAMPLE_RESOURCES[11]  # prod-keyvault
        display = self.resolver.get_resource_ip_display(kv)
        assert display == ""

    def test_empty_resources(self):
        """Resolver should handle empty resource list."""
        resolver = IPResolver([])
        assert resolver.get_resource_ip_display({}) == ""

    def test_has_public_ip_vm(self):
        """VM with public IP should be detected."""
        vm = SAMPLE_RESOURCES[0]  # web-vm-01 (has public IP)
        assert self.resolver.has_public_ip(vm) is True

    def test_has_no_public_ip_vm(self):
        """VM without public IP should not be detected as public."""
        vm = SAMPLE_RESOURCES[1]  # web-vm-02 (no public IP)
        assert self.resolver.has_public_ip(vm) is False
