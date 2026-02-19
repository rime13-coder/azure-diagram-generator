"""Abstract base class for diagram renderers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from azure_diagrammer.model.graph import ArchitectureGraph


class BaseRenderer(ABC):
    """Abstract renderer interface for all output formats."""

    @abstractmethod
    def render(self, graph: ArchitectureGraph, output_path: Path) -> Path:
        """Render the architecture graph to an output file.

        Args:
            graph: The architecture graph model to render.
            output_path: Directory or file path for the output.

        Returns:
            Path to the generated output file.
        """

    @abstractmethod
    def file_extension(self) -> str:
        """Return the file extension for this renderer's output."""

    def output_file(self, output_path: Path, project_name: str) -> Path:
        """Compute the full output file path.

        If output_path is a directory, generates a filename from the project name.
        """
        if output_path.is_dir() or not output_path.suffix:
            output_path.mkdir(parents=True, exist_ok=True)
            return output_path / f"{project_name}.{self.file_extension()}"
        return output_path
