"""Azure icon management — download, cache, and map icons to resource types."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ICONS_DIR = Path(__file__).parent / "azure"

# Microsoft Azure Architecture Icons download URL
# Users should download from: https://learn.microsoft.com/en-us/azure/architecture/icons/
AZURE_ICONS_URL = "https://arch-center.azureedge.net/icons/Azure_Public_Service_Icons_V18.zip"


def get_icon_path(icon_file: str) -> str | None:
    """Get the full path to an icon file if it exists.

    Args:
        icon_file: Icon filename (e.g., 'vm.svg').

    Returns:
        Full path string if the icon exists, None otherwise.
    """
    path = ICONS_DIR / icon_file
    if path.exists():
        return str(path)
    return None


def icons_available() -> bool:
    """Check if Azure icons have been downloaded."""
    return ICONS_DIR.exists() and any(ICONS_DIR.iterdir())
