from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from fmu.dataio._definitions import ValidFormats
from fmu.dataio._logging import null_logger
from fmu.dataio.datastructure.meta import specification
from fmu.dataio.datastructure.meta.content import BoundingBox3D
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

    def get_spec(self) -> dict[str, Any]:
        """Derive data.spec for FaultRoomSurface"""
        logger.info("Get spec for FaultRoomSurface")
        faultsurf = self.obj
        return specification.FaultRoomSurfaceSpecification(
            horizons=faultsurf.horizons,
            faults=faultsurf.faults,
            juxtaposition_hw=faultsurf.juxtaposition_hw,
            juxtaposition_fw=faultsurf.juxtaposition_fw,
            properties=faultsurf.properties,
            name=faultsurf.name,
        ).model_dump(
            mode="json",
            exclude_none=True,
        )

    def get_objectdata(self) -> DerivedObjectDescriptor:
        """Derive object data for FaultRoomSurface"""
        return DerivedObjectDescriptor(
            subtype="JSON",
            classname="surface",
            layout="faultroom_triangulated",
            efolder="maps",
            fmt=(fmt := self.dataio.dict_fformat),
            spec=self.get_spec(),
            bbox=self.get_bbox().model_dump(mode="json", exclude_none=True),
            extension=self._validate_get_ext(fmt, "JSON", ValidFormats().dictionary),
            table_index=None,
        )
