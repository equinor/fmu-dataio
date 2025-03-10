from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    GetJsonSchemaHandler,
    NaiveDatetime,
    RootModel,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

from . import enums
from .specification import AnySpecification
from .standard_result import AnyStandardResult

if TYPE_CHECKING:
    from pydantic_core import CoreSchema


class Timestamp(BaseModel):
    """A timestamp object contains a datetime representation of the time
    being marked and a string label for this timestamp."""

    label: Optional[str] = Field(
        default=None,
        examples=["base", "monitor", "mylabel"],
    )
    """A string label corresponding to the timestamp."""

    value: Union[NaiveDatetime, AwareDatetime] = Field(examples=["2020-10-28T14:28:02"])
    """A datetime representation."""


class Time(BaseModel):
    """A block containing lists of objects describing timestamp information for this
    data object, if applicable, like Flow simulator restart dates, or dates for seismic
    4D surveys.  See :class:`Time`.

    .. note:: ``data.time`` items can currently hold a maximum of two values."""

    t0: Timestamp
    """The first timestamp. See :class:`Timestamp`."""

    t1: Optional[Timestamp] = Field(default=None)
    """The second timestamp. See :class:`Timestamp`."""


class Seismic(BaseModel):
    """
    A block describing seismic data. Shall be present if ``data.content``
    == ``seismic``.
    """

    attribute: Optional[str] = Field(default=None, examples=["amplitude_timeshifted"])
    """A known seismic attribute."""

    calculation: Optional[str] = Field(default=None, examples=["mean"])
    """The type of calculation applied."""

    filter_size: Optional[float] = Field(default=None, allow_inf_nan=False)
    """The filter size applied."""

    scaling_factor: Optional[float] = Field(default=None, allow_inf_nan=False)
    """The scaling factor applied."""

    stacking_offset: Optional[str] = Field(default=None, examples=["0-15"])
    """The stacking offset applied."""

    zrange: Optional[float] = Field(default=None, allow_inf_nan=False)
    """The z-range of these data."""


class FluidContact(BaseModel):
    """
    A block describing a fluid contact. Shall be present if ``data.content``
    == ``fluid_contact``.
    """

    contact: enums.FluidContactType = Field(examples=["owc", "fwl"])
    """A known type of contact."""

    truncated: bool = Field(default=False)
    """If True, this is a representation of a contact surface which is truncated to
    stratigraphy."""

    @field_validator("contact", mode="before")
    def contact_to_lowercase(cls, v: str) -> str:
        if any(c.isupper() for c in v):
            warnings.warn(
                f"You've defined the fluid contact as '{v}' which contains uppercase "
                "characters. In a future version we may require that fluid contacts "
                "should be all lowercase. To ensure future compatibility you should "
                f"change this value to '{v.lower()}'.",
                UserWarning,
            )
        return v.lower()


class FieldOutline(BaseModel):
    """
    A block describing a field outline. Shall be present if ``data.content``
    == "field_outline"
    """

    contact: str
    """A known type of fluid contact used to define the field outline."""


class FieldRegion(BaseModel):
    """
    A block describing a field region. Shall be present if ``data.content``
    == "field_region"
    """

    id: int
    """A known id of the region."""


class Geometry(BaseModel):
    """
    The geometry of the object, i.e. the grid that an object representing a grid
    property is derivative of.
    """

    name: str = Field(examples=["MyGrid"])
    """The name of the grid representing the geometry being linked to."""

    relative_path: str = Field(examples=["some/relative/path/mygrid.roff"])
    """The relative path to the grid on disk."""


class GridModel(BaseModel):
    """A block containing information pertaining to grid model content.
    See :class:`GridModel`.

    .. warning:: This has currently no function and is likely to be deprecated."""

    name: str = Field(examples=["MyGrid"])
    """A name reference to this data."""


class Layer(BaseModel):
    """Used to represent a layer, i.e. top or bottom, of a given stratigraphic
    interval."""

    name: str = Field(examples=["VIKING GP. Top"])
    """This is the identifying name of this data object. For surfaces, this is typically
    the horizon name or similar. Shall be compliant with the stratigraphic column if
    applicable."""

    offset: float = Field(allow_inf_nan=False, default=0)
    """If a specific horizon is represented with an offset, e.g.
    "2 m below Top Volantis"."""

    stratigraphic: bool = Field(default=False)
    """True if this is defined in the stratigraphic column."""


class BoundingBox2D(BaseModel):
    """Contains the 2D coordinates within which a data object is contained."""

    xmin: float = Field(allow_inf_nan=False)
    """Minimum x-coordinate"""

    xmax: float = Field(allow_inf_nan=False)
    """Maximum x-coordinate"""

    ymin: float = Field(allow_inf_nan=False)
    """Minimum y-coordinate"""

    ymax: float = Field(allow_inf_nan=False)
    """Maximum y-coordinate"""


class BoundingBox3D(BoundingBox2D):
    """Contains the 3D coordinates within which a data object is contained."""

    zmin: float = Field(allow_inf_nan=False)
    """Minimum z-coordinate. For regular surfaces this field represents the
    "minimum surface value and it will be absent if all values are undefined."""

    zmax: float = Field(allow_inf_nan=False)
    """Maximum z-coordinate. For regular surfaces this field represents the
    maximum surface value and it will be absent if all values are undefined."""


class Data(BaseModel):
    """
    The ``data`` block contains information about the data contained in this object.
    This class is derived from for more specific content types that are discriminated
    upon by the ``data.content`` field.
    """

    content: enums.Content
    """The type of content these data represent."""

    standard_result: Optional[AnyStandardResult] = Field(default=None)
    """Information about the standard result that these data represent. The presence of
    this field indicates that these data conforms to a specified standard."""

    name: str = Field(examples=["VIKING GP. Top"])
    """This is the identifying name of this data object. For surfaces, this is typically
    the horizon name or similar. Shall be compliant with the stratigraphic column if
    applicable.
    """

    alias: Optional[List[str]] = Field(default=None)
    """Other known-as names for ``data.name``. Typically names used within specific
    software, e.g. RMS and others."""

    tagname: Optional[str] = Field(
        default=None,
        examples=["ds_extract_geogrid", "ds_post_strucmod"],
    )
    """An identifier for this/these data object(s). Similar to the second part of the
    generated filename in disk-oriented FMU data standard.

    You should avoid using tagname as metadata in queries since its value is free-form.
    The intention with tagname is mostly backward compatibility with legacy scratch-file
    naming rules in FMU.
    """

    stratigraphic: bool
    """True if this is defined in the stratigraphic column."""

    description: Optional[List[str]] = Field(default=None)
    """A list of strings, freetext description of this data, if applicable."""

    geometry: Optional[Geometry] = Field(default=None)
    """The geometry of the object, i.e. the grid that an object representing a grid
    property is derivative of. See :class:`Geometry`."""

    bbox: Optional[Union[BoundingBox3D, BoundingBox2D]] = Field(default=None)
    """A block containing the bounding box for this data. Only applicable if the
    object is coordinate-based. See :class:`BoundingBox3D` and
    :class:`BoundingBox2D`."""

    format: enums.FileFormat = Field(examples=["irap_binary"])
    """A reference to a known file format."""

    grid_model: Optional[GridModel] = Field(default=None)
    """A block containing information pertaining to grid model content.
    See :class:`GridModel`.

    .. warning:: This has currently no function and is likely to be deprecated."""

    is_observation: bool
    """True if this is an observation."""

    is_prediction: bool
    """True if this is a prediction."""

    layout: Optional[enums.Layout] = Field(
        default=None,
        examples=["regular", "cornerpoint"],
    )
    """A reference to the layout of the data object. See :class:`enums.Layout`."""

    offset: float = Field(default=0.0, allow_inf_nan=False)
    """If a specific horizon is represented with an offset, e.g.
    "2 m below Top Volantis"."""

    spec: Optional[AnySpecification] = Field(default=None)
    """A block containing the specs for this object, if applicable.
    See :class:`AnySpecification`."""

    time: Optional[Time] = Field(default=None)
    """A block containing lists of objects describing timestamp information for this
    data object, if applicable, like Flow simulator restart dates, or dates for seismic
    4D surveys.  See :class:`Time`.

    .. note:: ``data.time`` items can currently hold a maximum of two values."""

    undef_is_zero: Optional[bool] = Field(default=None)
    """Flag if undefined values are to be interpreted as zero"""

    unit: str = Field(default="", examples=["m"])
    """A reference to a known unit."""

    vertical_domain: Optional[enums.VerticalDomain] = Field(
        default=None,
        examples=["depth", "time"],
    )
    """A reference to a known vertical domain."""

    domain_reference: Optional[enums.DomainReference] = Field(
        default=None,
        examples=["msl", "sb", "rkb"],
    )
    """The reference for the vertical scale of the data."""

    table_index: Optional[List[str]] = Field(
        default=None,
        examples=[["ZONE", "REGION"]],
    )
    """Column names in the table which can be used for indexing. Only applicable if the
    data object is a table."""

    base: Optional[Layer] = Field(default=None)
    """If the data represent an interval, this field can be used to represent its base.
    See :class:`Layer`.

    .. note:: ``top`` is required to use with this."""

    top: Optional[Layer] = Field(default=None)
    """If the data represent an interval, this field can be used to represent its top.
    See :class:`Layer`.

    .. note:: ``base`` is required to use with this."""


class DepthData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for depth type.
    """

    content: Literal[enums.Content.depth]
    """The type of content these data represent."""

    vertical_domain: Literal[enums.VerticalDomain.depth]
    """A reference to a known vertical domain."""

    @field_validator("vertical_domain", mode="before")
    @classmethod
    def set_vertical_domain(cls, v: str) -> Literal[enums.VerticalDomain.depth]:
        """For DepthData the domain should be 'depth'"""
        if v and v != enums.VerticalDomain.depth:
            warnings.warn(
                f"The value of 'vertical_domain' is '{v}'. Since this is a "
                "'depth' content the 'vertical_domain' will be set to 'depth'."
            )
        return enums.VerticalDomain.depth


class FaciesThicknessData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for facies thickness.
    """

    content: Literal[enums.Content.facies_thickness]
    """The type of content these data represent."""


class FaultLinesData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for fault lines.
    """

    content: Literal[enums.Content.fault_lines]
    """The type of content these data represent."""


class FaultPropertiesData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for fault properties.
    """

    content: Literal[enums.Content.fault_properties]
    """The type of content these data represent."""


class FieldOutlineData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for field outlines.
    """

    content: Literal[enums.Content.field_outline]
    """The type of content these data represent."""

    field_outline: FieldOutline
    """A block describing a field outline. See :class:`FieldOutline`."""


class FieldRegionData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for field regions.
    """

    content: Literal[enums.Content.field_region]
    """The type of content these data represent."""

    field_region: FieldRegion
    """A block describing a field region. See :class:`FieldRegion`."""


class FluidContactData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for fluid contacts.
    """

    content: Literal[enums.Content.fluid_contact]
    """The type of content these data represent."""

    fluid_contact: FluidContact
    """A block describing a fluid contact. See :class:`FluidContact`."""


class KPProductData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for KP products.
    """

    content: Literal[enums.Content.khproduct]
    """The type of content these data represent."""


class LiftCurvesData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for lift curves.
    """

    content: Literal[enums.Content.lift_curves]
    """The type of content these data represent."""


class NamedAreaData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for named areas.
    """

    content: Literal[enums.Content.named_area]
    """The type of content these data represent."""


class ParametersData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for parameters.
    """

    content: Literal[enums.Content.parameters]
    """The type of content these data represent."""


class PinchoutData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for pinchouts.
    """

    content: Literal[enums.Content.pinchout]
    """The type of content these data represent."""


class PropertyData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for property data.
    """

    content: Literal[enums.Content.property]
    """The type of content these data represent."""


class PVTData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for pvt data.
    """

    content: Literal[enums.Content.pvt]
    """The type of content these data represent."""


class RegionsData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for regions.
    """

    content: Literal[enums.Content.regions]
    """The type of content these data represent."""


class RelpermData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for relperm.
    """

    content: Literal[enums.Content.relperm]
    """The type of content these data represent."""


class RFTData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for rft data.
    """

    content: Literal[enums.Content.rft]
    """The type of content these data represent."""


class SeismicData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for seismics.
    """

    content: Literal[enums.Content.seismic]
    """The type of content these data represent."""

    seismic: Seismic
    """A block describing seismic data. See :class:`Seismic`."""


class SimulationTimeSeriesData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for simulation time series. This is a time series
    result derived from some simulator like OPM Flow.
    """

    content: Literal[enums.Content.simulationtimeseries]
    """The type of content these data represent."""


class SubcropData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for subcrops.
    """

    content: Literal[enums.Content.subcrop]
    """The type of content these data represent."""


class ThicknessData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for thickness.
    """

    content: Literal[enums.Content.thickness]
    """The type of content these data represent."""


class TimeData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for time.
    """

    content: Literal[enums.Content.time]
    """The type of content these data represent."""

    vertical_domain: Literal[enums.VerticalDomain.time]
    """A reference to a known vertical domain."""

    @field_validator("vertical_domain", mode="before")
    @classmethod
    def set_vertical_domain(cls, v: str) -> Literal[enums.VerticalDomain.time]:
        """For TimeData the domain should be 'time'"""
        if v and v != enums.VerticalDomain.time:
            warnings.warn(
                f"The value of 'vertical_domain' is '{v}'. Since this is a "
                "'time' content the 'vertical_domain' will be set to 'time'."
            )
        return enums.VerticalDomain.time


class TimeSeriesData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for time series.
    """

    content: Literal[enums.Content.timeseries]
    """The type of content these data represent."""


class TransmissibilitiesData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for transmissibilities.
    """

    content: Literal[enums.Content.transmissibilities]
    """The type of content these data represent."""


class VelocityData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for velocities.
    """

    content: Literal[enums.Content.velocity]
    """The type of content these data represent."""


class VolumesData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for volumes.
    """

    content: Literal[enums.Content.volumes]
    """The type of content these data represent."""


class WellPicksData(Data):
    """
    The ``data`` block contains information about the data contained in this object.
    This class contains metadata for well picks.
    """

    content: Literal[enums.Content.wellpicks]
    """The type of content these data represent."""


class AnyData(RootModel):
    """
    The ``data`` block contains information about the data contained in this object.
    This class, ``AnyData``, is a root model that allows for data with more specific
    content types to be placed within it. It can contain the metadata for any data
    object.

    See :class:`Data` to get an overview of all of the subfields used in the ``data``
    block. Between the different content types, only the ``data.content`` field will
    differ. This field indicates the type of content the data are representing.
    """

    root: Annotated[
        Union[
            DepthData,
            FaciesThicknessData,
            FaultLinesData,
            FieldOutlineData,
            FieldRegionData,
            FluidContactData,
            KPProductData,
            LiftCurvesData,
            NamedAreaData,
            ParametersData,
            PinchoutData,
            PropertyData,
            FaultPropertiesData,
            PVTData,
            RegionsData,
            RelpermData,
            RFTData,
            SeismicData,
            SimulationTimeSeriesData,
            SubcropData,
            ThicknessData,
            TimeData,
            TimeSeriesData,
            TransmissibilitiesData,
            VelocityData,
            VolumesData,
            WellPicksData,
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
