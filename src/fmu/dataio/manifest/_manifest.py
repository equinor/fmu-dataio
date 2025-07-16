"""
This module provides functionality to manage the export manifest file.
This manifest is a JSON file that keeps track of all files exported.

The location of the manifest file depends on the context in which FMU is running.
In a `realization` context, the manifest is located at the runpath.
In a `case` context, the manifest is located at the casepath.
"""

from pathlib import Path
from typing import Final

from fmu.dataio._logging import null_logger
from fmu.dataio._runcontext import FmuEnv
from fmu.dataio.manifest._models import ExportManifest

logger = null_logger(__name__)

MANIFEST_FILENAME: Final = ".dataio_export_manifest.json"


def get_manifest_path(casepath: Path | str | None = None) -> Path:
    """Determine the manifest path based on the FMU context.
    - 'realization': located at the runpath (inferred from environment)
    - 'case': located at the provided casepath"""

    if runpath := FmuEnv.RUNPATH.value:
        return Path(runpath) / MANIFEST_FILENAME
    if casepath:
        return Path(casepath) / MANIFEST_FILENAME
    raise ValueError("Casepath must be provided when running in fmu_context `case`.")


def update_export_manifest(absolute_path: Path, casepath: Path | None = None) -> None:
    """Update the export manifest with a new file entry.
    If the manifest does not exist, it will be created."""
    manifest_path = get_manifest_path(casepath)

    if manifest_path.exists():
        logger.debug(f"Export manifest found at {manifest_path}")
        manifest = ExportManifest.from_file(manifest_path)
    else:
        logger.debug(f"Export manifest not found at {manifest_path}, creating new one.")
        manifest = ExportManifest()

    manifest.add_entry(absolute_path)
    manifest.to_file(manifest_path)


def load_export_manifest(casepath: Path | str | None = None) -> ExportManifest:
    """Load the export manifest from file. If running in a `realization` context
    the manifest location is derived from the environment. If running in a `case`
    context, the casepath must be provided."""

    manifest_path = get_manifest_path(casepath)
    logger.debug(f"Loading export manifest from {manifest_path}")

    if not manifest_path.exists():
        raise FileNotFoundError(f"Export manifest file not found at {manifest_path}")

    return ExportManifest.from_file(manifest_path)
