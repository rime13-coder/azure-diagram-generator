"""Shared utility for building display_info strings for diagram nodes.

Centralizes the logic for extracting and formatting SKU, tags,
location, and IP information into concise display strings.
"""

from __future__ import annotations

from typing import Any

from azure_diagrammer.discovery.ip_resolver import IPResolver


def build_display_info(
    resource: dict[str, Any],
    ip_resolver: IPResolver | None = None,
    show_sku: bool = True,
    show_location: bool = True,
    show_tags: bool = False,
    show_ips: bool = False,
    max_tags: int = 3,
) -> str:
    """Build a concise display_info string for a resource."""
    parts: list[str] = []

    if show_sku:
        sku_text = _format_sku(resource)
        if sku_text:
            parts.append(sku_text)

    if show_location:
        location = resource.get("location", "")
        if location:
            parts.append(location)

    if show_ips and ip_resolver:
        ip_text = ip_resolver.get_resource_ip_display(resource)
        if ip_text:
            parts.append(ip_text)

    if show_tags:
        tag_text = _format_tags(resource, max_tags)
        if tag_text:
            parts.append(tag_text)

    return " | ".join(parts)


def _format_sku(resource: dict[str, Any]) -> str:
    """Format SKU information concisely."""
    sku = resource.get("sku")
    if not sku or not isinstance(sku, dict):
        return ""

    sku_parts: list[str] = []
    name = sku.get("name", "")
    if name:
        sku_parts.append(str(name))
    tier = sku.get("tier", "")
    if tier and str(tier).lower() != str(name).lower():
        sku_parts.append(str(tier))
    capacity = sku.get("capacity")
    if capacity is not None:
        sku_parts.append(f"cap:{capacity}")

    kind = resource.get("kind", "")
    if kind and kind not in sku_parts:
        sku_parts.append(kind)

    return ", ".join(sku_parts)


def resolve_icon(resource_type: str) -> str | None:
    """Resolve the icon file path for an Azure resource type.

    Returns the full path if the icon exists on disk, None otherwise.
    """
    from azure_diagrammer.icons import get_icon_path
    from azure_diagrammer.model.azure_types import get_resource_meta

    meta = get_resource_meta(resource_type)
    return get_icon_path(meta.icon_file)


def _format_tags(resource: dict[str, Any], max_tags: int = 3) -> str:
    """Format tags into a compact display string."""
    tags = resource.get("tags")
    if not tags or not isinstance(tags, dict):
        return ""

    display_tags = {
        k: v for k, v in tags.items()
        if v and not k.lower().startswith("hidden-")
    }
    if not display_tags:
        return ""

    tag_items = list(display_tags.items())[:max_tags]
    tag_str = ", ".join(f"{k}={v}" for k, v in tag_items)
    if len(display_tags) > max_tags:
        tag_str += f" +{len(display_tags) - max_tags} more"
    return f"[{tag_str}]"
