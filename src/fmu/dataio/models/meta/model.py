from __future__ import annotations

from collections import ChainMap
from pathlib import Path
from typing import Dict, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, NaiveDatetime, RootModel
from typing_extensions import Annotated

from . import content, enums


class Asset(BaseModel):
    name: str = Field(examples=["Drogon"])


class Ssdl(BaseModel):
    """
    Sub-Surface Data Lake
    """

    access_level: enums.AccessLevel
    rep_include: bool


class Access(BaseModel):
    asset: Asset
    classification: Optional[enums.AccessLevel] = Field(default=None)


class SsdlAccess(Access):
    ssdl: Ssdl


class File(BaseModel):
    """
    Block describing the file as the data appear in FMU context
    """

    absolute_path: Optional[Path] = Field(
        default=None,
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
    size_bytes: Optional[int] = Field(
        default=None,
        description="Size of file object in bytes",
    )


class Parameters(RootModel):
    root: Dict[str, Union[Parameters, int, float, str, Parameters]]


class Aggregation(BaseModel):
    id: UUID = Field(
        description="The ID of this aggregation",
        examples=["15ce3b84-766f-4c93-9050-b154861f9100"],
    )
    operation: str = Field(
        description="The aggregation performed",
    )
    realization_ids: list[int] = Field(
        description="Array of realization ids included in this aggregation"
    )
    parameters: Optional[Parameters] = Field(
        default=None,
        description="Parameters for this realization",
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
    name: str = Field(
        description="The case name",
        examples=["MyCaseName"],
    )
    user: User = Field(
        description="The user name used in ERT",
    )
    uuid: UUID = Field(
        examples=["15ce3b84-766f-4c93-9050-b154861f9100"],
    )
    description: Optional[list[str]] = Field(
        default=None,
    )


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
    uuid: UUID = Field(
        examples=["15ce3b84-766f-4c93-9050-b154861f9100"],
    )
    restart_from: Optional[UUID] = Field(
        default=None,
        description=(
            "A uuid reference to another iteration that this "
            "iteration was restarted from"
        ),
        examples=["15ce3b84-766f-4c93-9050-b154861f9100"],
    )


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
    name: str = Field(
        description="The convential name of this iteration, e.g. iter-0 or pred",
        examples=["iter-0"],
    )
    parameters: Optional[Parameters] = Field(
        default=None,
        description="Parameters for this realization",
    )
    jobs: Optional[RealizationJobs] = Field(
        default=None,
        description=(
            "Content directly taken from the ERT jobs.json file for this realization"
        ),
    )
    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])


class CountryItem(BaseModel):
    identifier: str = Field(
        examples=["Norway"],
    )
    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])


class DiscoveryItem(BaseModel):
    short_identifier: str = Field(
        examples=["SomeDiscovery"],
    )
    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])


class FieldItem(BaseModel):
    identifier: str = Field(
        examples=["OseFax"],
    )
    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])


class CoordinateSystem(BaseModel):
    identifier: str = Field(
        examples=["ST_WGS84_UTM37N_P32637"],
    )
    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])


class StratigraphicColumn(BaseModel):
    identifier: str = Field(
        examples=["DROGON_2020"],
    )
    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])


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
    """
    The FMU block records properties that are specific to FMU
    """

    case: Case
    model: Model
    iteration: Optional[Iteration] = Field(default=None)
    workflow: Optional[Workflow] = Field(default=None)
    aggregation: Optional[Aggregation] = Field(default=None)
    realization: Optional[Realization] = Field(default=None)


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

    # The presence of the a feild controlls what kind of
    # FMUObj it is. The fmu_discriminator will inspects
    # the obj. and returns a tag that tells pydantic
    # what model to use.
    fmu: FMUCase
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
