"""IP address resolution from Azure resource properties.

Extracts private IPs, public IPs, frontend IPs, and listener IPs
from NICs, Load Balancers, Application Gateways, and Public IP resources.
"""

from __future__ import annotations

from typing import Any


class IPResolver:
    """Resolves IP addresses for Azure resources from discovery data."""

    def __init__(self, resources: list[dict[str, Any]]) -> None:
        self._nic_private_ips: dict[str, list[str]] = {}
        self._nic_public_ip_ids: dict[str, list[str]] = {}
        self._public_ip_addresses: dict[str, str] = {}
        self._build_indexes(resources)

    def _build_indexes(self, resources: list[dict[str, Any]]) -> None:
        for resource in resources:
            rid = (resource.get("id") or "").lower()
            rtype = (resource.get("type") or "").lower()
            props = resource.get("properties") or {}

            if rtype == "microsoft.network/publicipaddresses":
                ip_addr = props.get("ipAddress", "")
                if ip_addr:
                    self._public_ip_addresses[rid] = ip_addr

            elif rtype == "microsoft.network/networkinterfaces":
                for ip_config in props.get("ipConfigurations", []):
                    ip_props = ip_config.get("properties") or {}
                    priv_ip = ip_props.get("privateIPAddress", "")
                    if priv_ip:
                        self._nic_private_ips.setdefault(rid, []).append(priv_ip)
                    pip_ref = ip_props.get("publicIPAddress") or {}
                    pip_id = (pip_ref.get("id") or "").lower() if isinstance(pip_ref, dict) else ""
                    if pip_id:
                        self._nic_public_ip_ids.setdefault(rid, []).append(pip_id)

    def get_vm_ips(self, vm_resource: dict[str, Any]) -> list[str]:
        """Get displayable IP strings for a VM (private + public)."""
        ips: list[str] = []
        props = vm_resource.get("properties") or {}
        nic_refs = (props.get("networkProfile") or {}).get("networkInterfaces", [])
        for nic_ref in nic_refs:
            nic_id = (nic_ref.get("id") or "").lower() if isinstance(nic_ref, dict) else ""
            if not nic_id:
                continue
            for priv_ip in self._nic_private_ips.get(nic_id, []):
                ips.append(f"priv: {priv_ip}")
            for pip_id in self._nic_public_ip_ids.get(nic_id, []):
                pub_ip = self._public_ip_addresses.get(pip_id, "")
                if pub_ip:
                    ips.append(f"pub: {pub_ip}")
        return ips

    def get_lb_frontend_ips(self, lb_resource: dict[str, Any]) -> list[str]:
        """Get frontend IPs for a Load Balancer."""
        ips: list[str] = []
        props = lb_resource.get("properties") or {}
        for fe_config in props.get("frontendIPConfigurations", []):
            fe_props = fe_config.get("properties") or {}
            priv_ip = fe_props.get("privateIPAddress", "")
            if priv_ip:
                ips.append(f"fe: {priv_ip}")
            pip_ref = fe_props.get("publicIPAddress") or {}
            pip_id = (pip_ref.get("id") or "").lower() if isinstance(pip_ref, dict) else ""
            if pip_id:
                pub_ip = self._public_ip_addresses.get(pip_id, "")
                if pub_ip:
                    ips.append(f"fe: {pub_ip}")
        return ips

    def get_appgw_listener_ips(self, appgw_resource: dict[str, Any]) -> list[str]:
        """Get frontend IPs for an Application Gateway."""
        return self.get_lb_frontend_ips(appgw_resource)  # Same structure

    def get_resource_ip_display(self, resource: dict[str, Any]) -> str:
        """Get a concise IP display string for any resource type."""
        rtype = (resource.get("type") or "").lower()
        ips: list[str] = []
        if rtype == "microsoft.compute/virtualmachines":
            ips = self.get_vm_ips(resource)
        elif rtype == "microsoft.network/loadbalancers":
            ips = self.get_lb_frontend_ips(resource)
        elif rtype == "microsoft.network/applicationgateways":
            ips = self.get_appgw_listener_ips(resource)
        elif rtype == "microsoft.network/publicipaddresses":
            props = resource.get("properties") or {}
            ip = props.get("ipAddress", "")
            if ip:
                ips = [ip]
        return " | ".join(ips)

    def has_public_ip(self, resource: dict[str, Any]) -> bool:
        """Check if a resource has any public IP association."""
        rtype = (resource.get("type") or "").lower()
        if rtype == "microsoft.network/publicipaddresses":
            return True
        if rtype == "microsoft.compute/virtualmachines":
            return any(ip.startswith("pub:") for ip in self.get_vm_ips(resource))
        if rtype in ("microsoft.network/loadbalancers", "microsoft.network/applicationgateways"):
            for ip in self.get_lb_frontend_ips(resource):
                if not ip.startswith("fe: 10.") and not ip.startswith("fe: 172.") and not ip.startswith("fe: 192.168."):
                    return True
        return False
