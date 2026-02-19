"""Configuration management for Azure Diagram Generator."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class ResourceFilter(BaseModel):
    """Filters for Azure resource discovery."""

    include_resource_groups: list[str] = Field(default_factory=list)
    exclude_resource_types: list[str] = Field(default_factory=list)
    filter_tags: dict[str, str] = Field(default_factory=dict)


class Config(BaseModel):
    """Application configuration loaded from environment variables."""

    # Azure
    subscription_ids: list[str] = Field(default_factory=lambda: ["all"])
    azure_tenant_id: Optional[str] = None

    # Lucidchart
    lucidchart_api_key: Optional[str] = None
    lucidchart_client_id: Optional[str] = None
    lucidchart_client_secret: Optional[str] = None
    lucidchart_base_url: str = "https://api.lucid.co"

    # Output
    default_output_format: str = "lucidchart"
    default_diagram_type: str = "all"
    output_dir: Path = Path("./output")
    project_name: str = "azure-project"

    # Filters
    resource_filter: ResourceFilter = Field(default_factory=ResourceFilter)

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
        sub_ids_raw = os.getenv("AZURE_SUBSCRIPTION_IDS", "all")
        subscription_ids = [s.strip() for s in sub_ids_raw.split(",")]

        resource_filter = ResourceFilter()

        include_rgs = os.getenv("INCLUDE_RESOURCE_GROUPS", "")
        if include_rgs:
            resource_filter.include_resource_groups = [
                rg.strip() for rg in include_rgs.split(",")
            ]

        exclude_types = os.getenv("EXCLUDE_RESOURCE_TYPES", "")
        if exclude_types:
            resource_filter.exclude_resource_types = [
                t.strip() for t in exclude_types.split(",")
            ]

        filter_tag = os.getenv("FILTER_TAG", "")
        if filter_tag and "=" in filter_tag:
            key, value = filter_tag.split("=", 1)
            resource_filter.filter_tags = {key.strip(): value.strip()}

        return cls(
            subscription_ids=subscription_ids,
            azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
            lucidchart_api_key=os.getenv("LUCIDCHART_API_KEY"),
            lucidchart_client_id=os.getenv("LUCIDCHART_CLIENT_ID"),
            lucidchart_client_secret=os.getenv("LUCIDCHART_CLIENT_SECRET"),
            lucidchart_base_url=os.getenv(
                "LUCIDCHART_BASE_URL", "https://api.lucid.co"
            ),
            default_output_format=os.getenv("DEFAULT_OUTPUT_FORMAT", "lucidchart"),
            default_diagram_type=os.getenv("DEFAULT_DIAGRAM_TYPE", "all"),
            output_dir=Path(os.getenv("OUTPUT_DIR", "./output")),
            project_name=os.getenv("PROJECT_NAME", "azure-project"),
            resource_filter=resource_filter,
        )
