from __future__ import annotations

from pydantic import BaseModel, Field

from . import enums


class RowColumn(BaseModel):
    """Specifies the number of rows and columns in a regular surface object."""

    nrow: int = Field(gt=0)
    """The number of rows."""

    ncol: int = Field(gt=0)
    """The number of columns."""


class RowColumnLayer(RowColumn):
    """Specifies the number of rows, columns, and layers in grid object."""

    nlay: int = Field(gt=0)
    """The number of layers."""


class SurfaceSpecification(RowColumn):
    """Specifies relevant values describing a regular surface object."""

    rotation: float = Field(allow_inf_nan=False)
    """Rotation angle in degrees."""

    undef: float = Field(allow_inf_nan=False)
    """Value representing undefined data."""

    xinc: float = Field(gt=0, allow_inf_nan=False)
    """Increment along the x-axis."""

    yinc: float = Field(gt=0, allow_inf_nan=False)
    """Increment along the y-axis."""

    xori: float = Field(allow_inf_nan=False)
    """Origin along the x-axis."""

    yflip: enums.AxisOrientation
    """Flip along the y-axis, -1 or 1."""

    yori: float = Field(allow_inf_nan=False)
    """Origin along the y-axis."""


# TODO: Base on TableSpecification when we only support table export format for points
class PointSpecification(BaseModel):
    """Specifies relevant values describing an xyz points object."""

    attributes: list[str] | None = Field(default=None)
    """List of columns present in a table."""

    size: int = Field(ge=0, examples=[1, 9999])
    """Size of data object."""

    columns: list[str] | None = Field(default=None)
    """List of columns present in a table."""

    num_columns: int | None = Field(default=None, ge=0, examples=[1, 9999])
    """The number of columns in a table."""

    num_rows: int | None = Field(default=None, ge=0, examples=[1, 9999])
    """The number of rows in a table.."""


class TableSpecification(BaseModel):
    """Specifies relevant values describing a generic tabular data object."""

    columns: list[str]
    """List of columns present in a table."""

    num_columns: int = Field(ge=0, examples=[1, 9999])
    """The number of columns in a table."""

    num_rows: int = Field(ge=0, examples=[1, 9999])
    """The number of rows in a table.."""

    size: int = Field(ge=0, examples=[1, 9999])
    """The total size of the table, i.e. `rows x cols`."""


class CPGridSpecification(RowColumnLayer):
    """Specifies relevant values describing a corner point grid object."""

    xshift: float = Field(allow_inf_nan=False)
    """Shift along the x-axis."""

    yshift: float = Field(allow_inf_nan=False)
    """Shift along the y-axis."""

    zshift: float = Field(allow_inf_nan=False)
    """Shift along the z-axis."""

    xscale: float = Field(allow_inf_nan=False)
    """Scaling factor for the x-axis."""

    yscale: float = Field(allow_inf_nan=False)
    """Scaling factor for the y-axis."""

    zscale: float = Field(allow_inf_nan=False)
    """Scaling factor for the z-axis."""

    zonation: list[ZoneDefinition] | None = Field(default=None)
    """
    Zone names and corresponding layer index ranges. The list is ordered from
    shallowest to deepest zone. Note the layer indices are zero-based; add 1 to
    convert to corresponding layer number.
    """


class ZoneDefinition(BaseModel):
    """Zone name and corresponding layer index min/max"""

    name: str
    """Name of zone"""

    min_layer_idx: int = Field(ge=0)
    """Minimum layer index for the zone"""

    max_layer_idx: int = Field(ge=0)
    """Maximum layer index for the zone"""


class CPGridPropertySpecification(RowColumnLayer):
    """Specifies relevant values describing a corner point grid property object."""


# TODO: Base on TableSpecification when we only support table export format for polygons
class PolygonsSpecification(BaseModel):
    """Specifies relevant values describing a polygon object."""

    npolys: int = Field(ge=0)
    """The number of individual polygons in the data object."""

    columns: list[str] | None = Field(default=None)
    """List of columns present in a table."""

    num_columns: int | None = Field(default=None, ge=0, examples=[1, 9999])
    """The number of columns in a table."""

    num_rows: int | None = Field(default=None, ge=0, examples=[1, 9999])
    """The number of rows in a table.."""

    size: int | None = Field(default=None, ge=0, examples=[1, 9999])
    """The total size of the table, i.e. `rows x cols`."""


class FaultRoomSurfaceSpecification(BaseModel):
    """Specifies relevant values describing a Faultroom surface object."""

    horizons: list[str]
    """List of horizon names."""

    faults: list[str]
    """Names of faults."""

    juxtaposition_hw: list[str]
    """List of zones included in hangingwall juxtaposition."""

    juxtaposition_fw: list[str]
    """List of zones included in footwall juxtaposition."""

    properties: list[str]
    """List of properties along fault plane."""

    name: str
    """A name id of the faultroom usage."""


class TriangulatedSurfaceSpecification(BaseModel):
    """Specifies relevant values describing a triangulated surface."""

    num_vertices: int = Field(ge=0)
    """The number of vertices."""

    num_triangles: int = Field(ge=0)
    """The number of triangles."""


class CubeSpecification(SurfaceSpecification):
    """Specifies relevant values describing a cube object, i.e. a seismic cube."""

    nlay: int = Field(gt=0)
    """The number of layers."""

    xinc: float = Field(gt=0, allow_inf_nan=False)
    """Increment along the x-axis."""

    yinc: float = Field(gt=0, allow_inf_nan=False)
    """Increment along the y-axis."""

    zinc: float = Field(gt=0, allow_inf_nan=False)
    """Increment along the z-axis."""

    xori: float = Field(allow_inf_nan=False)
    """Origin along the x-axis."""

    yori: float = Field(allow_inf_nan=False)
    """Origin along the y-axis."""

    zori: float = Field(allow_inf_nan=False)
    """Origin along the z-axis."""

    yflip: enums.AxisOrientation
    """Flip along the y-axis, -1 or 1."""

    zflip: enums.AxisOrientation
    """Flip along the z-axis, -1 or 1."""

    rotation: float = Field(allow_inf_nan=False)
    """Rotation angle in degrees."""

    undef: float
    """Value representing undefined data."""


AnySpecification = (
    CPGridPropertySpecification
    | CPGridSpecification
    | FaultRoomSurfaceSpecification
    | PointSpecification
    | CubeSpecification
    | PolygonsSpecification
    | SurfaceSpecification
    | TriangulatedSurfaceSpecification
    | TableSpecification
)
