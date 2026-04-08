"""Functions for exporting data with and without metadata."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import yaml

from fmu.dataio._logging import null_logger
from fmu.dataio._metadata import (
    SharePathConstructor,
    _generate_metadata,
    create_object_data,
)
from fmu.dataio.exceptions import ValidationError
from fmu.dataio.manifest._manifest import update_export_manifest
from fmu.dataio.types import ExportableData

from .serialize import export_object

if TYPE_CHECKING:
    from fmu.dataio.types import ExportableData

    from ._export_config import ExportConfig

logger: Final = null_logger(__name__)


def export_without_metadata(export_config: ExportConfig, obj: ExportableData) -> Path:
    """Export object without generating metadata."""
    objdata = create_object_data(obj, export_config)
    share_path = SharePathConstructor(export_config, objdata).get_share_path()
    absolute_path = export_config.runcontext.exportroot / share_path

    _write_object(absolute_path, objdata)

    return absolute_path


def export_with_metadata(export_config: ExportConfig, obj: ExportableData) -> Path:
    """Export object with full metadata."""
    if export_config.standard_result is not None and export_config.config is None:
        raise ValidationError(
            "When exporting standard_results it is required to have a valid config."
        )

    objdata = create_object_data(obj, export_config)
    metadata = _generate_metadata(export_config, objdata)

    outfile = Path(metadata["file"]["absolute_path"])
    metafile = outfile.parent / f".{outfile.name}.yml"

    _write_object(outfile, objdata)
    logger.info("Actual file is %s", outfile)

    export_metadata_file(metafile, metadata)
    logger.info("Metadata file is: %s", metafile)

    _update_manifest_if_needed(export_config, outfile)

    return outfile


def _update_manifest_if_needed(export_config: ExportConfig, outfile: Path) -> None:
    """Update the export manifest with a new path if inside FMU."""
    if not export_config.runcontext.inside_fmu:
        return
    update_export_manifest(outfile, casepath=export_config.runcontext.casepath)


def _write_object(file: Path, objdata: ExportableData) -> None:
    """Write an object to a file, creating parent directories as needed."""
    file.parent.mkdir(parents=True, exist_ok=True)
    export_object(objdata, file)


def export_metadata_file(file: Path, metadata: dict) -> None:
    """Export metadata to a YAML file."""
    if not metadata:
        raise RuntimeError(
            "Export of metadata was requested, but no metadata are present."
        )

    with open(file, "w", encoding="utf8") as stream:
        stream.write(yaml.safe_dump(metadata, allow_unicode=True))

    logger.info("Yaml file on: %s", file)
