"""CLI entry point for Azure Diagram Generator.

Provides commands to discover Azure resources, generate architecture
diagrams, and upload to Lucidchart.
"""

from __future__ import annotations

import json
import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn

from azure_diagrammer.config import Config

app = typer.Typer(
    name="azure-diagrammer",
    help="Automated Azure architecture diagram generator",
    no_args_is_help=True,
)
console = Console()


class DiagramType(str, Enum):
    HIGH_LEVEL = "high-level"
    NETWORK = "network"
    APP = "app"
    DATAFLOW = "dataflow"
    SECURITY = "security"
    ALL = "all"


class OutputFormat(str, Enum):
    LUCIDCHART = "lucidchart"
    DRAWIO = "drawio"
    MERMAID = "mermaid"


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.command()
def discover(
    subscription: Annotated[
        Optional[list[str]],
        typer.Option("--subscription", "-s", help="Subscription ID(s), or 'all'"),
    ] = None,
    resource_group: Annotated[
        Optional[list[str]],
        typer.Option("--resource-group", "-g", help="Filter to specific resource group(s)"),
    ] = None,
    tag: Annotated[
        Optional[str],
        typer.Option("--tag", help="Filter by tag (key=value)"),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output path for discovery JSON"),
    ] = Path("./discovery.json"),
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Discover Azure resources and save to a JSON file."""
    _setup_logging(verbose)

    config = Config.from_env()
    if subscription:
        config.subscription_ids = subscription
    if resource_group:
        config.resource_filter.include_resource_groups = resource_group
    if tag and "=" in tag:
        k, v = tag.split("=", 1)
        config.resource_filter.filter_tags = {k.strip(): v.strip()}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Discovering Azure resources...", total=None)

        from azure_diagrammer.discovery.resource_graph import ResourceGraphDiscovery
        from azure_diagrammer.discovery.relationships import build_relationship_graph

        discovery = ResourceGraphDiscovery(config)

        all_resources = discovery.discover_all_resources()
        resource_groups_data = discovery.discover_resource_groups()
        subscriptions_data = discovery.discover_subscriptions()
        network_resources = discovery.discover_network_resources()
        nsg_rules = discovery.discover_nsg_rules()

        # Build relationships
        relationships = build_relationship_graph(all_resources)

    # Save discovery data
    discovery_data = {
        "resources": all_resources,
        "resource_groups": resource_groups_data,
        "subscriptions": subscriptions_data,
        "network_resources": network_resources,
        "nsg_rules": nsg_rules,
        "relationships": [
            {
                "source_id": r.source_id,
                "target_id": r.target_id,
                "type": r.relationship_type,
                "label": r.label,
            }
            for r in relationships
        ],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(discovery_data, indent=2, default=str), encoding="utf-8")
    console.print(f"[green]Discovery data saved to {output}[/green]")
    console.print(f"  Resources: {len(all_resources)}")
    console.print(f"  Resource Groups: {len(resource_groups_data)}")
    console.print(f"  Relationships: {len(relationships)}")


@app.command()
def generate(
    input_file: Annotated[
        Path,
        typer.Option("--input", "-i", help="Discovery JSON file"),
    ] = Path("./discovery.json"),
    diagram_type: Annotated[
        DiagramType,
        typer.Option("--type", "-t", help="Diagram type to generate"),
    ] = DiagramType.ALL,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.MERMAID,
    project: Annotated[
        str,
        typer.Option("--project", "-p", help="Project name for the diagram"),
    ] = "azure-architecture",
    upload: Annotated[
        bool,
        typer.Option("--upload", help="Upload to Lucidchart (requires API key)"),
    ] = False,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file or directory"),
    ] = Path("./output"),
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Generate diagrams from previously discovered data."""
    _setup_logging(verbose)

    if not input_file.exists():
        console.print(f"[red]Discovery file not found: {input_file}[/red]")
        console.print("Run 'azure-diagrammer discover' first.")
        raise typer.Exit(code=1)

    discovery_data = json.loads(input_file.read_text(encoding="utf-8"))
    config = Config.from_env()

    _generate_diagrams(
        discovery_data=discovery_data,
        diagram_type=diagram_type,
        output_format=output_format,
        project_name=project,
        upload=upload,
        output_path=output,
        config=config,
    )


@app.command()
def run(
    subscription: Annotated[
        Optional[list[str]],
        typer.Option("--subscription", "-s", help="Subscription ID(s), or 'all'"),
    ] = None,
    resource_group: Annotated[
        Optional[list[str]],
        typer.Option("--resource-group", "-g", help="Filter to specific resource group(s)"),
    ] = None,
    tag: Annotated[
        Optional[str],
        typer.Option("--tag", help="Filter by tag (key=value)"),
    ] = None,
    diagram_type: Annotated[
        DiagramType,
        typer.Option("--type", "-t", help="Diagram type to generate"),
    ] = DiagramType.ALL,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.MERMAID,
    project: Annotated[
        str,
        typer.Option("--project", "-p", help="Project name"),
    ] = "azure-architecture",
    upload: Annotated[
        bool,
        typer.Option("--upload", help="Upload to Lucidchart"),
    ] = False,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output path"),
    ] = Path("./output"),
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Discover Azure resources and generate diagrams in one step."""
    _setup_logging(verbose)

    config = Config.from_env()
    if subscription:
        config.subscription_ids = subscription
    if resource_group:
        config.resource_filter.include_resource_groups = resource_group
    if tag and "=" in tag:
        k, v = tag.split("=", 1)
        config.resource_filter.filter_tags = {k.strip(): v.strip()}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Discovering Azure resources...", total=None)

        from azure_diagrammer.discovery.resource_graph import ResourceGraphDiscovery
        from azure_diagrammer.discovery.relationships import build_relationship_graph
        from azure_diagrammer.discovery.data_flow import discover_data_flows

        discovery = ResourceGraphDiscovery(config)

        all_resources = discovery.discover_all_resources()
        resource_groups_data = discovery.discover_resource_groups()
        subscriptions_data = discovery.discover_subscriptions()
        network_resources = discovery.discover_network_resources()
        nsg_rules = discovery.discover_nsg_rules()
        relationships = build_relationship_graph(all_resources)
        data_flows = discover_data_flows(all_resources, relationships, nsg_rules)

        progress.update(task, description="Generating diagrams...")

    discovery_data = {
        "resources": all_resources,
        "resource_groups": resource_groups_data,
        "subscriptions": subscriptions_data,
        "network_resources": network_resources,
        "nsg_rules": nsg_rules,
        "relationships": [
            {
                "source_id": r.source_id,
                "target_id": r.target_id,
                "type": r.relationship_type,
                "label": r.label,
            }
            for r in relationships
        ],
        "data_flows": [
            {
                "source": f.source,
                "destination": f.destination,
                "protocol": f.protocol,
                "port": f.port,
                "label": f.label,
                "flow_type": f.flow_type,
                "direction": f.direction,
                "access": f.access,
                "priority": f.priority,
                "source_ip": f.source_ip,
                "destination_ip": f.destination_ip,
            }
            for f in data_flows
        ],
    }

    _generate_diagrams(
        discovery_data=discovery_data,
        diagram_type=diagram_type,
        output_format=output_format,
        project_name=project,
        upload=upload,
        output_path=output,
        config=config,
    )


def _generate_diagrams(
    discovery_data: dict,
    diagram_type: DiagramType,
    output_format: OutputFormat,
    project_name: str,
    upload: bool,
    output_path: Path,
    config: Config,
) -> None:
    """Core diagram generation logic shared by generate and run commands."""
    from azure_diagrammer.icons import icons_available

    if not icons_available():
        console.print(
            "[yellow]Azure icons not found. Run 'azure-diagrammer download-icons' "
            "for icon support.[/yellow]"
        )

    from azure_diagrammer.discovery.data_flow import DataFlow
    from azure_diagrammer.discovery.relationships import ResourceRelationship
    from azure_diagrammer.model.graph import ArchitectureGraph
    from azure_diagrammer.templates.high_level import build_high_level_page
    from azure_diagrammer.templates.network import build_network_page
    from azure_diagrammer.templates.application import build_application_page
    from azure_diagrammer.templates.data_flow import build_data_flow_page
    from azure_diagrammer.templates.security import build_security_page

    # Reconstruct relationships from serialized data
    relationships = [
        ResourceRelationship(
            source_id=r["source_id"],
            target_id=r["target_id"],
            relationship_type=r["type"],
            label=r.get("label", ""),
        )
        for r in discovery_data.get("relationships", [])
    ]

    # Reconstruct data flows
    data_flows = [
        DataFlow(
            source=f["source"],
            destination=f["destination"],
            protocol=f.get("protocol", ""),
            port=f.get("port", ""),
            label=f.get("label", ""),
            flow_type=f.get("flow_type", "network"),
            direction=f.get("direction", ""),
            access=f.get("access", "Allow"),
            priority=f.get("priority"),
            source_ip=f.get("source_ip", ""),
            destination_ip=f.get("destination_ip", ""),
        )
        for f in discovery_data.get("data_flows", [])
    ]

    graph = ArchitectureGraph(project_name=project_name)

    types_to_generate = (
        [DiagramType.HIGH_LEVEL, DiagramType.NETWORK, DiagramType.APP, DiagramType.DATAFLOW, DiagramType.SECURITY]
        if diagram_type == DiagramType.ALL
        else [diagram_type]
    )

    for dtype in types_to_generate:
        try:
            if dtype == DiagramType.HIGH_LEVEL:
                page = build_high_level_page(
                    discovery_data.get("resources", []),
                    discovery_data.get("resource_groups", []),
                    discovery_data.get("subscriptions", []),
                )
                graph.add_page(page)
            elif dtype == DiagramType.NETWORK:
                page = build_network_page(
                    discovery_data.get("network_resources", {}),
                    relationships,
                    all_resources=discovery_data.get("resources", []),
                )
                graph.add_page(page)
            elif dtype == DiagramType.APP:
                page = build_application_page(
                    discovery_data.get("resources", []),
                    relationships,
                )
                graph.add_page(page)
            elif dtype == DiagramType.DATAFLOW:
                page = build_data_flow_page(
                    data_flows,
                    discovery_data.get("resources", []),
                )
                graph.add_page(page)
            elif dtype == DiagramType.SECURITY:
                page = build_security_page(
                    discovery_data.get("resources", []),
                    discovery_data.get("network_resources", {}),
                    relationships,
                    discovery_data.get("nsg_rules", []),
                )
                graph.add_page(page)
        except Exception as exc:
            console.print(f"[yellow]Warning: Failed to build {dtype.value} diagram: {exc}[/yellow]")

    # Render with selected format
    renderer = _get_renderer(output_format)
    output_file = renderer.render(graph, output_path)
    console.print(f"[green]Diagram generated: {output_file}[/green]")

    # Upload to Lucidchart if requested
    if upload and output_format == OutputFormat.LUCIDCHART:
        _upload_to_lucidchart(output_file, project_name, config)


def _get_renderer(output_format: OutputFormat):
    """Get the appropriate renderer for the output format."""
    if output_format == OutputFormat.LUCIDCHART:
        from azure_diagrammer.renderers.lucidchart import LucidchartRenderer
        return LucidchartRenderer()
    elif output_format == OutputFormat.DRAWIO:
        from azure_diagrammer.renderers.drawio import DrawioRenderer
        return DrawioRenderer()
    else:
        from azure_diagrammer.renderers.mermaid import MermaidRenderer
        return MermaidRenderer()


def _upload_to_lucidchart(file_path: Path, title: str, config: Config) -> None:
    """Upload a generated .lucid file to Lucidchart."""
    has_oauth = config.lucidchart_client_id and config.lucidchart_client_secret
    has_key = config.lucidchart_api_key

    if not has_oauth and not has_key:
        console.print(
            "[yellow]Lucidchart credentials not configured. "
            "Set LUCIDCHART_CLIENT_ID + LUCIDCHART_CLIENT_SECRET "
            "(or LUCIDCHART_API_KEY) in your .env file.[/yellow]"
        )
        return

    from azure_diagrammer.renderers.lucidchart import LucidchartUploader

    uploader = LucidchartUploader(
        api_key=config.lucidchart_api_key or "",
        client_id=config.lucidchart_client_id or "",
        client_secret=config.lucidchart_client_secret or "",
        base_url=config.lucidchart_base_url,
    )
    try:
        doc_url = uploader.upload(file_path, title=title)
        console.print(f"[green]Uploaded to Lucidchart: {doc_url}[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to upload to Lucidchart: {exc}[/red]")


@app.command()
def download_icons(
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Download official Microsoft Azure Architecture Icons."""
    _setup_logging(verbose)
    from azure_diagrammer.icons.download_icons import download_and_extract_icons

    count = download_and_extract_icons()
    console.print(f"[green]Downloaded {count} Azure icons.[/green]")


if __name__ == "__main__":
    app()
