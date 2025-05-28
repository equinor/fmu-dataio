"""The model for the export manifest file"""

from pathlib import Path

from pydantic import AwareDatetime, BaseModel, RootModel


class ExportManifestEntry(BaseModel):
    """A single entry in the ExportManifest. Each entry contains
    information about a single exported file"""

    absolute_path: Path
    """The absolute path to the exported file"""
    exported_at: AwareDatetime
    """The datetime recording when the file was exported"""
    exported_by: str
    """The user that exported the file"""


class ExportManifest(RootModel):
    """The export manifest which acts as a log of exported files,
    containing one entry per file."""

    root: list[ExportManifestEntry]
