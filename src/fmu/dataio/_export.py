"""Functions for exporting data with and without metadata."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import yaml

from ._logging import null_logger
from ._metadata import generate_export_metadata
from .exceptions import ValidationError
from .manifest._manifest import update_export_manifest
from .providers._filedata import SharePathConstructor
from .providers.objectdata._provider import (
    ObjectDataProvider,
    objectdata_provider_factory,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import BytesIO

    from ._export_config import ExportConfig
    from .types import Inferrable

logger: Final = null_logger(__name__)


def export_without_metadata(export_config: ExportConfig, obj: Inferrable) -> Path:
    """Export object without generating metadata."""
    objdata = objectdata_provider_factory(obj, export_config)
    share_path = SharePathConstructor(export_config, objdata).get_share_path()
    absolute_path = export_config.runcontext.exportroot / share_path

    export_object_to_file(absolute_path, objdata.export_to_file)

    return absolute_path


def export_with_metadata(export_config: ExportConfig, obj: Inferrable) -> Path:
    """Export object with full metadata."""
    if export_config.standard_result is not None and export_config.config is None:
        raise ValidationError(
            "When exporting standard_results it is required to have a valid config."
        )

    objdata = objectdata_provider_factory(obj, export_config)
    metadata = _generate_metadata(export_config, objdata)

    outfile = Path(metadata["file"]["absolute_path"])
    metafile = outfile.parent / f".{outfile.name}.yml"

    export_object_to_file(outfile, objdata.export_to_file)
    logger.info("Actual file is %s", outfile)

    export_metadata_file(metafile, metadata)
    logger.info("Metadata file is: %s", metafile)

    _update_manifest_if_needed(export_config, outfile)

    return outfile


def generate_metadata(export_config: ExportConfig, obj: Inferrable) -> dict[str, Any]:
    """Generate metadata without exporting."""
    objdata = objectdata_provider_factory(obj, export_config)
    return _generate_metadata(export_config, objdata)


def _generate_metadata(
    export_config: ExportConfig, objdata: ObjectDataProvider
) -> dict[str, Any]:
    """Generate metadata dict from object data provider."""
    return generate_export_metadata(
        objdata=objdata,
        export_config=export_config,
    ).model_dump(mode="json", exclude_none=True, by_alias=True)


def _update_manifest_if_needed(export_config: ExportConfig, outfile: Path) -> None:
    """Update the export manifest with a new path if inside FMU."""
    if not export_config.runcontext.inside_fmu:
        return
    update_export_manifest(outfile, casepath=export_config.runcontext.casepath)


def export_object_to_file(
    file: Path | BytesIO,
    export_function: Callable[[Path | BytesIO], None],
) -> None:
    """Export an object to file or memory buffer using a provided export function."""
    if isinstance(file, Path):
        file.parent.mkdir(parents=True, exist_ok=True)

    export_function(file)


def export_metadata_file(file: Path, metadata: dict) -> None:
    """Export metadata to a YAML file."""
    if not metadata:
        raise RuntimeError(
            "Export of metadata was requested, but no metadata are present."
        )

    with open(file, "w", encoding="utf8") as stream:
        stream.write(yaml.safe_dump(metadata, allow_unicode=True))

    logger.info("Yaml file on: %s", file)
