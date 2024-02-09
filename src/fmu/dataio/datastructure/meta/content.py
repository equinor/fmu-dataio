from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, GetJsonSchemaHandler, RootModel, model_validator
from pydantic_core import CoreSchema
from typing_extensions import Annotated

from . import enums, specification


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
        allow_inf_nan=False,
        default=None,
    )
    scaling_factor: Optional[float] = Field(
        allow_inf_nan=False,
        default=None,
    )
    stacking_offset: Optional[str] = Field(
        default=None,
        examples=["0-15"],
    )
    zrange: Optional[float] = Field(
        allow_inf_nan=False,
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
        allow_inf_nan=False,
        default=0,
    )
    stratigraphic: bool = Field(
        default=False,
        description=(
            "True if data object represents an entity in the stratigraphic colum"
        ),
    )


class BoundingBox(BaseModel):
    xmin: float = Field(
        description="Minimum x-coordinate",
        allow_inf_nan=False,
    )
    xmax: float = Field(
        description="Maximum x-coordinate",
        allow_inf_nan=False,
    )
    ymin: float = Field(
        description="Minimum y-coordinate",
        allow_inf_nan=False,
    )
    ymax: float = Field(
        description="Maximum y-coordinate",
        allow_inf_nan=False,
    )
    zmin: float = Field(
        description="Minimum z-coordinate",
        allow_inf_nan=False,
    )
    zmax: float = Field(
        description="Maximum z-coordinate",
        allow_inf_nan=False,
    )


class Content(BaseModel):
    content: enums.ContentEnum = Field(description="The contents of this data object")

    alias: Optional[List[str]] = Field(default=None)

    # Only valid for cooridate based meta.
    bbox: Optional[BoundingBox] = Field(default=None)

    description: Optional[List[str]] = Field(
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
        allow_inf_nan=False,
    )
    spec: Optional[specification.AnySpecification] = Field(default=None)
    stratigraphic_alias: Optional[List[str]] = Field(default=None)
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

    # Both must be set, or none.
    base: Optional[Layer] = None
    top: Optional[Layer] = None


class DepthContent(Content):
    content: Literal[enums.ContentEnum.depth]
    depth_reference: Literal["msl", "sb", "rkb"]


class FaciesThicknessContent(Content):
    content: Literal[enums.ContentEnum.facies_thickness]


class FaultLinesContent(Content):
    content: Literal[enums.ContentEnum.fault_lines]


class FieldOutlineContent(Content):
    content: Literal[enums.ContentEnum.field_outline]
    field_outline: FieldOutline = Field(
        description="Conditional field",
    )


class FieldRegionContent(Content):
    content: Literal[enums.ContentEnum.field_region]
    field_region: FieldRegion = Field(
        description="Conditional field",
    )


class FluidContactContent(Content):
    content: Literal[enums.ContentEnum.fluid_contact]
    fluid_contact: FluidContact = Field(
        description="Conditional field",
    )


class InplaceVolumesContent(Content):
    content: Literal[enums.ContentEnum.inplace_volumes]


class KPProductContent(Content):
    content: Literal[enums.ContentEnum.khproduct]


class LiftCurvesContent(Content):
    content: Literal[enums.ContentEnum.lift_curves]


class ParametersContent(Content):
    content: Literal[enums.ContentEnum.parameters]


class PinchoutContent(Content):
    content: Literal[enums.ContentEnum.pinchout]


class PropertyContent(Content):
    content: Literal[enums.ContentEnum.property]


class PVTContent(Content):
    content: Literal[enums.ContentEnum.pvt]


class RegionsContent(Content):
    content: Literal[enums.ContentEnum.regions]


class RelpermContent(Content):
    content: Literal[enums.ContentEnum.relperm]


class RFTContent(Content):
    content: Literal[enums.ContentEnum.rft]


class SeismicContent(Content):
    content: Literal[enums.ContentEnum.seismic]
    seismic: Seismic = Field(
        description="Conditional field",
    )


class SubcropContent(Content):
    content: Literal[enums.ContentEnum.subcrop]


class ThicknessContent(Content):
    content: Literal[enums.ContentEnum.thickness]


class TimeContent(Content):
    content: Literal[enums.ContentEnum.time]


class TimeSeriesContent(Content):
    content: Literal[enums.ContentEnum.timeseries]


class TransmissibilitiesContent(Content):
    content: Literal[enums.ContentEnum.transmissibilities]


class VelocityContent(Content):
    content: Literal[enums.ContentEnum.velocity]


class VolumesContent(Content):
    content: Literal[enums.ContentEnum.volumes]


class VolumetricsContent(Content):
    content: Literal[enums.ContentEnum.volumetrics]


class WellPicksContent(Content):
    content: Literal[enums.ContentEnum.wellpicks]


class AnyContent(RootModel):
    root: Annotated[
        Union[
            DepthContent,
            FaciesThicknessContent,
            FaultLinesContent,
            FieldOutlineContent,
            FieldRegionContent,
            FluidContactContent,
            InplaceVolumesContent,
            KPProductContent,
            LiftCurvesContent,
            ParametersContent,
            PinchoutContent,
            PropertyContent,
            PVTContent,
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

    @model_validator(mode="before")
    @classmethod
    def _top_and_base_(cls, values: Dict) -> Dict:
        top, base = values.get("top"), values.get("base")
        if top is None and base is None:
            return values
        if top is not None and base is not None:
            return values
        raise ValueError("Both 'top' and 'base' must be set together or both be unset")

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> Dict[str, Any]:
        json_schema = super().__get_pydantic_json_schema__(core_schema, handler)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.update(
            {
                "dependencies": {
                    "top": {"required": ["base"]},
                    "base": {"required": ["top"]},
                }
            }
        )
        return json_schema
