from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from fmu.dataio._definitions import ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio.datastructure.meta.content import BoundingBox3D
from fmu.dataio.datastructure.meta.specification import FaultRoomSurfaceSpecification
from fmu.dataio.readers import FaultRoomSurface

from ._base import (
    DerivedObjectDescriptor,
    ObjectDataProvider,
)

logger: Final = null_logger(__name__)


@dataclass
class FaultRoomSurfaceProvider(ObjectDataProvider):
    obj: FaultRoomSurface

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
        return FaultRoomSurfaceSpecification(
            horizons=self.obj.horizons,
            faults=self.obj.faults,
            juxtaposition_hw=self.obj.juxtaposition_hw,
            juxtaposition_fw=self.obj.juxtaposition_fw,
            properties=self.obj.properties,
            name=self.obj.name,
        )

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for FaultRoomSurface"""
        return DerivedObjectDescriptor(
            subtype="JSON",
            classname="surface",
            layout="faultroom_triangulated",
            efolder="maps",
            fmt=(fmt := self.dataio.dict_fformat),
            spec=self.get_spec().model_dump(mode="json", exclude_none=True),
            bbox=self.get_bbox().model_dump(mode="json", exclude_none=True),
            extension=self._validate_get_ext(fmt, "JSON", ValidFormats().dictionary),
            table_index=None,
        )
