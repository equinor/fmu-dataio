"""Service for exporting data and metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._logging import null_logger
from ._metadata import generate_export_metadata
from ._utils import export_metadata_file, export_object_to_file
from .exceptions import ValidationError
from .manifest._manifest import update_export_manifest
from .providers._filedata import SharePathConstructor
from .providers.objectdata._provider import (
    ObjectDataProvider,
    objectdata_provider_factory,
)

if TYPE_CHECKING:
    from fmu.datamodels.fmu_results.standard_result import StandardResult

    from ._export_config import ExportConfig
    from .types import Inferrable

logger = null_logger(__name__)


@dataclass(frozen=True)
class ExportService:
    """Handles the exporting files with metadata."""

    export_config: ExportConfig

    def export_without_metadata(self, obj: Inferrable) -> Path:
        """Export object without generating metadata."""
        objdata = objectdata_provider_factory(obj, self.export_config)
        share_path = SharePathConstructor(self.export_config, objdata).get_share_path()
        absolute_path = self.export_config.runcontext.exportroot / share_path

        export_object_to_file(absolute_path, objdata.export_to_file)

        return absolute_path

    def export_with_metadata(
        self,
        obj: Inferrable,
        *,
        standard_result: StandardResult | None = None,
    ) -> Path:
        """Export object with full metadata."""
        if standard_result and self.export_config.config is None:
            raise ValidationError(
                "When exporting standard_results it is required to have a valid config."
            )

        objdata = objectdata_provider_factory(obj, self.export_config, standard_result)
        metadata = self._generate_metadata(objdata)

        outfile = Path(metadata["file"]["absolute_path"])
        metafile = outfile.parent / f".{outfile.name}.yml"

        export_object_to_file(outfile, objdata.export_to_file)
        logger.info(f"Actual file is {outfile}")

        export_metadata_file(metafile, metadata)
        logger.info(f"Metadata file is: {metafile}")

        self._update_manifest_if_needed(outfile)
        return outfile

    def generate_metadata(
        self, obj: Inferrable, *, standard_result: StandardResult | None = None
    ) -> dict[str, Any]:
        """Generate metadata without exporting."""
        objdata = objectdata_provider_factory(obj, self.export_config, standard_result)
        return self._generate_metadata(objdata)

    def _generate_metadata(self, objdata: ObjectDataProvider) -> dict[str, Any]:
        return generate_export_metadata(
            objdata=objdata,
            export_config=self.export_config,
        ).model_dump(mode="json", exclude_none=True, by_alias=True)

    def _update_manifest_if_needed(self, outfile: Path) -> None:
        """Updates the export manifest with a new path."""
        if not self.export_config.runcontext.inside_fmu:
            return

        update_export_manifest(outfile, casepath=self.export_config.runcontext.casepath)
