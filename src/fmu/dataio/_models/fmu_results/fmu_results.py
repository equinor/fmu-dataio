from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    GetJsonSchemaHandler,
    RootModel,
    model_validator,
)

from fmu.dataio._models._schema_base import (
    FmuSchemas,
    GenerateJsonSchemaBase,
    SchemaBase,
)
from fmu.dataio.types import VersionStr

from .data import AnyData
from .enums import FMUResultsMetadataClass, MetadataClass, ObjectMetadataClass
from .fields import (
    FMU,
    Access,
    Display,
    File,
    FMUBase,
    FMUEnsemble,
    FMUIteration,
    FMURealization,
    Masterdata,
    SsdlAccess,
    Tracklog,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Final

    from pydantic_core import CoreSchema


class FmuResultsSchema(SchemaBase):
    """The main metadata export describing the results."""

    VERSION: VersionStr = "0.12.0"

    VERSION_CHANGELOG: str = """
    #### 0.12.0

    - `fmu.ert.simulation_mode` now supports `ensemble_information_filter`

    #### 0.11.0

    - `data.standard_result` now supports `FluidContactSurfaceStandardResult`
    - `fmu.entity.uuid` added as optional field
    - `file.runpath_relative_path` added as optional field
    - `fmu.ert.experiment.id` is added as contractual field
    - improved validation of grid numbering
    - improved validation of grid increments
    - `fmu.ert.simulation_mode` no longer supports `iterative_ensemble_smoother`
    - added `TSurf` to list of supported file formats
    - `data.standard_result` now supports `StructureTimeSurfaceStandardResult`

    #### 0.10.0

    - `triangulated_surface` added as a new object class
    - `Ensemble` objects with `class=ensemble` is now supported, and will
      in the future replace `Iteration` objects
    - `fmu.context.stage` now supports option `ensemble`
    - `$contractual.fmu.ensemble.uuid` and `$contractual.fmu.ensemble.name` added
    - `fmu.ensemble` added as duplicate and future replacement of `fmu.iteration`
    - `data.property` added as optional field for data of content `property`
    - `data.property.attribute` added as optional field.
    - `data.property.is_discrete` added as optional field.
    - `data.standard_result` now supports `StructureDepthIsochoreStandardResult`
    - `data.standard_result` now supports `StructureDepthFaultLinesStandardResult`
    - `data.spec.columns` added as optional field for points, polygons
    - `data.spec.num_columns` added as optional field for points, polygons
    - `data.spec.num_rows` added as optional field for points, polygons
    - `data.spec.size` added as optional field for polygons

    #### 0.9.0

    This is the first versioned update to the schema and contains numerous changes.

    - `$contractual.stratigraphic_alias` has been removed. It was never used.
    - `data.product`: renamed to `data.standard_result`
    - `data.spec.nrow` must be greater or equal to 0 for cubes, surfaces
    - `data.spec.ncol` must be greater or equal to 0 for cubes, surfaces
    - `data.spec.nlay` must be greater or equal to 0 for cubes
    - `data.spec.xinc` must be greater or equal to 0 for cubes, surfaces
    - `data.spec.yinc` must be greater or equal to 0 for cubes, surfaces
    - `data.spec.zinc` must be greater or equal to 0 for cubes
    - `data.spec.npolys` must be greater or equal to 0 for polygons
    - `data.spec.num_columns` is no longer optional and must be greater or equal
      to 0 for tables
    - `data.spec.num_rows` is no longer optional and must be greater or equal to
      0 for tables
    - `data.spec.size` must be greater or equal 0 for tables, points
    - `data.time.t0` is no longer optional
    - `data.time.t0.value` is no longer optional
    - `data.time.t1.value` is no longer optional (`data.time.t1` remains optional)
    - `data.stratigraphic_alias` has been removed
    - `file.absolute_path_symlink` has been removed
    - `file.relative_path_symlink` has been removed
    - `fmu.aggregation.parameters` has been removed
    - `fmu.ert.experiment` is no longer optional
    - `fmu.ert.experiment.id` is no longer optional
    - `fmu.ert.simulation_mode` is no longer optional
    - `fmu.iteration.id` is no longer optional and must be greater or equal to 0
    - `fmu.realization.id` must be greater or equal to 0
    - `fmu.realization.parameters` has been removed
    - `fmu.realization.jobs` has been removed

    #### 0.8.0

    This is the initial schema version.
    """

    FILENAME: str = "fmu_results.json"
    PATH: Path = FmuSchemas.PATH / VERSION / FILENAME

    SOURCE: str = "fmu"
    CONTRACTUAL: Final[list[str]] = [
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
        "data.standard_result.name",
        "data.stratigraphic",
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
        "fmu.entity.uuid",
        "fmu.ensemble.name",
        "fmu.ensemble.uuid",
        "fmu.ert.experiment.id",
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

    class FmuResultsGenerateJsonSchema(GenerateJsonSchemaBase):
        def generate(
            self,
            schema: Mapping[str, Any],
            mode: Literal["validation", "serialization"] = "validation",
        ) -> dict[str, Any]:
            json_schema = super().generate(schema, mode=mode)

            json_schema["$id"] = FmuResultsSchema.url()
            json_schema["$contractual"] = FmuResultsSchema.CONTRACTUAL

            return json_schema

    @classmethod
    def dump(cls) -> dict[str, Any]:
        return FmuResults.model_json_schema(
            schema_generator=cls.FmuResultsGenerateJsonSchema
        )


class MetadataBase(BaseModel):
    """Base model for all root metadata models generated."""

    class_: MetadataClass = Field(alias="class", title="metadata_class")
    """The class of this metadata object. Functions as the discriminating field."""

    masterdata: Masterdata
    """The ``masterdata`` block contains information related to masterdata.
    See :class:`Masterdata`."""

    tracklog: Tracklog
    """The ``tracklog`` block contains a record of events recorded on these data.
    See :class:`Tracklog`."""

    source: str = Field(default=FmuResultsSchema.SOURCE)
    """The source of this data. Defaults to 'fmu'."""

    version: VersionStr = Field(default=FmuResultsSchema.VERSION)
    """The version of the schema that generated this data."""

    schema_: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl(FmuResultsSchema.url()),
        alias="$schema",
    )
    """The url of the schema that generated this data."""


class CaseMetadata(MetadataBase, populate_by_name=True):
    """The FMU metadata model for an FMU case.

    A case represent a set of iterations that belong together, either by being part of
    the same run (i.e. history matching) or by being placed together by the user,
    corresponding to /scratch/<asset>/<user>/<my case name>/.
    """

    class_: Literal[FMUResultsMetadataClass.case] = Field(
        alias="class", title="metadata_class"
    )
    """The class of this metadata object. In this case, always an FMU case."""

    fmu: FMUBase
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMUBase`."""

    access: Access
    """The ``access`` block contains information related to access control for
    this data object. See :class:`Access`."""


class IterationMetadata(MetadataBase):
    """Deprecated and replaced by :class:`EnsembleMetadata`."""

    class_: Literal[FMUResultsMetadataClass.iteration] = Field(
        alias="class", title="metadata_class"
    )
    """The class of this metadata object. In this case, always an FMU iteration."""

    fmu: FMUIteration
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMU`."""

    access: Access
    """The ``access`` block contains information related to access control for
    this data object. See :class:`Access`."""


class EnsembleMetadata(MetadataBase):
    """The FMU metadata model for an FMU ensemble.

    An object representing a single Ensemble of a specific case.
    """

    class_: Literal[FMUResultsMetadataClass.ensemble] = Field(
        alias="class", title="metadata_class"
    )
    """The class of this metadata object. In this case, always an FMU ensemble."""

    fmu: FMUEnsemble
    """The ``fmu`` block contains all attributes specific to FMU.
    See :class:`FMU`."""

    access: Access
    """The ``access`` block contains information related to access control for
    this data object. See :class:`Access`."""


class RealizationMetadata(MetadataBase):
    """The FMU metadata model for an FMU Realization.

    An object representing a single Realization of a specific Ensemble.
    """

    class_: Literal[FMUResultsMetadataClass.realization] = Field(
        alias="class", title="metadata_class"
    )
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
        ObjectMetadataClass.surface,
        ObjectMetadataClass.triangulated_surface,
        ObjectMetadataClass.table,
        ObjectMetadataClass.cpgrid,
        ObjectMetadataClass.cpgrid_property,
        ObjectMetadataClass.polygons,
        ObjectMetadataClass.cube,
        ObjectMetadataClass.well,
        ObjectMetadataClass.points,
        ObjectMetadataClass.dictionary,
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


class FmuResults(
    RootModel[
        Annotated[
            CaseMetadata
            | ObjectMetadata
            | RealizationMetadata
            | IterationMetadata
            | EnsembleMetadata,
            Field(discriminator="class_"),
        ]
    ]
):
    @model_validator(mode="after")
    def _check_class_data_spec(self) -> FmuResults:
        if (
            self.root.class_ in (ObjectMetadataClass.table, ObjectMetadataClass.surface)
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
