"""Script to download and extract Azure Architecture Icons.

Downloads the official Microsoft Azure icon set and maps each icon
to the corresponding resource type used by the diagram generator.

Usage:
    python -m azure_diagrammer.icons.download_icons
"""

from __future__ import annotations

import io
import logging
import shutil
import zipfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

ICONS_DIR = Path(__file__).parent / "azure"

# Official Microsoft Azure Architecture Icons URL
AZURE_ICONS_URL = "https://arch-center.azureedge.net/icons/Azure_Public_Service_Icons_V18.zip"

# Map from our icon_file names (in azure_types.py) to search patterns
# in the Microsoft icon ZIP. The ZIP contains folders like:
#   Azure_Public_Service_Icons/Icons/Compute/10021-icon-service-Virtual-Machines.svg
ICON_SEARCH_MAP = {
    "vm.svg": ["Virtual-Machine", "Virtual Machine"],
    "vmss.svg": ["VM-Scale-Set", "Virtual Machine Scale Set"],
    "app-service.svg": ["App-Service", "App Service"],
    "app-service-plan.svg": ["App-Service-Plan", "App Service Plan"],
    "function-app.svg": ["Function-App", "Function App"],
    "aks.svg": ["Kubernetes", "AKS"],
    "container-instance.svg": ["Container-Instance", "Container Instance"],
    "container-registry.svg": ["Container-Registr", "Container Registry"],
    "vnet.svg": ["Virtual-Network", "Virtual Network"],
    "subnet.svg": ["Subnet"],
    "nic.svg": ["Network-Interface", "NIC"],
    "public-ip.svg": ["Public-IP", "Public IP"],
    "load-balancer.svg": ["Load-Balancer", "Load Balancer"],
    "app-gateway.svg": ["Application-Gateway", "App Gateway"],
    "firewall.svg": ["Firewall"],
    "nsg.svg": ["Network-Security-Group", "NSG"],
    "private-endpoint.svg": ["Private-Endpoint", "Private Endpoint"],
    "vpn-gateway.svg": ["VPN-Gateway", "VPN Gateway", "Virtual-Network-Gateway"],
    "expressroute.svg": ["ExpressRoute"],
    "dns-zone.svg": ["DNS"],
    "traffic-manager.svg": ["Traffic-Manager", "Traffic Manager"],
    "front-door.svg": ["Front-Door", "Front Door"],
    "route-table.svg": ["Route-Table", "Route Table"],
    "sql-server.svg": ["SQL-Server", "SQL Server"],
    "sql-database.svg": ["SQL-Database", "SQL Database"],
    "cosmos-db.svg": ["Cosmos", "Azure Cosmos"],
    "mysql.svg": ["MySQL"],
    "postgresql.svg": ["PostgreSQL"],
    "redis-cache.svg": ["Redis", "Cache for Redis"],
    "storage-account.svg": ["Storage-Account", "Storage Account"],
    "key-vault.svg": ["Key-Vault", "Key Vault"],
    "waf.svg": ["WAF", "Web-Application-Firewall"],
    "service-bus.svg": ["Service-Bus", "Service Bus"],
    "event-hub.svg": ["Event-Hub", "Event Hub"],
    "event-grid.svg": ["Event-Grid", "Event Grid"],
    "api-management.svg": ["API-Management", "API Management"],
    "logic-app.svg": ["Logic-App", "Logic App"],
    "app-insights.svg": ["Application-Insights", "App Insights"],
    "log-analytics.svg": ["Log-Analytics", "Log Analytics"],
    "managed-identity.svg": ["Managed-Identit", "Managed Identity"],
    "generic.svg": [],  # Placeholder — no match needed
}


def download_and_extract_icons(
    url: str = AZURE_ICONS_URL,
    output_dir: Path = ICONS_DIR,
) -> int:
    """Download the Azure icon set and extract mapped icons.

    Args:
        url: URL to the Azure icons ZIP file.
        output_dir: Directory to store extracted icons.

    Returns:
        Number of icons successfully extracted.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Azure icons from {url}...")
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    print("Extracting icons...")
    extracted_count = 0

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        # Index all SVG files in the ZIP
        svg_files = [
            name for name in zf.namelist()
            if name.lower().endswith(".svg")
        ]

        print(f"Found {len(svg_files)} SVG files in archive")

        for target_name, search_patterns in ICON_SEARCH_MAP.items():
            if not search_patterns:
                continue

            # Find a matching SVG
            matched_file = _find_matching_svg(svg_files, search_patterns)
            if matched_file:
                # Extract to our target filename
                data = zf.read(matched_file)
                target_path = output_dir / target_name
                target_path.write_bytes(data)
                extracted_count += 1
                logger.debug("Extracted %s -> %s", matched_file, target_name)
            else:
                logger.warning("No icon found for %s (patterns: %s)", target_name, search_patterns)

    # Create a generic placeholder SVG
    _create_generic_icon(output_dir / "generic.svg")
    extracted_count += 1

    print(f"Extracted {extracted_count} icons to {output_dir}")
    return extracted_count


def _find_matching_svg(svg_files: list[str], patterns: list[str]) -> str | None:
    """Find the first SVG file matching any of the search patterns."""
    for pattern in patterns:
        pattern_lower = pattern.lower()
        for svg in svg_files:
            # Match on filename (not full path)
            filename = svg.split("/")[-1].lower()
            if pattern_lower in filename:
                return svg
    return None


def _create_generic_icon(path: Path) -> None:
    """Create a simple generic Azure resource SVG icon."""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="4" y="4" width="56" height="56" rx="8" ry="8"
        fill="#B4B4B4" stroke="#808080" stroke-width="2"/>
  <text x="32" y="38" text-anchor="middle" font-family="Segoe UI, sans-serif"
        font-size="18" fill="#FFFFFF" font-weight="bold">Az</text>
</svg>"""
    path.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    download_and_extract_icons()
