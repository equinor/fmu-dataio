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

    access_level: enums.Classification
    rep_include: bool


class Access(BaseModel):
    asset: Asset
    classification: Optional[enums.Classification] = Field(default=None)


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


class Case(BaseModel):
    """The ``fmu.case`` block contains information about the case from which this data
    object was exported.

    A case represent a set of iterations that belong together, either by being part of
    the same run (i.e. history matching) or by being placed together by the user,
    corresponding to /scratch/<asset>/<user>/<my case name>/.

    .. note:: If an FMU data object is exported outside the case context, this block
       will not be present.
    """

    name: str = Field(examples=["MyCaseName"])
    """The name of the case."""

    user: User
    """A block holding information about the user.
    See :class:`User`."""

    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])
    """The unique identifier of this case. Currently made by fmu.dataio."""

    description: Optional[List[str]] = Field(default=None)
    """A free-text description of this case."""


class Iteration(BaseModel):
    """The ``fmu.iteration`` block contains information about the iteration this data
    object belongs to."""

    id: Optional[int] = Field(default=None)
    """The internal identification of this iteration, typically represented by an
    integer."""

    name: str = Field(examples=["iter-0"])
    """The name of the iteration. This is typically reflecting the folder name on
    scratch. In ERT, custom names for iterations are supported, e.g. "pred"."""

    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])
    """The unique identifier of this case. Currently made by fmu.dataio."""

    restart_from: Optional[UUID] = Field(
        default=None,
        examples=["15ce3b84-766f-4c93-9050-b154861f9100"],
    )
    """A uuid reference to another iteration that this iteration was restarted
    from"""


class Model(BaseModel):
    """The ``fmu.model`` block contains information about the model used.

    .. note::
       Synonyms for "model" in this context are "template", "setup", etc. The term
       "model" is ultra-generic but was chosen before e.g. "template" as the latter
       deviates from daily communications and is, if possible, even more generic
       than "model".
    """

    description: Optional[List[str]] = Field(default=None)
    """This is a free text description of the model setup"""

    name: str = Field(examples=["Drogon"])
    """The name of the model."""

    revision: str = Field(examples=["21.0.0.dev"])
    """The revision of the model."""


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
    """The ``fmu.realization`` block contains information about the realization this
    data object belongs to."""

    id: int
    """The internal ID of the realization, typically represented by an integer."""

    name: str = Field(examples=["iter-0"])
    """The name of the realization. This is typically reflecting the folder name on
    scratch. We recommend to use ``fmu.realization.id`` for all usage except purely
    visual appearance."""

    parameters: Optional[Parameters] = Field(default=None)
    """These are the parameters used in this realization. It is a direct pass of
    ``parameters.txt`` and will contain key:value pairs representing the design
    parameters. See :class:`Parameters`."""

    jobs: Optional[object] = Field(default=None)
    """Content directly taken from the ERT jobs.json file for this realization."""

    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])
    """The universally unique identifier for this realization. It is a hash of
    ``fmu.case.uuid`` and ``fmu.iteration.uuid`` and ``fmu.realization.id``."""


class CountryItem(BaseModel):
    """Reference to a country known to SMDA."""

    identifier: str = Field(examples=["Norway"])
    """Identifier known to SMDA."""

    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])
    """Identifier known to SMDA."""


class DiscoveryItem(BaseModel):
    """Reference to a discovery known to SMDA."""

    short_identifier: str = Field(examples=["SomeDiscovery"])
    """Identifier known to SMDA."""

    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])
    """Identifier known to SMDA."""


class FieldItem(BaseModel):
    """Reference to a field known to SMDA."""

    identifier: str = Field(examples=["OseFax"])
    """Identifier known to SMDA."""

    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])
    """Identifier known to SMDA."""


class CoordinateSystem(BaseModel):
    """Reference to coordinate system known to SMDA."""

    identifier: str = Field(examples=["ST_WGS84_UTM37N_P32637"])
    """Identifier known to SMDA."""

    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])
    """Identifier known to SMDA."""


class StratigraphicColumn(BaseModel):
    """Reference to stratigraphic column known to SMDA."""

    identifier: str = Field(examples=["DROGON_2020"])
    """Identifier known to SMDA."""

    uuid: UUID = Field(examples=["15ce3b84-766f-4c93-9050-b154861f9100"])
    """Identifier known to SMDA."""


class Smda(BaseModel):
    """Block containing SMDA-related attributes."""

    coordinate_system: CoordinateSystem
    """Reference to coordinate system known to SMDA.
    See :class:`CoordinateSystem`."""

    country: List[CountryItem]
    """A list referring to countries known to SMDA. First item is primary.
    See :class:`CountryItem`."""

    discovery: List[DiscoveryItem]
    """A list referring to discoveries known to SMDA. First item is primary.
    See :class:`DiscoveryItem`."""

    field: List[FieldItem]
    """A list referring to fields known to SMDA. First item is primary.
    See :class:`FieldItem`."""

    stratigraphic_column: StratigraphicColumn
    """Reference to stratigraphic column known to SMDA.
    See :class:`StratigraphicColumn`."""


class Masterdata(BaseModel):
    """The ``masterdata`` block contains information related to masterdata.
    Currently, smda holds the masterdata.
    """

    smda: Smda
    """Block containing SMDA-related attributes.
    See :class:`Smda`."""


class VersionInformation(BaseModel):
    version: str


class SystemInformationOperatingSystem(BaseModel):
    """
    This model encapsulates various pieces of system-related information using Python's
    platform module. It provides a structured way to access details about the system's
    hardware, operating system, and interpreter version information.
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
    """The ``tracklog`` block contains a record of events recorded on these data.
    This data object describes a tracklog event.
    """

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

    stage: enums.FmuContext


class FMUCaseAttributes(BaseModel):
    """
    The ``fmu`` block contains all attributes specific to FMU. The idea is that the FMU
    results data model can be applied to data from *other* sources - in which the
    fmu-specific stuff may not make sense or be applicable.
    """

    case: Case
    model: Model


class FMUAttributes(FMUCaseAttributes):
    """
    The ``fmu`` block contains all attributes specific to FMU. The idea is that the FMU
    results data model can be applied to data from *other* sources - in which the
    fmu-specific stuff may not make sense or be applicable.
    """

    context: Context
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


class MetadataBase(BaseModel):
    """Base model for all root metadata models generated."""

    class_: enums.FMUClassEnum = Field(
        alias="class",
        title="metadata_class",
    )

    masterdata: Masterdata
    """The ``masterdata`` block contains information related to masterdata.
    See :class:`Masterdata`."""

    tracklog: List[TracklogEvent]
    """The ``tracklog`` block contains a record of events recorded on these data.
    See :class:`TracklogEvent`."""

    source: Literal["fmu"]
    """The source of this data. Defaults to 'fmu'."""

    version: Literal["0.8.0"]
    """The version of the schema that generated this data."""


class CaseMetadata(MetadataBase):
    """The FMU metadata model for an FMU case.

    A case represent a set of iterations that belong together, either by being part of
    the same run (i.e. history matching) or by being placed together by the user,
    corresponding to /scratch/<asset>/<user>/<my case name>/.
    """

    class_: Literal[enums.FMUClassEnum.case] = Field(
        alias="class",
        title="metadata_class",
    )

    fmu: FMUCaseAttributes
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMUCaseAttributes`."""

    access: Access


class ObjectMetadata(MetadataBase):
    """The FMU metadata model for a given data object."""

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
        title="metadata_class",
    )

    fmu: FMUAttributes
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMUAttributes`."""

    access: SsdlAccess
    data: content.AnyContent
    file: File
    display: Display


class Root(
    RootModel[
        Annotated[
            Union[
                CaseMetadata,
                ObjectMetadata,
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
    Removes entries with key "format" and value "path" from dictionaries. This
    adjustment is necessary because JSON Schema does not recognize the "format":
    "path", while OpenAPI does. This function is used in contexts where OpenAPI
    specifications are not applicable.
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
    """  # noqa: E501
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
