from __future__ import annotations

from collections import ChainMap
from pathlib import Path
from typing import Dict, List, Literal, Optional, TypeVar, Union
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    GetJsonSchemaHandler,
    NaiveDatetime,
    RootModel,
    model_validator,
)
from pydantic_core import CoreSchema
from typing_extensions import Annotated

from . import content, enums

T = TypeVar("T", Dict, List, object)


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
    checksum_md5: Optional[str] = Field(
        description="md5 checksum of the file or bytestring",
        examples=["kjhsdfvsdlfk23knerknvk23"],
    )
    size_bytes: Optional[int] = Field(
        default=None,
        description="Size of file object in bytes",
    )

    relative_path_symlink: Optional[Path] = Field(default=None)
    absolute_path_symlink: Optional[Path] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _check_for_non_ascii_in_path(cls, values: Dict) -> Dict:
        if (path := values.get("absolute_path")) and not str(path).isascii():
            raise ValueError(
                f"Path has non-ascii elements which is not supported: {path}"
            )
        return values


class Parameters(RootModel):
    root: Dict[str, Union[Parameters, int, float, str]]


class Aggregation(BaseModel):
    id: UUID = Field(
        description="The ID of this aggregation",
        examples=["15ce3b84-766f-4c93-9050-b154861f9100"],
    )
    operation: str = Field(
        description="The aggregation performed",
    )
    realization_ids: List[int] = Field(
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


class FMUCase(BaseModel):
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
    description: Optional[List[str]] = Field(
        default=None,
    )


class Iteration(BaseModel):
    id: Optional[int] = Field(
        default=None,
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


class FMUModel(BaseModel):
    description: Optional[List[str]] = Field(
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
    arg_types: List[str]
    argList: List[Path]
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
    jobs: Optional[object] = Field(
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
    country: List[CountryItem]
    discovery: List[DiscoveryItem]
    field: List[FieldItem]
    stratigraphic_column: StratigraphicColumn


class Masterdata(BaseModel):
    smda: Smda


class VersionInformation(BaseModel):
    version: str


class SystemInformationOperatingSystem(BaseModel):
    """
    This model encapsulates various pieces of
    system-related information using Python's platform module. It provides a
    structured way to access details about the system's hardware, operating
    system, and interpreter version information.
    """

    hostname: str = Field(
        title="Hostname",
        description="The network name of the computer, possibly not fully qualified.",
        examples=["Johns-MacBook-Pro.local"],
    )

    operating_system: str = Field(
        title="Platform",
        description=(
            "A detailed string identifying the underlying platform "
            "with as much useful information as possible."
        ),
        examples=["Darwin-18.7.0-x86_64-i386-64bit"],
    )

    release: str = Field(
        title="Release",
        description="The system's release version, such as a version number or a name.",
        examples=["18.7.0"],
    )

    system: str = Field(
        title="System",
        description="The name of the operating system.",
        examples=["Darwin"],
    )

    version: str = Field(
        title="Version",
        description="The specific release version of the system.",
        examples=["#1 SMP Tue Aug 27 21:37:59 PDT 2019"],
    )


class SystemInformation(BaseModel):
    fmu_dataio: Optional[VersionInformation] = Field(
        alias="fmu-dataio",
        default=None,
        examples=["1.2.3"],
    )
    komodo: Optional[VersionInformation] = Field(
        default=None,
        examples=["2023.12.05-py38"],
    )
    operating_system: Optional[SystemInformationOperatingSystem] = Field(
        default=None,
    )


class TracklogEvent(BaseModel):
    # TODO: Update ex. to inc. timezone
    # update NaiveDatetime ->  AwareDatetime
    # On upload, sumo adds timezone if its lacking.
    # For roundtripping i need an Union here.
    datetime: Union[NaiveDatetime, AwareDatetime] = Field(
        examples=["2020-10-28T14:28:02"],
    )
    event: str = Field(
        examples=["created", "updated", "merged"],
    )
    user: User
    sysinfo: Optional[SystemInformation] = Field(
        default_factory=SystemInformation,
    )


class Display(BaseModel):
    name: Optional[str] = Field(default=None)


class Context(BaseModel):
    """The internal FMU context in which this data object was produced"""

    stage: Literal[
        "case",
        "iteration",
        "realization",
    ]


class FMUClassMetaCase(BaseModel):
    """
    The FMU block records properties that are specific to FMU
    """

    case: FMUCase
    model: FMUModel


class FMUClassMetaData(BaseModel):
    """
    The FMU block records properties that are specific to FMU
    """

    case: FMUCase
    context: Context
    model: FMUModel
    iteration: Optional[Iteration] = Field(default=None)
    workflow: Optional[Workflow] = Field(default=None)
    aggregation: Optional[Aggregation] = Field(default=None)
    realization: Optional[Realization] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _dependencies_aggregation_realization(cls, values: Dict) -> Dict:
        aggregation, realization = values.get("aggregation"), values.get("realization")
        if aggregation and realization:
            raise ValueError(
                "Both 'aggregation' and 'realization' cannot be set "
                "at the same time. Please set only one."
            )
        return values

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> Dict[str, object]:
        json_schema = super().__get_pydantic_json_schema__(core_schema, handler)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.update(
            {
                "dependencies": {
                    "aggregation": {"not": {"required": ["realization"]}},
                    "realization": {"not": {"required": ["aggregation"]}},
                }
            }
        )
        return json_schema


class ClassMeta(BaseModel):
    class_: enums.FMUClassEnum = Field(
        alias="class",
        title="Metadata class",
    )
    masterdata: Masterdata
    tracklog: List[TracklogEvent]
    source: Literal["fmu"] = Field(description="Data source (FMU)")
    version: Literal["0.8.0"] = Field(title="FMU results metadata version")


class FMUCaseClassMeta(ClassMeta):
    class_: Literal[enums.FMUClassEnum.case] = Field(
        alias="class",
        title="Metadata class",
    )
    fmu: FMUClassMetaCase
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
    fmu: FMUClassMetaData
    access: SsdlAccess
    data: content.AnyContent
    file: File
    display: Display


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
    @model_validator(mode="after")
    def _check_class_data_spec(self) -> Root:
        if (
            self.root.class_ in (enums.FMUClassEnum.table, enums.FMUClassEnum.surface)
            and hasattr(self.root, "data")
            and self.root.data.root.spec is None
        ):
            raise ValueError(
                "When 'class' is 'table' or 'surface', "
                "'data' must contain the 'spec' field."
            )
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> Dict[str, object]:
        json_schema = super().__get_pydantic_json_schema__(core_schema, handler)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.update(
            {
                "if": {"properties": {"class": {"enum": ["table", "surface"]}}},
                "then": {"properties": {"data": {"required": ["spec"]}}},
            }
        )
        return json_schema


def _remove_discriminator_mapping(obj: Dict) -> Dict:
    """
    Modifies a provided JSON schema object by specifically
    removing the `discriminator.mapping` fields. This alteration aims
    to ensure compatibility with the AJV Validator by addressing and
    resolving schema validation errors that previously led to startup
    failures in applications like `sumo-core`.
    """
    del obj["discriminator"]["mapping"]
    del obj["$defs"]["AnyContent"]["discriminator"]["mapping"]
    return obj


def _remove_format_path(obj: T) -> T:
    """
    Removes entries with key "format" and value "path" from dictionaries. This adjustment
    is necessary because JSON Schema does not recognize the "format": "path", while OpenAPI does.
    This function is used in contexts where OpenAPI specifications are not applicable.
    """

    if isinstance(obj, dict):
        return {
            k: _remove_format_path(v)
            for k, v in obj.items()
            if not (k == "format" and v == "path")
        }

    if isinstance(obj, list):
        return [_remove_format_path(element) for element in obj]

    return obj


def dump() -> Dict:
    # ruff: noqa: E501
    """
    Dumps the export root model to JSON format for schema validation and
    usage in FMU data structures.

    To update the schema:
        1. Run the following CLI command to dump the updated schema:
            `python3 -m fmu.dataio.datastructure.meta > schema/definitions/0.8.0/schema/fmu_meta.json`
        2. Check the diff for changes. Adding fields usually indicates non-breaking
            changes and is generally safe. However, if fields are removed, it could
            indicate breaking changes that may affect dependent systems. Perform a
            quality control (QC) check to ensure these changes do not break existing
            implementations.
            If changes are satisfactory and do not introduce issues, commit
            them to maintain schema consistency.
    """
    schema = dict(
        ChainMap(
            {
                "$contractual": [
                    "access",
                    "class",
                    "data.alias",
                    "data.bbox",
                    "data.content",
                    "data.format",
                    "data.grid_model",
                    "data.is_observation",
                    "data.is_prediction",
                    "data.name",
                    "data.offset",
                    "data.seismic.attribute",
                    "data.spec.columns",
                    "data.stratigraphic",
                    "data.stratigraphic_alias",
                    "data.tagname",
                    "data.time",
                    "data.vertical_domain",
                    "file.checksum_md5",
                    "file.relative_path",
                    "file.size_bytes",
                    "fmu.aggregation.operation",
                    "fmu.aggregation.realization_ids",
                    "fmu.case",
                    "fmu.context.stage",
                    "fmu.iteration.name",
                    "fmu.iteration.uuid",
                    "fmu.model",
                    "fmu.realization.id",
                    "fmu.realization.name",
                    "fmu.realization.uuid",
                    "fmu.workflow",
                    "masterdata",
                    "source",
                    "tracklog.datetime",
                    "tracklog.event",
                    "tracklog.user.id",
                    "version",
                ],
                # schema must be present for "dependencies" key to work.
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "fmu_meta.json",
            },
            Root.model_json_schema(),
        )
    )

    return _remove_format_path(
        _remove_discriminator_mapping(
            schema,
        ),
    )
