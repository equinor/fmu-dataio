from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from fmu.dataio._definitions import ExportFolder, FileExtension
from fmu.dataio._logging import null_logger
from fmu.dataio.providers.objectdata._utils import Utils
from fmu.datamodels.fmu_results.data import BoundingBox3D
from fmu.datamodels.fmu_results.enums import FileFormat, Layout, ObjectMetadataClass
from fmu.datamodels.fmu_results.global_configuration import (
    GlobalConfiguration,
)
from fmu.datamodels.fmu_results.specification import FaultRoomSurfaceSpecification

from ._base import (
    ObjectDataProvider,
)

if TYPE_CHECKING:
    from io import BytesIO

    from fmu.dataio._readers.faultroom import FaultRoomSurface

logger: Final = null_logger(__name__)


@dataclass
class FaultRoomSurfaceProvider(ObjectDataProvider):
    obj: FaultRoomSurface

    @property
    def classname(self) -> ObjectMetadataClass:
        return ObjectMetadataClass.surface

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.maps.value

    @property
    def extension(self) -> str:
        return FileExtension.json.value

    @property
    def fmt(self) -> FileFormat:
        return FileFormat.json

    @property
    def layout(self) -> Layout:
        return Layout.faultroom_triangulated

    @property
    def table_index(self) -> None:
        """Return the table index."""

    def get_geometry(self) -> None:
        """Derive data.geometry for FaultRoomSurface."""

    def get_bbox(self) -> BoundingBox3D:
        """Derive data.bbox for FaultRoomSurface."""
        logger.info("Get bbox for FaultRoomSurface")
        return BoundingBox3D(
            xmin=float(self.obj.bbox["xmin"]),
            xmax=float(self.obj.bbox["xmax"]),
            ymin=float(self.obj.bbox["ymin"]),
            ymax=float(self.obj.bbox["ymax"]),
            zmin=float(self.obj.bbox["zmin"]),
            zmax=float(self.obj.bbox["zmax"]),
        )

    def get_spec(self) -> FaultRoomSurfaceSpecification:
        """Derive data.spec for FaultRoomSurface"""
        logger.info("Get spec for FaultRoomSurface")

        # Juxtapositions are already ordered according to the strat. column
        # in global config

        juxtaposition_hw = []
        juxtaposition_fw = []
        if isinstance(self.dataio.config, GlobalConfiguration) and (
            strat := self.dataio.config.stratigraphy
        ):
            # Use the name in the juxtaposition list if it doesn't exist
            # in the strat. column
            juxtaposition_hw = [
                Utils.get_stratigraphic_name(strat, juxt) or juxt
                for juxt in self.obj.juxtaposition_hw
            ]
            juxtaposition_fw = [
                Utils.get_stratigraphic_name(strat, juxt) or juxt
                for juxt in self.obj.juxtaposition_fw
            ]

        return FaultRoomSurfaceSpecification(
            horizons=self.obj.horizons,
            faults=self.obj.faults,
            juxtaposition_hw=juxtaposition_hw,
            juxtaposition_fw=juxtaposition_fw,
            properties=self.obj.properties,
            name=self.obj.name,
        )

    def export_to_file(self, file: Path | BytesIO) -> None:
        """Export the object to file or memory buffer"""

        serialized_json = json.dumps(self.obj.storage, indent=4)

        if isinstance(file, Path):
            with open(file, "w", encoding="utf-8") as stream:
                stream.write(serialized_json)
        else:
            file.write(serialized_json.encode("utf-8"))
