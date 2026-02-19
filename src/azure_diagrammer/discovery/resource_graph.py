"""Azure Resource Graph discovery engine.

Uses KQL queries via the azure-mgmt-resourcegraph SDK to discover
all resources, resource groups, and network topology across subscriptions.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import (
    QueryRequest,
    QueryRequestOptions,
    ResultFormat,
)
from azure.mgmt.resource import SubscriptionClient

from azure_diagrammer.config import Config, ResourceFilter

logger = logging.getLogger(__name__)


class ResourceGraphDiscovery:
    """Discovers Azure resources via Azure Resource Graph KQL queries."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.credential = DefaultAzureCredential()
        self.client = ResourceGraphClient(self.credential)
        self._subscription_ids: list[str] | None = None

    @property
    def subscription_ids(self) -> list[str]:
        """Resolve subscription IDs, expanding 'all' if needed."""
        if self._subscription_ids is None:
            if "all" in self.config.subscription_ids:
                self._subscription_ids = self._list_all_subscriptions()
            else:
                self._subscription_ids = self.config.subscription_ids
        return self._subscription_ids

    def _list_all_subscriptions(self) -> list[str]:
        """List all accessible subscription IDs."""
        sub_client = SubscriptionClient(self.credential)
        subs = []
        for sub in sub_client.subscriptions.list():
            if sub.state and sub.state.lower() == "enabled":
                subs.append(sub.subscription_id)
        logger.info("Discovered %d enabled subscriptions", len(subs))
        return subs

    def _execute_query(self, kql: str) -> list[dict[str, Any]]:
        """Execute a KQL query against Resource Graph with pagination.

        Args:
            kql: KQL query string.

        Returns:
            List of result rows as dictionaries.
        """
        all_results: list[dict[str, Any]] = []
        skip_token = None

        while True:
            options = QueryRequestOptions(
                result_format=ResultFormat.OBJECT_ARRAY,
                top=1000,
                skip_token=skip_token,
            )
            request = QueryRequest(
                subscriptions=self.subscription_ids,
                query=kql,
                options=options,
            )
            response = self.client.resources(request)

            if response.data:
                all_results.extend(response.data)

            skip_token = response.skip_token
            if not skip_token:
                break

        logger.info("Query returned %d results: %s...", len(all_results), kql[:80])
        return all_results

    def discover_all_resources(
        self, resource_filter: ResourceFilter | None = None
    ) -> list[dict[str, Any]]:
        """Discover all resources across target subscriptions.

        Args:
            resource_filter: Optional filters for resource groups, types, tags.

        Returns:
            List of resource dictionaries with full properties.
        """
        rf = resource_filter or self.config.resource_filter
        kql = "Resources"
        where_clauses = []

        if rf.include_resource_groups:
            rg_list = ", ".join(f"'{rg}'" for rg in rf.include_resource_groups)
            where_clauses.append(f"resourceGroup in~ ({rg_list})")

        if rf.exclude_resource_types:
            for rtype in rf.exclude_resource_types:
                where_clauses.append(f"type !~ '{rtype}'")

        if rf.filter_tags:
            for key, value in rf.filter_tags.items():
                where_clauses.append(f"tags['{key}'] == '{value}'")

        if where_clauses:
            kql += " | where " + " and ".join(where_clauses)

        kql += " | project id, name, type, location, resourceGroup, subscriptionId, tags, properties, sku, kind"

        return self._execute_query(kql)

    def discover_resource_groups(self) -> list[dict[str, Any]]:
        """Discover all resource groups across target subscriptions."""
        kql = (
            "ResourceContainers "
            "| where type =~ 'microsoft.resources/subscriptions/resourcegroups' "
            "| project id, name, location, subscriptionId, tags, properties"
        )
        return self._execute_query(kql)

    def discover_subscriptions(self) -> list[dict[str, Any]]:
        """Discover subscription metadata."""
        kql = (
            "ResourceContainers "
            "| where type =~ 'microsoft.resources/subscriptions' "
            "| project id, name, subscriptionId, properties"
        )
        return self._execute_query(kql)

    def discover_network_resources(self) -> dict[str, list[dict[str, Any]]]:
        """Discover all network-related resources organized by type.

        Returns:
            Dictionary keyed by resource type with lists of resources.
        """
        network_types = {
            "vnets": "microsoft.network/virtualnetworks",
            "subnets": "microsoft.network/virtualnetworks/subnets",
            "nsgs": "microsoft.network/networksecuritygroups",
            "nics": "microsoft.network/networkinterfaces",
            "public_ips": "microsoft.network/publicipaddresses",
            "load_balancers": "microsoft.network/loadbalancers",
            "app_gateways": "microsoft.network/applicationgateways",
            "firewalls": "microsoft.network/azurefirewalls",
            "private_endpoints": "microsoft.network/privateendpoints",
            "route_tables": "microsoft.network/routetables",
            "vnet_gateways": "microsoft.network/virtualnetworkgateways",
        }

        results = {}
        for key, rtype in network_types.items():
            kql = (
                f"Resources "
                f"| where type =~ '{rtype}' "
                f"| project id, name, type, location, resourceGroup, subscriptionId, properties"
            )
            results[key] = self._execute_query(kql)

        # Discover VNet peerings separately
        kql = (
            "Resources "
            "| where type =~ 'microsoft.network/virtualnetworks' "
            "| mv-expand peering = properties.virtualNetworkPeerings "
            "| project vnetId=id, vnetName=name, peeringName=peering.name, "
            "remoteVnetId=peering.properties.remoteVirtualNetwork.id, "
            "peeringState=peering.properties.peeringState"
        )
        results["peerings"] = self._execute_query(kql)

        return results

    def discover_compute_resources(self) -> dict[str, list[dict[str, Any]]]:
        """Discover compute resources (VMs, VMSS, App Services, etc.)."""
        compute_types = {
            "vms": "microsoft.compute/virtualmachines",
            "vmss": "microsoft.compute/virtualmachinescalesets",
            "app_services": "microsoft.web/sites",
            "app_service_plans": "microsoft.web/serverfarms",
            "aks_clusters": "microsoft.containerservice/managedclusters",
            "container_instances": "microsoft.containerinstance/containergroups",
            "container_registries": "microsoft.containerregistry/registries",
        }

        results = {}
        for key, rtype in compute_types.items():
            kql = (
                f"Resources "
                f"| where type =~ '{rtype}' "
                f"| project id, name, type, location, resourceGroup, subscriptionId, properties, sku, kind"
            )
            results[key] = self._execute_query(kql)

        return results

    def discover_data_resources(self) -> dict[str, list[dict[str, Any]]]:
        """Discover data/database resources."""
        data_types = {
            "sql_servers": "microsoft.sql/servers",
            "sql_databases": "microsoft.sql/servers/databases",
            "cosmos_accounts": "microsoft.documentdb/databaseaccounts",
            "redis_caches": "microsoft.cache/redis",
            "storage_accounts": "microsoft.storage/storageaccounts",
            "mysql_servers": "microsoft.dbformysql/flexibleservers",
            "postgresql_servers": "microsoft.dbforpostgresql/flexibleservers",
        }

        results = {}
        for key, rtype in data_types.items():
            kql = (
                f"Resources "
                f"| where type =~ '{rtype}' "
                f"| project id, name, type, location, resourceGroup, subscriptionId, properties, sku, kind"
            )
            results[key] = self._execute_query(kql)

        return results

    def discover_nsg_rules(self) -> list[dict[str, Any]]:
        """Discover NSG security rules for data flow analysis."""
        kql = (
            "Resources "
            "| where type =~ 'microsoft.network/networksecuritygroups' "
            "| mv-expand rule = properties.securityRules "
            "| project nsgId=id, nsgName=name, resourceGroup, "
            "ruleName=rule.name, "
            "direction=rule.properties.direction, "
            "access=rule.properties.access, "
            "protocol=rule.properties.protocol, "
            "sourceAddressPrefix=rule.properties.sourceAddressPrefix, "
            "sourcePortRange=rule.properties.sourcePortRange, "
            "destinationAddressPrefix=rule.properties.destinationAddressPrefix, "
            "destinationPortRange=rule.properties.destinationPortRange, "
            "priority=rule.properties.priority"
        )
        return self._execute_query(kql)
