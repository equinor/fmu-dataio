from __future__ import annotations

from collections import ChainMap
from pathlib import Path
from typing import Dict, Literal, Optional, Union

from pydantic import BaseModel, Field, NaiveDatetime, RootModel
from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import Annotated

from . import content, enums


class UUID(RootModel[str]):
    root: str = Field(
        examples=["ad214d85-8a1d-19da-e053-c918a4889309"],
        pattern=r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$",
    )


class Asset(BaseModel):
    name: str = Field(examples=["Drogon"])


class Ssdl(BaseModel):
    """
    Sub-Surface Data Lake
    """

    access_level: Literal["internal", "restricted", "asset"]
    rep_include: bool


class Access(BaseModel):
    asset: Asset
    classification: Literal["internal", "restricted", "asset"] | None = Field(
        default=None
    )


class SsdlAccess(Access):
    ssdl: Ssdl


class Shape(BaseModel):
    nrow: int = Field(description="The number of rows")
    ncol: int = Field(description="The number of columns")
    nlay: int = Field(description="The number of layers")


class CaseSpec(BaseModel):
    ...


class SurfaceSpec(Shape):
    rotation: float = Field(description="Rotation angle")
    undef: float = Field(description="Value representing undefined data")
    xinc: float = Field(description="Increment along the x-axis")
    xori: float = Field(description="Origin along the x-axis")
    yflip: Literal[-1, 1] = Field(description="Flip along the y-axis, -1 or 1")
    yori: float = Field(description="Origin along the y-axis")


class TableSpec(BaseModel):
    columns: list[str] = Field(
        description="List of columns present in a table.",
    )
    size: int = Field(
        description="Size of data object.",
        examples=[1, 9999],
    )


class CPGridSpec(Shape):
    """Corner point grid"""

    xshift: float = Field(description="Shift along the x-axis")
    yshift: float = Field(description="Shift along the y-axis")
    zshift: float = Field(description="Shift along the z-axis")

    xscale: float = Field(description="Scaling factor for the x-axis")
    yscale: float = Field(description="Scaling factor for the y-axis")
    zscale: float = Field(description="Scaling factor for the z-axis")


class CPGridPropertySpec(Shape):
    ...


class PolygonsSpec(BaseModel):
    npolys: int = Field(
        description="The number of individual polygons in the data object",
    )


class CubeSpec(SurfaceSpec):
    # Increment
    xinc: float = Field(description="Increment along the x-axis")
    yinc: float = Field(description="Increment along the y-axis")
    zinc: float = Field(description="Increment along the z-axis")

    # Origin
    xori: float = Field(description="Origin along the x-axis")
    yori: float = Field(description="Origin along the y-axis")
    zori: float = Field(description="Origin along the z-axis")

    # Miscellaneous
    yflip: Literal[-1, 1] = Field(description="Flip along the y-axis, -1 or 1")
    zflip: Literal[-1, 1] = Field(description="Flip along the z-axis, -1 or 1")
    rotation: float = Field(description="Rotation angle")
    undef: float = Field(description="Value representing undefined data")


class WellSpec(BaseModel):
    ...


class PointsSpec(BaseModel):
    ...


class DictionarySpec(BaseModel):
    ...


class File(BaseModel):
    """
    Block describing the file as the data appear in FMU context
    """

    absolute_path: Path = Field(
        description="The absolute file path",
        examples=["/abs/path/share/results/maps/volantis_gp_base--depth.gri"],
    )
    relative_path: Path = Field(
        description="The file path relative to RUNPATH",
        examples=["share/results/maps/volantis_gp_base--depth.gri"],
    )
    checksum_md5: str = Field(
        description="md5 checksum of the file or bytestring",
        examples=["kjhsdfvsdlfk23knerknvk23"],
    )
    size_bytes: int | None = Field(
        default=None,
        description="Size of file object in bytes",
    )


class Parameters(RootModel[Dict[str, Union[int, float, str, dict]]]):
    ...


class Aggregation(BaseModel):
    id: UUID = Field(
        description="The ID of this aggregation",
        examples=["15ce3b84-766f-4c93-9050-b154861f9100"],
    )
    operation: str = Field(
        description="The aggregation performed",
    )
    parameters: Parameters = Field(
        description="Parameters for this realization",
    )
    realization_ids: list[int] = Field(
        description="Array of realization ids included in this aggregation"
    )


class Workflow(BaseModel):
    reference: str = Field(
        description="Reference to the part of the FMU workflow that produced this"
    )


class User(BaseModel):
    id: str = Field(
        examples=["peesv", "jlov"],
        title="User ID",
    )


class Case(BaseModel):
    description: Optional[list[str]] = None
    name: str = Field(
        description="The case name",
        examples=["MyCaseName"],
    )
    user: User = Field(
        description="The user name used in ERT",
    )
    uuid: UUID


class Iteration(BaseModel):
    id: int = Field(
        description=(
            "The internal identification of this iteration, e.g. the iteration number"
        ),
    )
    name: str = Field(
        description="The convential name of this iteration, e.g. iter-0 or pred",
        examples=["iter-0"],
    )
    restart_from: UUID | None = Field(
        default=None,
        description=(
            "A uuid reference to another iteration that this "
            "iteration was restarted from"
        ),
    )

    uuid: UUID


class Model(BaseModel):
    description: Optional[list[str]] = Field(
        default=None,
        description="This is a free text description of the model setup",
    )
    name: Optional[str] = Field(
        default=None,
        examples=["Drogon"],
    )
    revision: Optional[str] = Field(
        default=None,
        examples=["21.0.0.dev"],
    )


class RealizationJobListing(BaseModel):
    arg_types: list[str]
    argList: list[Path]
    error_file: Optional[Path]
    executable: Path
    license_path: Optional[Path]
    max_arg: int
    max_running_minutes: Optional[int]
    max_running: Optional[int]
    min_arg: int
    name: str
    start_file: Optional[str]
    stderr: Optional[str]
    stdin: Optional[str]
    stdout: Optional[str]
    target_file: Optional[Path]


class RealizationJobs(BaseModel):
    data_root: Path = Field(alias="DATA_ROOT")
    ert_pid: str
    global_environment: dict[str, str]
    global_update_path: dict
    job_list: list[RealizationJobListing] = Field(alias="jobList")
    run_id: str
    umask: str


class Realization(BaseModel):
    id: int = Field(
        description="The unique number of this realization as used in FMU",
    )
    jobs: Optional[RealizationJobs] = Field(
        default=None,
        description=(
            "Content directly taken from the ERT jobs.json file for this realization"
        ),
    )
    name: str = Field(
        description="The convential name of this iteration, e.g. iter-0 or pred",
        examples=["iter-0"],
    )
    parameters: Parameters | None = Field(
        default=None,
        description="Parameters for this realization",
    )
    uuid: UUID


class CountryItem(BaseModel):
    identifier: str = Field(
        examples=["Norway"],
    )
    uuid: UUID


class DiscoveryItem(BaseModel):
    short_identifier: str = Field(
        examples=["SomeDiscovery"],
    )
    uuid: UUID


class FieldItem(BaseModel):
    identifier: str = Field(
        examples=["OseFax"],
    )
    uuid: UUID


class CoordinateSystem(BaseModel):
    identifier: str = Field(
        examples=["ST_WGS84_UTM37N_P32637"],
    )
    uuid: UUID


class StratigraphicColumn(BaseModel):
    identifier: str = Field(
        examples=["DROGON_2020"],
    )
    uuid: UUID


class Smda(BaseModel):
    coordinate_system: CoordinateSystem
    country: list[CountryItem]
    discovery: list[DiscoveryItem]
    field: list[FieldItem]
    stratigraphic_column: StratigraphicColumn


class Masterdata(BaseModel):
    smda: Smda


class TracklogEvent(BaseModel):
    # TODO: Update ex. to inc. timezone
    # update NaiveDatetime ->  AwareDatetime
    datetime: NaiveDatetime = Field(
        examples=["2020-10-28T14:28:02"],
    )
    event: str = Field(
        examples=["created", "updated"],
    )
    user: User


class FMUCase(BaseModel):
    case: Case
    model: Model


class FMUDataObj(FMUCase):
    iteration: Optional[Iteration] = None
    workflow: Optional[Workflow] = None


class FMUAggregation(FMUDataObj):
    """
    The FMU block records properties that are specific to FMU
    """

    aggregation: Aggregation


class FMURealization(FMUDataObj):
    """
    The FMU block records properties that are specific to FMU
    """

    realization: Realization


class ClassMeta(BaseModel):
    class_: enums.FMUClassEnum = Field(
        alias="class",
        title="Metadata class",
    )
    masterdata: Masterdata
    tracklog: list[TracklogEvent]
    source: Literal["fmu"] = Field(description="Data source (FMU)")
    version: Literal["0.8.0"] = Field(title="FMU results metadata version")


class FMUCaseClassMeta(ClassMeta):
    class_: Literal[enums.FMUClassEnum.case] = Field(
        alias="class",
        title="Metadata class",
    )
    fmu: FMUCase
    access: Access


class FMUDataClassMeta(ClassMeta):
    class_: Literal[
        enums.FMUClassEnum.surface,
        enums.FMUClassEnum.table,
        enums.FMUClassEnum.cpgrid,
        enums.FMUClassEnum.cpgrid_property,
        enums.FMUClassEnum.polygons,
        enums.FMUClassEnum.cube,
        enums.FMUClassEnum.well,
        enums.FMUClassEnum.points,
        enums.FMUClassEnum.dictionary,
    ] = Field(
        alias="class",
        title="Metadata class",
    )
    fmu: Union[FMUAggregation, FMURealization, FMUCase]
    access: SsdlAccess
    data: content.AnyContent
    file: File


class Root(
    RootModel[
        Annotated[
            Union[
                FMUCaseClassMeta,
                FMUDataClassMeta,
            ],
            Field(discriminator="class_"),
        ]
    ]
):
    ...


def dump() -> dict:
    return dict(
        ChainMap(
            {
                "$id": "https://main-fmu-schemas-dev.radix.equinor.com/schemas/0.8.0/fmu_results.json",
                "$schema": GenerateJsonSchema.schema_dialect,
                "$contractual": [
                    "class",
                    "source",
                    "version",
                    "tracklog",
                    "data.format",
                    "data.name",
                    "data.stratigraphic",
                    "data.alias",
                    "data.stratigraphic_alias",
                    "data.offset",
                    "data.content",
                    "data.tagname",
                    "data.vertical_domain",
                    "data.grid_model",
                    "data.bbox",
                    "data.time",
                    "data.is_prediction",
                    "data.is_observation",
                    "data.seismic.attribute",
                    "data.spec.columns",
                    "access",
                    "masterdata",
                    "fmu.model",
                    "fmu.workflow",
                    "fmu.case",
                    "fmu.iteration.name",
                    "fmu.iteration.uuid",
                    "fmu.realization.name",
                    "fmu.realization.id",
                    "fmu.realization.uuid",
                    "fmu.aggregation.operation",
                    "fmu.aggregation.realization_ids",
                    "fmu.context.stage",
                    "file.relative_path",
                    "file.checksum_md5",
                    "file.size_bytes",
                ],
            },
            Root.model_json_schema(
                by_alias=True,
            ),
        )
    )
