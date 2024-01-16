from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class GeologicalModel(BaseModel):
    type: Literal["Structural", "Rock"]


class RockGeologicalModel(GeologicalModel):
    type: Literal["Rock"] = "Rock"


class StructuralGeologicalModel(GeologicalModel):
    type: Literal["Structural"] = "Structural"


class Shape(BaseModel):
    ncol: int = Field(ge=0)
    nrow: int = Field(ge=0)
    nlay: int = Field(ge=0)


class Orientation(BaseModel):
    x: float
    y: float
    z: float


class Grid(BaseModel):
    orientation: Orientation
    shape: Shape
    undef: float | None


class Range(BaseModel):
    start: float
    stop: float


class BoundingBox(BaseModel):
    x: Range
    y: Range
    z: Range


class Header(BaseModel):
    asset: str
    created_at: datetime
    created_by: str
    version: int


class Payland(BaseModel):
    type: Literal["fmu.everest", "fmu.ert"]


class FMUEverest(Payland):
    type: Literal["fmu.everest"] = "fmu.everest"


class FMUErt(BaseModel):
    type: Literal["fmu.ert"] = "fmu.ert"
    model: Annotated[
        StructuralGeologicalModel | RockGeologicalModel,
        Field(discriminator="type"),
    ]


class Export(BaseModel):
    header: Header
    payload: Annotated[
        FMUEverest | FMUErt,
        Field(discriminator="type"),
    ]
