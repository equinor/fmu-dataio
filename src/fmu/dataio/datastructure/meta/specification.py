from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, Field

from . import enums


class RowColumn(BaseModel):
    """Specifies the number of rows and columns in a regular surface object."""

    nrow: int = Field(
        description="The number of rows",
    )
    ncol: int = Field(
        description="The number of columns",
    )


class RowColumnLayer(RowColumn):
    """Specifies the number of rows, columns, and layers in grid object."""

    nlay: int = Field(
        description="The number of layers",
    )


class SurfaceSpecification(RowColumn):
    """Specifies relevant values describing a regular surface object."""

    rotation: float = Field(
        description="Rotation angle",
        allow_inf_nan=False,
    )
    undef: float = Field(
        description="Value representing undefined data",
        allow_inf_nan=False,
    )
    xinc: float = Field(
        description="Increment along the x-axis",
        allow_inf_nan=False,
    )
    # ok to add yinc?
    yinc: float = Field(
        description="Increment along the y-axis",
        allow_inf_nan=False,
    )
    xori: float = Field(
        description="Origin along the x-axis",
        allow_inf_nan=False,
    )
    yflip: enums.AxisOrientation = Field(
        description="Flip along the y-axis, -1 or 1",
    )
    yori: float = Field(
        description="Origin along the y-axis",
        allow_inf_nan=False,
    )


class PointSpecification(BaseModel):
    """Specifies relevant values describing an xyz points object."""

    attributes: Optional[List[str]] = Field(
        description="List of columns present in a table.",
    )
    size: int = Field(
        description="Size of data object.",
        examples=[1, 9999],
    )


class TableSpecification(BaseModel):
    """Specifies relevant values describing a generic tabular data object."""

    columns: List[str] = Field(
        description="List of columns present in a table.",
    )
    size: int = Field(
        description="Size of data object.",
        examples=[1, 9999],
    )


class CPGridSpecification(RowColumnLayer):
    """Specifies relevant values describing a corner point grid object."""

    xshift: float = Field(
        description="Shift along the x-axis",
        allow_inf_nan=False,
    )
    yshift: float = Field(
        description="Shift along the y-axis",
        allow_inf_nan=False,
    )
    zshift: float = Field(
        description="Shift along the z-axis",
        allow_inf_nan=False,
    )

    xscale: float = Field(
        description="Scaling factor for the x-axis",
        allow_inf_nan=False,
    )
    yscale: float = Field(
        description="Scaling factor for the y-axis",
        allow_inf_nan=False,
    )
    zscale: float = Field(
        description="Scaling factor for the z-axis",
        allow_inf_nan=False,
    )


class CPGridPropertySpecification(RowColumnLayer):
    """Specifies relevant values describing a corner point grid property object."""


class PolygonsSpecification(BaseModel):
    """Specifies relevant values describing a polygon object."""

    npolys: int = Field(
        description="The number of individual polygons in the data object",
    )


class FaultRoomSurfaceSpecification(BaseModel):
    """Specifies relevant values describing a Faultroom surface object."""

    horizons: List[str] = Field(
        description="List of horizon names",
    )
    faults: List[str] = Field(
        description="Names of faults",
    )
    juxtaposition_hw: List[str] = Field(
        description="List of zones included in hangingwall juxtaposition",
    )
    juxtaposition_fw: List[str] = Field(
        description="List of zones included in footwall juxtaposition",
    )
    properties: List[str] = Field(
        description="List of properties along fault plane",
    )
    name: str = Field(
        description="A name id of the faultroom usage",
    )


class CubeSpecification(SurfaceSpecification):
    """Specifies relevant values describing a cube object, i.e. a seismic cube."""

    nlay: int = Field(
        description="The number of layers",
    )

    # Increment
    xinc: float = Field(
        description="Increment along the x-axis",
        allow_inf_nan=False,
    )
    yinc: float = Field(
        description="Increment along the y-axis",
        allow_inf_nan=False,
    )
    zinc: float = Field(
        description="Increment along the z-axis",
        allow_inf_nan=False,
    )

    # Origin
    xori: float = Field(
        description="Origin along the x-axis",
        allow_inf_nan=False,
    )
    yori: float = Field(
        description="Origin along the y-axis",
        allow_inf_nan=False,
    )
    zori: float = Field(
        description="Origin along the z-axis",
        allow_inf_nan=False,
    )

    # Miscellaneous
    yflip: enums.AxisOrientation = Field(
        description="Flip along the y-axis, -1 or 1",
    )
    zflip: enums.AxisOrientation = Field(
        description="Flip along the z-axis, -1 or 1",
    )
    rotation: float = Field(
        description="Rotation angle",
        allow_inf_nan=False,
    )
    undef: float = Field(
        description="Value representing undefined data",
    )


AnySpecification = Union[
    CPGridPropertySpecification,
    CPGridSpecification,
    FaultRoomSurfaceSpecification,
    PointSpecification,
    CubeSpecification,
    PolygonsSpecification,
    SurfaceSpecification,
    TableSpecification,
]
