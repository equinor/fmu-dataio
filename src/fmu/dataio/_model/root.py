from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Literal, TypeVar, Union

from pydantic import (
    BaseModel,
    Field,
    GetJsonSchemaHandler,
    RootModel,
    model_validator,
)
from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import Annotated

from .data import AnyData
from .enums import FMUClass
from .fields import (
    FMU,
    Access,
    Display,
    File,
    FMUBase,
    FMUIteration,
    FMURealization,
    Masterdata,
    SsdlAccess,
    Tracklog,
)

if TYPE_CHECKING:
    from typing import Any, Final, Mapping

    from pydantic_core import CoreSchema

T = TypeVar("T", Dict, List, object)


class MetadataBase(BaseModel):
    """Base model for all root metadata models generated."""

    class_: FMUClass = Field(alias="class", title="metadata_class")
    """The class of this metadata object. Functions as the discriminating field."""

    masterdata: Masterdata
    """The ``masterdata`` block contains information related to masterdata.
    See :class:`Masterdata`."""

    tracklog: Tracklog
    """The ``tracklog`` block contains a record of events recorded on these data.
    See :class:`Tracklog`."""

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

    class_: Literal[FMUClass.case] = Field(alias="class", title="metadata_class")
    """The class of this metadata object. In this case, always an FMU case."""

    fmu: FMUBase
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMUBase`."""

    access: Access
    """The ``access`` block contains information related to access control for
    this data object. See :class:`Access`."""


class IterationMetadata(MetadataBase):
    """The FMU metadata model for an FMU Iteration.

    An object representing a single Iteration of a specific case.
    """

    class_: Literal[FMUClass.iteration] = Field(alias="class", title="metadata_class")
    """The class of this metadata object. In this case, always an FMU iteration."""

    fmu: FMUIteration
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMU`."""

    access: Access
    """The ``access`` block contains information related to access control for
    this data object. See :class:`Access`."""


class RealizationMetadata(MetadataBase):
    """The FMU metadata model for an FMU Realization.

    An object representing a single Realization of a specific Iteration.
    """

    class_: Literal[FMUClass.realization] = Field(alias="class", title="metadata_class")
    """The class of this metadata object. In this case, always an FMU realization."""

    fmu: FMURealization
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMU`."""

    access: Access
    """The ``access`` block contains information related to access control for
    this data object. See :class:`Access`."""


class ObjectMetadata(MetadataBase):
    """The FMU metadata model for a given data object."""

    class_: Literal[
        FMUClass.surface,
        FMUClass.table,
        FMUClass.cpgrid,
        FMUClass.cpgrid_property,
        FMUClass.polygons,
        FMUClass.cube,
        FMUClass.well,
        FMUClass.points,
        FMUClass.dictionary,
    ] = Field(
        alias="class",
        title="metadata_class",
    )
    """The class of the data object being exported and described by the metadata
    contained herein."""

    fmu: FMU
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMU`."""

    access: SsdlAccess
    """The ``access`` block contains information related to access control for
    this data object. See :class:`SsdlAccess`."""

    data: AnyData
    """The ``data`` block contains information about the data contained in this
    object. See :class:`data.AnyData`."""

    file: File
    """ The ``file`` block contains references to this data object as a file on a disk.
    See :class:`File`."""

    display: Display
    """ The ``display`` block contains information related to how this data object
    should/could be displayed. See :class:`Display`."""


class Root(
    RootModel[
        Annotated[
            Union[
                CaseMetadata,
                ObjectMetadata,
                RealizationMetadata,
                IterationMetadata,
            ],
            Field(discriminator="class_"),
        ]
    ]
):
    @model_validator(mode="after")
    def _check_class_data_spec(self) -> Root:
        if (
            self.root.class_ in (FMUClass.table, FMUClass.surface)
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
    ) -> dict[str, object]:
        json_schema = super().__get_pydantic_json_schema__(core_schema, handler)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.update(
            {
                "if": {"properties": {"class": {"enum": ["table", "surface"]}}},
                "then": {"properties": {"data": {"required": ["spec"]}}},
            }
        )
        return json_schema


class FmuResultsJsonSchema(GenerateJsonSchema):
    contractual: Final[list[str]] = [
        "access",
        "class",
        "data.alias",
        "data.bbox",
        "data.content",
        "data.format",
        "data.geometry",
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
        "fmu.realization.is_reference",
        "fmu.realization.name",
        "fmu.realization.uuid",
        "fmu.workflow",
        "masterdata",
        "source",
        "tracklog.datetime",
        "tracklog.event",
        "tracklog.user.id",
        "version",
    ]

    def _remove_format_path(self, obj: T) -> T:
        """
        Removes entries with key "format" and value "path" from dictionaries. This
        adjustment is necessary because JSON Schema does not recognize the "format":
        "path", while OpenAPI does. This function is used in contexts where OpenAPI
        specifications are not applicable.
        """

        if isinstance(obj, dict):
            return {
                k: self._remove_format_path(v)
                for k, v in obj.items()
                if not (k == "format" and v == "path")
            }

        if isinstance(obj, list):
            return [self._remove_format_path(element) for element in obj]

        return obj

    def generate(
        self,
        schema: Mapping[str, Any],
        mode: Literal["validation", "serialization"] = "validation",
    ) -> dict[str, Any]:
        json_schema = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        json_schema["$id"] = "fmu_results.json"
        json_schema["$contractual"] = self.contractual

        # sumo-core's validator does not recognize these.
        del json_schema["discriminator"]["mapping"]
        del json_schema["$defs"]["AnyData"]["discriminator"]["mapping"]

        return self._remove_format_path(json_schema)


def dump() -> dict:
    """
    Dumps the export root model to JSON format for schema validation and
    usage in FMU data structures.

    To update the schema:
        1. Run the following CLI command to dump the updated schema:
            `./tools/update_schema`
        2. Check the diff for changes. Adding fields usually indicates non-breaking
            changes and is generally safe. However, if fields are removed, it could
            indicate breaking changes that may affect dependent systems. Perform a
            quality control (QC) check to ensure these changes do not break existing
            implementations.
            If changes are satisfactory and do not introduce issues, commit
            them to maintain schema consistency.
    """
    return Root.model_json_schema(schema_generator=FmuResultsJsonSchema)
