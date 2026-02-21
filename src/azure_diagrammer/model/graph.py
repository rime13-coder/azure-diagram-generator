"""Core graph model for architecture diagrams.

Defines the intermediate representation used between Azure discovery
and diagram rendering. Decouples resource data from visual output.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EdgeType(str, Enum):
    """Classification of diagram edges."""

    NETWORK = "network"
    DATA_FLOW = "data_flow"
    DEPENDENCY = "dependency"
    ASSOCIATION = "association"
    CONTAINMENT = "containment"
    PEERING = "peering"


class GroupType(str, Enum):
    """Classification of diagram groups (containers)."""

    SUBSCRIPTION = "subscription"
    RESOURCE_GROUP = "resource_group"
    VNET = "vnet"
    SUBNET = "subnet"
    REGION = "region"
    LOGICAL_TIER = "logical_tier"
    APP_SERVICE_PLAN = "app_service_plan"


class Position(BaseModel):
    """2D position on the diagram canvas."""

    x: float = 0.0
    y: float = 0.0


class Size(BaseModel):
    """Dimensions of a diagram element."""

    w: float = 120.0
    h: float = 80.0


class BoundingBox(BaseModel):
    """Bounding box for groups/containers."""

    x: float = 0.0
    y: float = 0.0
    w: float = 400.0
    h: float = 300.0


class DiagramNode(BaseModel):
    """A single resource/element on the diagram."""

    id: str
    name: str
    azure_resource_type: str = ""
    azure_resource_id: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)
    position: Position = Field(default_factory=Position)
    size: Size = Field(default_factory=Size)
    icon_path: Optional[str] = None
    group_id: Optional[str] = None
    display_info: str = ""  # Additional text shown under the name (e.g., SKU, IP)
    style: dict[str, str] = Field(default_factory=dict)


class DiagramEdge(BaseModel):
    """A connection between two diagram nodes."""

    id: str
    source_id: str
    target_id: str
    label: str = ""
    edge_type: EdgeType = EdgeType.DEPENDENCY
    style: dict[str, str] = Field(default_factory=dict)
    bidirectional: bool = False


class DiagramGroup(BaseModel):
    """A container that groups related nodes (e.g., VNet, Subnet, RG)."""

    id: str
    name: str
    group_type: GroupType = GroupType.RESOURCE_GROUP
    children: list[str] = Field(default_factory=list)  # Node IDs or child group IDs
    parent_id: Optional[str] = None
    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    style: dict[str, str] = Field(default_factory=dict)
    azure_resource_id: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class DiagramPage(BaseModel):
    """A single page/tab within the diagram document."""

    id: str
    title: str
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    groups: list[DiagramGroup] = Field(default_factory=list)


class ArchitectureGraph(BaseModel):
    """Top-level diagram model containing all pages and metadata."""

    project_name: str = "azure-architecture"
    pages: list[DiagramPage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_page(self, page_id: str) -> Optional[DiagramPage]:
        """Return a page by its ID."""
        for page in self.pages:
            if page.id == page_id:
                return page
        return None

    def add_page(self, page: DiagramPage) -> None:
        """Add a page to the architecture graph."""
        self.pages.append(page)

    def all_nodes(self) -> list[DiagramNode]:
        """Return all nodes across all pages."""
        nodes = []
        for page in self.pages:
            nodes.extend(page.nodes)
        return nodes

    def all_edges(self) -> list[DiagramEdge]:
        """Return all edges across all pages."""
        edges = []
        for page in self.pages:
            edges.extend(page.edges)
        return edges
