from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from fmu.dataio._definitions import ExportFolder, ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio._models.fmu_results.data import BoundingBox3D
from fmu.dataio._models.fmu_results.enums import FileFormat, FMUClass, Layout
from fmu.dataio._models.fmu_results.global_configuration import (
    GlobalConfiguration,
)
from fmu.dataio._models.fmu_results.specification import FaultRoomSurfaceSpecification
from fmu.dataio.providers.objectdata._utils import Utils

from ._base import (
    ObjectDataProvider,
)

if TYPE_CHECKING:
    from fmu.dataio.readers import FaultRoomSurface

logger: Final = null_logger(__name__)


@dataclass
class FaultRoomSurfaceProvider(ObjectDataProvider):
    obj: FaultRoomSurface

    @property
    def classname(self) -> FMUClass:
        return FMUClass.surface

    @property
    def efolder(self) -> str:
        return self.dataio.forcefolder or ExportFolder.maps.value

    @property
    def extension(self) -> str:
        return self._validate_get_ext(self.fmt.value, ValidFormats.dictionary)

    @property
    def fmt(self) -> FileFormat:
        return FileFormat(self.dataio.dict_fformat)

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
            xmax=float(self.obj.bbox["xmin"]),
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
