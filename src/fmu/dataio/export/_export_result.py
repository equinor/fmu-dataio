from pathlib import Path
from typing import List

from pydantic import BaseModel


class ExportResultItem(BaseModel):
    """Object containing information about an exported data object."""

    absolute_path: Path


class ExportResult(BaseModel):
    """
    Represents the return object from a simplified export function.
    This is used to provide feedback to the user regarding the details
    of the items that were successfully exported by the export function.
    """

    items: List[ExportResultItem]
