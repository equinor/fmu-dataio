from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class FMUTimeObject(BaseModel):
    """
    Time stamp for data object.
    """

    label: Optional[str] = Field(
        default=None,
        examples=["base", "monitor", "mylabel"],
    )
    value: Optional[str] = Field(
        default=None,
        examples=["2020-10-28T14:28:02"],
    )


class Time(BaseModel):
    t0: Optional[FMUTimeObject] = None
    t1: Optional[FMUTimeObject] = None


class Seismic(BaseModel):
    """
    Conditional field
    """

    attribute: Optional[str] = Field(
        default=None,
        examples=["amplitude_timeshifted"],
    )
    calculation: Optional[str] = Field(
        default=None,
        examples=["mean"],
    )
    filter_size: Optional[float] = Field(
        default=None,
    )
    scaling_factor: Optional[float] = Field(
        default=None,
    )
    stacking_offset: Optional[str] = Field(
        default=None,
        examples=["0-15"],
    )
    zrange: Optional[float] = Field(
        default=None,
    )


class FluidContact(BaseModel):
    """
    Conditional field
    """

    contact: Literal["owc", "fwl", "goc", "fgl"] = Field(
        examples=["owc", "fwl"],
    )
    truncated: bool = Field(default=False)


class FieldOutline(BaseModel):
    """
    Conditional field
    """

    contact: str


class FieldRegion(BaseModel):
    """
    Conditional field
    """

    id: int = Field(
        description="The ID of the region",
    )


class GridModel(BaseModel):
    name: str = Field(examples=["MyGrid"])


class Layer(BaseModel):
    name: str = Field(
        description=(
            "Name of the data object. If stratigraphic, "
            "match the entry in the stratigraphic column"
        ),
        examples=["VIKING GP. Top"],
    )
    offset: float = Field(
        default=0,
    )
    stratigraphic: bool = Field(
        default=False,
        description=(
            "True if data object represents an entity in the stratigraphic colum"
        ),
    )


class BoundingBox(BaseModel):
    xmin: float = Field(description="Minimum x-coordinate")
    xmax: float = Field(description="Maximum x-coordinate")
    ymin: float = Field(description="Minimum y-coordinate")
    ymax: float = Field(description="Maximum y-coordinate")
    zmin: float = Field(description="Minimum z-coordinate")
    zmax: float = Field(description="Maximum z-coordinate")


class Content(BaseModel):
    content: Literal[
        "depth",
        "time",
        "thickness",
        "property",
        "seismic",
        "fluid_contact",
        "field_outline",
        "field_region",
        "regions",
        "pinchout",
        "subcrop",
        "fault_lines",
        "velocity",
        "volumes",
        "volumetrics",
        "inplace_volumes",
        "khproduct",
        "timeseries",
        "wellpicks",
        "parameters",
        "relperm",
        "rft",
        "pvt",
        "lift_curves",
        "transmissibilities",
    ] = Field(
        description="The contents of this data object",
        examples=["depth"],
    )

    alias: Optional[list[str]] = Field(default=None)
    base: Optional[Layer] = None

    # Only valid for cooridate based meta.
    bbox: Optional[BoundingBox] = Field(default=None)

    description: Optional[list[str]] = Field(
        default=None,
    )
    format: str = Field(
        examples=["irap_binary"],
    )

    grid_model: Optional[GridModel] = Field(default=None)
    is_observation: bool = Field(
        title="Is observation flag",
    )
    is_prediction: bool = Field(
        title="Is prediction flag",
    )
    layout: Optional[str] = Field(
        default=None,
        examples=["regular"],
    )
    name: str = Field(
        description=(
            "Name of the data object. If stratigraphic, "
            "match the entry in the stratigraphic column"
        ),
        examples=["VIKING GP. Top"],
    )
    offset: float = Field(
        default=0.0,
    )
    # spec: Optional[TableSpec | CPGridSpec, ...] = None
    stratigraphic_alias: Optional[list[str]] = Field(default=None)
    stratigraphic: bool = Field(
        description=(
            "True if data object represents an entity in the stratigraphic column"
        ),
    )
    tagname: Optional[str] = Field(
        default=None,
        description="A semi-human readable tag for internal usage and uniqueness",
        examples=["ds_extract_geogrid", "ds_post_strucmod"],
    )
    time: Optional[Time] = Field(default=None)
    top: Optional[Layer] = None

    undef_is_zero: Optional[bool] = Field(
        default=None,
        description="Flag if undefined values are to be interpreted as zero",
    )
    unit: str = Field(
        default="",
        examples=["m"],
    )
    vertical_domain: Optional[Literal["depth", "time"]] = Field(
        default=None,
        examples=["depth"],
    )


class DepthContent(Content):
    content: Literal["depth"]
    depth_reference: Literal["msl", "sb", "rkb"]


class FaultLinesContent(Content):
    content: Literal["fault_lines"]


class FieldOutlineContent(Content):
    content: Literal["field_outline"]
    field_outline: FieldOutline = Field(
        description="Conditional field",
    )


class FieldRegionContent(Content):
    content: Literal["field_region"]
    field_region: FieldRegion = Field(
        description="Conditional field",
    )


class FluidContactContent(Content):
    content: Literal["fluid_contact"]
    fluid_contact: FluidContact = Field(
        description="Conditional field",
    )


class InplaceVolumesContent(Content):
    content: Literal["inplace_volumes"]


class KPProductContent(Content):
    content: Literal["khproduct"]


class LiftCurvesContent(Content):
    content: Literal["lift_curves"]


class ParametersContent(Content):
    content: Literal["parameters"]


class PinchoutContent(Content):
    content: Literal["pinchout"]


class PropertyContent(Content):
    content: Literal["property"]


class PTVContent(Content):
    content: Literal["pvt"]


class RegionsContent(Content):
    content: Literal["regions"]


class RelpermContent(Content):
    content: Literal["relperm"]


class RFTContent(Content):
    content: Literal["rft"]


class SeismicContent(Content):
    content: Literal["seismic"]
    seismic: Seismic = Field(
        description="Conditional field",
    )


class SubcropContent(Content):
    content: Literal["subcrop"]


class ThicknessContent(Content):
    content: Literal["thickness"]


class TimeContent(Content):
    content: Literal["time"]


class TimeSeriesContent(Content):
    content: Literal["timeseries"]


class TransmissibilitiesContent(Content):
    content: Literal["transmissibilities"]


class VelocityContent(Content):
    content: Literal["velocity"]


class VolumesContent(Content):
    content: Literal["volumes"]


class VolumetricsContent(Content):
    content: Literal["volumetrics"]


class WellPicksContent(Content):
    content: Literal["wellpicks"]


AnyContent = Annotated[
    Union[
        DepthContent,
        FaultLinesContent,
        FieldRegionContent,
        InplaceVolumesContent,
        KPProductContent,
        LiftCurvesContent,
        ParametersContent,
        PinchoutContent,
        PropertyContent,
        PTVContent,
        RegionsContent,
        RelpermContent,
        RFTContent,
        SeismicContent,
        SubcropContent,
        ThicknessContent,
        TimeContent,
        TimeSeriesContent,
        VelocityContent,
        VolumesContent,
        VolumetricsContent,
        WellPicksContent,
    ],
    Field(discriminator="content"),
]
