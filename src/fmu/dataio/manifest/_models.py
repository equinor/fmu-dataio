"""The model for the export manifest file"""

import datetime
import getpass
import json
from pathlib import Path
from typing import Self

from pydantic import AwareDatetime, BaseModel, Field, RootModel


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

    root: list[ExportManifestEntry] = Field(default_factory=list)

    def __getitem__(self, item: int) -> ExportManifestEntry:
        return self.root[item]

    def __len__(self) -> int:
        return len(self.root)

    @classmethod
    def from_file(cls, manifest_path: Path) -> Self:
        """Load the export manifest from the JSON file."""
        with manifest_path.open("r", encoding="utf-8") as file:
            return cls.model_validate(json.load(file))

    def add_entry(self, absolute_path: Path) -> None:
        """Append a new file to the manifest."""
        self.root.append(
            ExportManifestEntry(
                absolute_path=absolute_path,
                exported_at=datetime.datetime.now(datetime.UTC),
                exported_by=getpass.getuser(),
            )
        )

    def to_file(self, manifest_path: Path) -> None:
        """Save the manifest as a JSON file."""
        with manifest_path.open("w", encoding="utf-8") as file:
            file.write(self.model_dump_json(indent=2))
