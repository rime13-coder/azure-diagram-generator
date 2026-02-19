"""Network Watcher topology discovery.

Uses the Azure Network Watcher API to discover network topology
(contains/associated relationships) for each resource group.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient

from azure_diagrammer.config import Config

logger = logging.getLogger(__name__)


class TopologyRelationship:
    """A relationship discovered from Network Watcher topology."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
    ) -> None:
        self.source_id = source_id
        self.target_id = target_id
        self.relationship_type = relationship_type  # "Contains" or "Associated"

    def __repr__(self) -> str:
        return (
            f"TopologyRelationship({self.source_id} "
            f"--{self.relationship_type}--> {self.target_id})"
        )


class NetworkTopologyDiscovery:
    """Discovers network topology using Azure Network Watcher."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.credential = DefaultAzureCredential()

    def get_topology_for_subscription(
        self, subscription_id: str
    ) -> list[TopologyRelationship]:
        """Get network topology relationships for all RGs in a subscription.

        Args:
            subscription_id: Azure subscription ID.

        Returns:
            List of topology relationships discovered.
        """
        network_client = NetworkManagementClient(self.credential, subscription_id)
        resource_client = ResourceManagementClient(self.credential, subscription_id)
        all_relationships: list[TopologyRelationship] = []

        # Get all resource groups
        resource_groups = list(resource_client.resource_groups.list())

        for rg in resource_groups:
            try:
                relationships = self._get_topology_for_rg(
                    network_client, rg.name, rg.location
                )
                all_relationships.extend(relationships)
            except Exception as exc:
                # Network Watcher may not be enabled in all regions
                logger.debug(
                    "Could not get topology for RG '%s' in '%s': %s",
                    rg.name,
                    rg.location,
                    exc,
                )

        logger.info(
            "Discovered %d topology relationships in subscription %s",
            len(all_relationships),
            subscription_id,
        )
        return all_relationships

    def _get_topology_for_rg(
        self,
        network_client: NetworkManagementClient,
        resource_group: str,
        location: str,
    ) -> list[TopologyRelationship]:
        """Get topology for a single resource group.

        Args:
            network_client: Network management client.
            resource_group: Resource group name.
            location: Azure region.

        Returns:
            List of topology relationships.
        """
        # Network Watcher name follows convention: NetworkWatcher_<region>
        watcher_rg = "NetworkWatcherRG"
        watcher_name = f"NetworkWatcher_{location}"

        topology = network_client.network_watchers.get_topology(
            resource_group_name=watcher_rg,
            network_watcher_name=watcher_name,
            parameters={"targetResourceGroupName": resource_group},
        )

        relationships: list[TopologyRelationship] = []

        if not topology.resources:
            return relationships

        for resource in topology.resources:
            resource_id = resource.id
            if not resource_id:
                continue

            # Process "associations" (bidirectional relationships)
            if resource.associations:
                for assoc in resource.associations:
                    relationships.append(
                        TopologyRelationship(
                            source_id=resource_id,
                            target_id=assoc.resource_id,
                            relationship_type=assoc.association_type or "Associated",
                        )
                    )

        return relationships

    def get_all_topologies(self) -> list[TopologyRelationship]:
        """Get topology for all configured subscriptions.

        Returns:
            Combined list of all topology relationships.
        """
        all_relationships: list[TopologyRelationship] = []

        subscription_ids = self.config.subscription_ids
        if "all" in subscription_ids:
            from azure.mgmt.subscription import SubscriptionClient

            sub_client = SubscriptionClient(self.credential)
            subscription_ids = [
                sub.subscription_id
                for sub in sub_client.subscriptions.list()
                if sub.state and sub.state.lower() == "enabled"
            ]

        for sub_id in subscription_ids:
            try:
                rels = self.get_topology_for_subscription(sub_id)
                all_relationships.extend(rels)
            except Exception as exc:
                logger.warning(
                    "Failed to get topology for subscription %s: %s", sub_id, exc
                )

        return all_relationships


def topology_to_adjacency(
    relationships: list[TopologyRelationship],
) -> dict[str, list[dict[str, Any]]]:
    """Convert topology relationships to an adjacency list.

    Args:
        relationships: List of topology relationships.

    Returns:
        Adjacency dict: resource_id -> list of {target_id, type}.
    """
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for rel in relationships:
        if rel.source_id not in adjacency:
            adjacency[rel.source_id] = []
        adjacency[rel.source_id].append(
            {"target_id": rel.target_id, "type": rel.relationship_type}
        )
    return adjacency
