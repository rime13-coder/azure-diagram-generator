"""Lucidchart renderer — builds .lucid ZIP files and uploads via REST API.

The .lucid format is a ZIP archive containing:
  - document.json: Shapes, lines, groups, pages, and styling
  - images/: Embedded icon images (PNG/SVG)

Upload uses the Lucidchart Standard Import REST API.
"""

from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path
from typing import Any

import requests

from azure_diagrammer.model.azure_types import get_resource_meta
from azure_diagrammer.model.graph import (
    ArchitectureGraph,
    DiagramEdge,
    DiagramGroup,
    DiagramNode,
    DiagramPage,
    EdgeType,
    GroupType,
)
from azure_diagrammer.renderers.base import BaseRenderer

logger = logging.getLogger(__name__)

_SAFE_ID_TABLE = str.maketrans({"/": "_", " ": "_", ":": "_", "(": "", ")": ""})


def _sanitize_id(raw_id: str) -> str:
    """Ensure ID is valid for Lucidchart (alphanumeric + -_.~ , max 36 chars)."""
    import hashlib

    clean = raw_id.translate(_SAFE_ID_TABLE)
    if len(clean) <= 36:
        return clean
    # Truncate to 29 chars + 7-char hash suffix for uniqueness
    h = hashlib.md5(clean.encode()).hexdigest()[:7]
    return f"{clean[:28]}_{h}"


class LucidchartRenderer(BaseRenderer):
    """Renders architecture graphs as Lucidchart .lucid files."""

    def file_extension(self) -> str:
        return "lucid"

    def render(self, graph: ArchitectureGraph, output_path: Path) -> Path:
        """Build a .lucid ZIP file from the architecture graph.

        Args:
            graph: The architecture graph to render.
            output_path: Output directory or file path.

        Returns:
            Path to the generated .lucid file.
        """
        out_file = self.output_file(output_path, graph.project_name)
        document = self._build_document(graph)

        with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("document.json", json.dumps(document, indent=2))
            # Embed icon images if they exist
            self._embed_icons(zf, graph)

        logger.info("Generated Lucidchart file: %s", out_file)
        return out_file

    def _build_document(self, graph: ArchitectureGraph) -> dict[str, Any]:
        """Build the document.json structure for the .lucid format."""
        pages = []
        for page in graph.pages:
            pages.append(self._build_page(page))

        return {
            "version": 1,
            "pages": pages,
        }

    def _build_page(self, page: DiagramPage) -> dict[str, Any]:
        """Build a single page definition."""
        shapes = []
        lines = []
        containers = []

        # Prefix all IDs with page ID to ensure global uniqueness across pages
        prefix = f"{page.id}_"

        # Build a mapping from original IDs to sanitized IDs.
        # Use id(obj) as key to handle duplicate .id values across subscriptions.
        # Also keep a name-based map for cross-references (group_id, source_id, etc.)
        obj_id_map: dict[int, str] = {}  # id(obj) -> sanitized ID
        id_map: dict[str, str] = {}  # first-wins name -> sanitized ID (for refs)
        used_ids: set[str] = set()

        def _unique_id(raw_id: str) -> str:
            candidate = _sanitize_id(f"{prefix}{raw_id}")
            if candidate not in used_ids:
                used_ids.add(candidate)
                return candidate
            for i in range(2, 100):
                alt = _sanitize_id(f"{prefix}{raw_id}_{i}")
                if alt not in used_ids:
                    used_ids.add(alt)
                    return alt
            return candidate

        for group in page.groups:
            uid = _unique_id(group.id)
            obj_id_map[id(group)] = uid
            if group.id not in id_map:
                id_map[group.id] = uid
        for node in page.nodes:
            uid = _unique_id(node.id)
            obj_id_map[id(node)] = uid
            if node.id not in id_map:
                id_map[node.id] = uid
        for edge in page.edges:
            uid = _unique_id(edge.id)
            obj_id_map[id(edge)] = uid
            if edge.id not in id_map:
                id_map[edge.id] = uid

        # Render groups as container shapes
        for group in page.groups:
            containers.append(self._group_to_shape(group, id_map, obj_id_map))

        # Render nodes as shapes (may produce multiple shapes per node for icon+label)
        for node in page.nodes:
            shapes.extend(self._node_to_shapes(node, id_map, obj_id_map))

        # Render edges as lines
        for edge in page.edges:
            lines.append(self._edge_to_line(edge, id_map, obj_id_map))

        return {
            "id": _sanitize_id(page.id),
            "title": page.title,
            "shapes": containers + shapes,
            "lines": lines,
        }

    def _node_to_shapes(
        self,
        node: DiagramNode,
        id_map: dict[str, str],
        obj_id_map: dict[int, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Convert a DiagramNode to Lucidchart shapes.

        If the node has an icon, produces an image shape + text label.
        Otherwise, produces a single rectangle shape.
        """
        meta = get_resource_meta(node.azure_resource_type)
        node_id = (obj_id_map or {}).get(id(node)) or id_map.get(node.id, _sanitize_id(node.id))

        text = node.name
        if node.display_info:
            text += f"\n{node.display_info}"

        parent_id = None
        if node.group_id:
            parent_id = id_map.get(node.group_id, _sanitize_id(node.group_id))

        if node.icon_path:
            icon_filename = Path(node.icon_path).name
            icon_w, icon_h = 48, 48
            label_h = max(30, 16 * text.count("\n") + 20)

            # Icon as rectangle with image fill
            icon_shape: dict[str, Any] = {
                "id": _sanitize_id(f"{node_id}_icon"),
                "type": "rectangle",
                "boundingBox": {
                    "x": node.position.x + (node.size.w - icon_w) / 2,
                    "y": node.position.y,
                    "w": icon_w,
                    "h": icon_h,
                },
                "style": {"strokeWidth": 0},
                "fill": {"type": "image", "ref": icon_filename},
            }
            if parent_id:
                icon_shape["containedBy"] = parent_id

            # Text label below icon
            label_shape: dict[str, Any] = {
                "id": node_id,
                "type": "text",
                "boundingBox": {
                    "x": node.position.x,
                    "y": node.position.y + icon_h + 4,
                    "w": node.size.w,
                    "h": label_h,
                },
                "text": text,
                "customData": [
                    {"key": "resourceId", "value": node.azure_resource_id},
                    {"key": "resourceType", "value": node.azure_resource_type},
                ],
            }
            if parent_id:
                label_shape["containedBy"] = parent_id

            return [icon_shape, label_shape]
        else:
            # Fallback to rectangle
            fill_color = node.style.get("fill", meta.fill_color)
            stroke_color = node.style.get("stroke", meta.stroke_color)

            shape: dict[str, Any] = {
                "id": node_id,
                "type": "rectangle",
                "boundingBox": {
                    "x": node.position.x,
                    "y": node.position.y,
                    "w": node.size.w,
                    "h": node.size.h,
                },
                "text": text,
                "style": {
                    "fillColor": fill_color,
                    "strokeColor": stroke_color,
                    "strokeWidth": 1,
                },
                "customData": [
                    {"key": "resourceId", "value": node.azure_resource_id},
                    {"key": "resourceType", "value": node.azure_resource_type},
                ],
            }
            if parent_id:
                shape["containedBy"] = parent_id

            return [shape]

    def _group_to_shape(
        self,
        group: DiagramGroup,
        id_map: dict[str, str],
        obj_id_map: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        """Convert a DiagramGroup to a Lucidchart container shape."""
        fill_color = group.style.get("fill", "#F5F5F5")
        stroke_color = group.style.get("stroke", "#CCCCCC")

        # GroupType-aware styling defaults
        stroke_width = 1
        if group.group_type in (GroupType.VNET, GroupType.APP_SERVICE_PLAN):
            stroke_width = 2

        shape: dict[str, Any] = {
            "id": (obj_id_map or {}).get(id(group)) or id_map.get(group.id, _sanitize_id(group.id)),
            "type": "roundedRectangleContainer",
            "boundingBox": {
                "x": group.bounding_box.x,
                "y": group.bounding_box.y,
                "w": group.bounding_box.w,
                "h": group.bounding_box.h,
            },
            "text": group.name,
            "style": {
                "fillColor": fill_color,
                "strokeColor": stroke_color,
                "strokeWidth": stroke_width,
                "cornerRadius": 8,
            },
            "customData": [
                {"key": "resourceId", "value": group.azure_resource_id},
                {"key": "groupType", "value": group.group_type.value},
            ],
        }

        if group.parent_id:
            shape["containedBy"] = id_map.get(
                group.parent_id, _sanitize_id(group.parent_id)
            )

        return shape

    def _edge_to_line(
        self,
        edge: DiagramEdge,
        id_map: dict[str, str],
        obj_id_map: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        """Convert a DiagramEdge to a Lucidchart line."""
        if edge.bidirectional:
            start_style = "arrow"
            end_style = "arrow"
        else:
            start_style = "none"
            end_style = "arrow"

        stroke_color = edge.style.get("stroke", "#666666")
        stroke_width = 1
        raw_dash = edge.style.get("dash", "solid")
        # Normalize to valid Lucidchart values: solid, dashed, dotted
        if raw_dash in ("solid", "dashed", "dotted"):
            dash = raw_dash
        elif raw_dash and raw_dash != "none":
            dash = "dashed"
        else:
            dash = "solid"

        # Edge type styling
        if edge.edge_type == EdgeType.PEERING:
            stroke_width = 2
            dash = "dashed"

        line: dict[str, Any] = {
            "id": (obj_id_map or {}).get(id(edge)) or id_map.get(edge.id, _sanitize_id(edge.id)),
            "lineType": "elbow",
            "endpoint1": {
                "type": "shapeEndpoint",
                "shapeId": id_map.get(edge.source_id, _sanitize_id(edge.source_id)),
                "style": start_style,
                "position": {"x": 1, "y": 0.5},
            },
            "endpoint2": {
                "type": "shapeEndpoint",
                "shapeId": id_map.get(edge.target_id, _sanitize_id(edge.target_id)),
                "style": end_style,
                "position": {"x": 0, "y": 0.5},
            },
            "stroke": {
                "color": stroke_color,
                "width": stroke_width,
                "style": dash,
            },
        }

        if edge.label:
            line["text"] = [
                {"text": edge.label, "position": 0.5, "side": "top"}
            ]

        return line

    def _embed_icons(
        self, zf: zipfile.ZipFile, graph: ArchitectureGraph
    ) -> None:
        """Embed referenced icon files into the ZIP archive."""
        embedded: set[str] = set()
        for node in graph.all_nodes():
            if node.icon_path and node.icon_path not in embedded:
                icon_file = Path(node.icon_path)
                if icon_file.exists():
                    zf.write(icon_file, f"images/{icon_file.name}")
                    embedded.add(node.icon_path)


class LucidchartUploader:
    """Uploads .lucid files to Lucidchart via the Standard Import REST API.

    Supports:
    - API key (simplest — generate at https://lucid.app/developer#/apikeys)
    - OAuth2 authorization code flow (client_id + client_secret with browser login)
    """

    REDIRECT_PORT = 8497
    REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.lucid.co",
        client_id: str = "",
        client_secret: str = "",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: str | None = None

    def _get_access_token(self) -> str:
        """Get an access token via API key or OAuth2 authorization code flow."""
        if self._access_token:
            return self._access_token

        # If a direct API key is provided, use it as-is
        if self.api_key and not self.client_id:
            return self.api_key

        # OAuth2 authorization code flow with local callback server
        self._access_token = self._oauth2_authorize()
        return self._access_token

    def _oauth2_authorize(self) -> str:
        """Run the OAuth2 authorization code flow with a local HTTP server."""
        import secrets
        import threading
        import webbrowser
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from urllib.parse import urlencode, urlparse, parse_qs

        state = secrets.token_urlsafe(32)
        auth_code_holder: dict[str, str | None] = {"code": None, "error": None}
        server_ready = threading.Event()

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                if params.get("error"):
                    auth_code_holder["error"] = params["error"][0]
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    error_desc = params.get("error_description", ["Unknown error"])[0]
                    self.wfile.write(
                        f"<h2>Authorization failed</h2><p>{error_desc}</p>".encode()
                    )
                elif params.get("code"):
                    auth_code_holder["code"] = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<h2>Authorization successful!</h2>"
                        b"<p>You can close this window and return to the terminal.</p>"
                    )
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h2>Missing authorization code</h2>")

            def log_message(self, format, *args):
                pass  # Suppress request logs

        # Start local callback server
        server = HTTPServer(("127.0.0.1", self.REDIRECT_PORT), CallbackHandler)
        server.timeout = 120  # 2-minute timeout

        def serve():
            server_ready.set()
            server.handle_request()  # Handle a single request then stop

        server_thread = threading.Thread(target=serve, daemon=True)
        server_thread.start()
        server_ready.wait()

        # Build authorization URL and open browser
        auth_params = urlencode({
            "client_id": self.client_id,
            "redirect_uri": self.REDIRECT_URI,
            "scope": "lucidchart.document.content",
            "response_type": "code",
            "state": state,
        })
        auth_url = f"https://lucid.app/oauth2/authorize?{auth_params}"

        logger.info("Opening browser for Lucidchart authorization...")
        print(f"\nOpening browser for Lucidchart login...")
        print(f"If the browser doesn't open, visit:\n{auth_url}\n")
        webbrowser.open(auth_url)

        # Wait for the callback
        server_thread.join(timeout=120)
        server.server_close()

        if auth_code_holder["error"]:
            raise RuntimeError(
                f"Lucidchart authorization failed: {auth_code_holder['error']}"
            )
        if not auth_code_holder["code"]:
            raise RuntimeError(
                "Lucidchart authorization timed out. No authorization code received."
            )

        # Exchange authorization code for access token
        token_url = f"{self.base_url}/oauth2/token"
        response = requests.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": auth_code_holder["code"],
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data["access_token"]
        logger.info("Obtained Lucidchart OAuth2 access token")
        return access_token

    def upload(self, lucid_file: Path, title: str | None = None) -> str:
        """Upload a .lucid file and return the document URL.

        Args:
            lucid_file: Path to the .lucid ZIP file.
            title: Optional document title override.

        Returns:
            URL of the created Lucidchart document.

        Raises:
            requests.HTTPError: If the upload fails.
        """
        token = self._get_access_token()
        url = f"{self.base_url}/documents"
        headers = {
            "Authorization": f"Bearer {token}",
            "Lucid-Api-Version": "1",
        }

        with open(lucid_file, "rb") as f:
            files = {
                "file": (
                    lucid_file.name,
                    f,
                    "x-application/vnd.lucid.standardImport",
                ),
            }
            data = {
                "product": "lucidchart",
            }
            if title:
                data["title"] = title

            response = requests.post(
                url, headers=headers, files=files, data=data, timeout=60
            )

        response.raise_for_status()
        result = response.json()
        doc_url = result.get("editUrl") or result.get("url", "")
        logger.info("Uploaded to Lucidchart: %s", doc_url)
        return doc_url
