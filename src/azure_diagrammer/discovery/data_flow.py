"""Data flow discovery from NSG rules, private endpoints, and service endpoints.

Analyzes network security rules and connectivity patterns to infer
directional data flows between resources/subnets.
"""

from __future__ import annotations

import logging
from typing import Any

from azure_diagrammer.discovery.relationships import ResourceRelationship

logger = logging.getLogger(__name__)


class DataFlow:
    """A directed data flow between two endpoints."""

    def __init__(
        self,
        source: str,
        destination: str,
        protocol: str = "",
        port: str = "",
        label: str = "",
        flow_type: str = "network",  # network, private_link, service_endpoint, diagnostic
    ) -> None:
        self.source = source
        self.destination = destination
        self.protocol = protocol
        self.port = port
        self.label = label or self._build_label()
        self.flow_type = flow_type

    def _build_label(self) -> str:
        parts = []
        if self.protocol and self.protocol != "*":
            parts.append(self.protocol.upper())
        if self.port and self.port != "*":
            parts.append(self.port)
        return " ".join(parts) if parts else ""

    def __repr__(self) -> str:
        return f"DataFlow({self.source} -> {self.destination} [{self.label}])"


def discover_data_flows(
    resources: list[dict[str, Any]],
    relationships: list[ResourceRelationship],
    nsg_rules: list[dict[str, Any]] | None = None,
) -> list[DataFlow]:
    """Discover data flows from NSG rules, private endpoints, and service endpoints.

    Args:
        resources: All discovered Azure resources.
        relationships: Inferred relationships from relationships.py.
        nsg_rules: NSG rule data from resource_graph.discover_nsg_rules().

    Returns:
        List of directional DataFlow objects.
    """
    flows: list[DataFlow] = []

    if nsg_rules:
        flows.extend(_flows_from_nsg_rules(nsg_rules))

    flows.extend(_flows_from_private_endpoints(resources, relationships))
    flows.extend(_flows_from_service_endpoints(resources))
    flows.extend(_flows_from_diagnostic_settings(resources))

    logger.info("Discovered %d data flows", len(flows))
    return flows


def _flows_from_nsg_rules(nsg_rules: list[dict[str, Any]]) -> list[DataFlow]:
    """Infer data flows from NSG allow rules.

    Only processes Allow rules in the Inbound direction to determine
    what traffic can reach what destinations.
    """
    flows = []

    for rule in nsg_rules:
        access = (rule.get("access") or "").lower()
        direction = (rule.get("direction") or "").lower()

        # Only process allow rules
        if access != "allow":
            continue

        source = rule.get("sourceAddressPrefix", "*")
        destination = rule.get("destinationAddressPrefix", "*")
        protocol = rule.get("protocol", "*")
        dest_port = rule.get("destinationPortRange", "*")
        nsg_name = rule.get("nsgName", "")
        rule_name = rule.get("ruleName", "")

        # Skip overly broad rules (*, VirtualNetwork -> VirtualNetwork)
        if source == "*" and destination == "*":
            continue

        label_parts = []
        if protocol and protocol != "*":
            label_parts.append(protocol.upper())
        if dest_port and dest_port != "*":
            label_parts.append(str(dest_port))
        label = " ".join(label_parts)

        if direction == "inbound":
            flows.append(
                DataFlow(
                    source=source,
                    destination=f"{nsg_name} ({destination})",
                    protocol=protocol,
                    port=str(dest_port),
                    label=label,
                    flow_type="network",
                )
            )
        elif direction == "outbound":
            flows.append(
                DataFlow(
                    source=f"{nsg_name} ({source})",
                    destination=destination,
                    protocol=protocol,
                    port=str(dest_port),
                    label=label,
                    flow_type="network",
                )
            )

    return flows


def _flows_from_private_endpoints(
    resources: list[dict[str, Any]],
    relationships: list[ResourceRelationship],
) -> list[DataFlow]:
    """Create flows for private endpoint connections.

    A private endpoint represents secure connectivity from a VNet to a
    PaaS service (SQL, Storage, Cosmos, etc.).
    """
    flows = []

    # Build a quick lookup of PE relationships
    pe_to_service: dict[str, str] = {}
    pe_to_subnet: dict[str, str] = {}

    for rel in relationships:
        if rel.relationship_type == "private_link_to":
            pe_to_service[rel.source_id] = rel.target_id
        elif rel.relationship_type == "in_subnet" and "/privateendpoints/" in rel.source_id:
            pe_to_subnet[rel.source_id] = rel.target_id

    # Build resource name lookup
    resource_names = {
        r["id"].lower(): r.get("name", r["id"].split("/")[-1])
        for r in resources
        if "id" in r
    }

    for pe_id, service_id in pe_to_service.items():
        subnet_id = pe_to_subnet.get(pe_id, "")
        source_name = _extract_name_from_id(subnet_id) or "VNet"
        target_name = resource_names.get(service_id.lower(), _extract_name_from_id(service_id))

        flows.append(
            DataFlow(
                source=source_name,
                destination=target_name,
                protocol="TCP",
                port="443",
                label=f"Private Link -> {target_name}",
                flow_type="private_link",
            )
        )

    return flows


def _flows_from_service_endpoints(
    resources: list[dict[str, Any]],
) -> list[DataFlow]:
    """Discover flows from VNet service endpoints configured on subnets."""
    flows = []

    for resource in resources:
        rtype = (resource.get("type") or "").lower()
        if rtype != "microsoft.network/virtualnetworks":
            continue

        props = resource.get("properties", {}) or {}
        subnets = props.get("subnets", [])
        vnet_name = resource.get("name", "")

        for subnet in subnets:
            subnet_props = subnet.get("properties", {}) or {}
            subnet_name = subnet.get("name", "")
            service_endpoints = subnet_props.get("serviceEndpoints", [])

            for endpoint in service_endpoints:
                service = endpoint.get("service", "")
                if service:
                    # e.g., Microsoft.Storage, Microsoft.Sql
                    flows.append(
                        DataFlow(
                            source=f"{vnet_name}/{subnet_name}",
                            destination=service,
                            protocol="TCP",
                            label=f"Service Endpoint: {service}",
                            flow_type="service_endpoint",
                        )
                    )

    return flows


def _flows_from_diagnostic_settings(
    resources: list[dict[str, Any]],
) -> list[DataFlow]:
    """Discover diagnostic data flows (logs/metrics to sinks).

    Note: Diagnostic settings are often not returned in Resource Graph.
    This processes resources that have diagnosticSettings in their properties.
    """
    flows = []

    for resource in resources:
        props = resource.get("properties", {}) or {}
        resource_name = resource.get("name", "")

        # Some resources expose diagnostic settings in properties
        diag_settings = props.get("diagnosticSettings", [])
        for setting in diag_settings:
            setting_props = setting.get("properties", {}) or {}

            # Log Analytics workspace
            workspace_id = setting_props.get("workspaceId")
            if workspace_id:
                flows.append(
                    DataFlow(
                        source=resource_name,
                        destination=_extract_name_from_id(workspace_id),
                        label="Diagnostics -> Log Analytics",
                        flow_type="diagnostic",
                    )
                )

            # Storage account
            storage_id = setting_props.get("storageAccountId")
            if storage_id:
                flows.append(
                    DataFlow(
                        source=resource_name,
                        destination=_extract_name_from_id(storage_id),
                        label="Diagnostics -> Storage",
                        flow_type="diagnostic",
                    )
                )

            # Event Hub
            eh_id = setting_props.get("eventHubAuthorizationRuleId")
            if eh_id:
                flows.append(
                    DataFlow(
                        source=resource_name,
                        destination=_extract_name_from_id(eh_id),
                        label="Diagnostics -> Event Hub",
                        flow_type="diagnostic",
                    )
                )

    return flows


def _extract_name_from_id(resource_id: str) -> str:
    """Extract the resource name from an Azure resource ID."""
    if not resource_id:
        return "Unknown"
    parts = resource_id.rstrip("/").split("/")
    return parts[-1] if parts else "Unknown"
