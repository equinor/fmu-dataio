"""
Module for ExportConfig which contains the fully resolved export configuration.

This is the interface used internally which has already processed user input and
undergone input validation and transformations.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, Self, TypeAlias

from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.data import (
    FieldOutline,
    FieldRegion,
    FluidContact,
    Property,
)
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    FMUContext,
    VerticalDomain,
)
from fmu.datamodels.fmu_results.fields import Display, Workflow
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from ._export_config_resolver import _resolve_fmu_context, build_from_export_data
from ._logging import null_logger
from ._runcontext import RunContext
from .providers.objectdata._export_models import AllowedContentSeismic

logger: Final = null_logger(__name__)


if TYPE_CHECKING:
    from .dataio import ExportData

AnyContentMetadata: TypeAlias = (
    AllowedContentSeismic | FieldOutline | FieldRegion | FluidContact | Property
)


@dataclass(frozen=True)
class ExportConfig:
    """Immutable configuration for export operations.

    All values are resolved and validated at creation time.
    """

    # Content
    content: Content | Literal["unset"]
    content_metadata: AnyContentMetadata | None

    # File/path configuration
    name: str
    tagname: str
    forcefolder: str
    subfolder: str
    parent: str
    filename_timedata_reverse: bool
    geometry: str | None

    # Domain configuration
    vertical_domain: VerticalDomain
    domain_reference: DomainReference

    # User input strings
    display: Display
    workflow: Workflow | None
    description: list[str] | None

    # Classification/access
    classification: Classification
    rep_include: bool

    # Table configuration
    table_index: list[str] | None
    table_fformat: str
    polygons_fformat: str
    points_fformat: str

    # Time configuration
    timedata: list[str] | list[list[str]] | None

    # Flags
    preprocessed: bool
    is_prediction: bool
    is_observation: bool
    undef_is_zero: bool

    # Other
    unit: str

    # Global configuration
    config: GlobalConfiguration | None

    # Run context
    runcontext: RunContext

    @property
    def content_enum(self) -> Content | None:
        """Filter possible 'unset' content."""
        if isinstance(self.content, Content):
            return self.content
        return None

    @property
    def fmu_context(self) -> FMUContext | None:
        """The FMU context from the run context."""
        return self.runcontext.fmu_context

    @property
    def casepath(self) -> Path | None:
        """The casepath from the run context."""
        return self.runcontext.casepath

    def with_ensemble_name(self, ensemble_name: str) -> Self:
        """Return a new ExportConfig with the ensemble name set explicitly."""
        runcontext = RunContext(
            casepath_proposed=self.runcontext.casepath,
            fmu_context=self.runcontext.fmu_context,
            ensemble_name=ensemble_name,
        )
        return dataclasses.replace(self, runcontext=runcontext)

    def with_polygons_file_format(self, file_format: str) -> Self:
        """Returns a new ExportConfig with the polygons file format set explicitly."""
        return dataclasses.replace(self, polygons_fformat=file_format)

    @classmethod
    def builder(cls) -> ExportConfigBuilder:
        """Create a new builder instance."""
        return ExportConfigBuilder()

    @classmethod
    def from_export_data(cls, dataio: ExportData) -> ExportConfig:
        """Create an ExportConfig from an ExportData instance.

        Args:
            dataio: The ExportData instance to create config from.

        Returns:
            An immutable ExportConfig with all resolved values.
        """

        return build_from_export_data(cls, dataio)


class ExportConfigBuilder:
    """Builder for ExportConfig.

    Accepts already-validated types. For resolution from raw user input, use
    ExportConfig.from_export_data().

    Example:
        config = (
            ExportConfig.builder()
            .content(Content.depth)
            .domain(VerticalDomain.depth, DomainReference.msl)
            .file_config(name="TopVolantis")
            .access(Classification.internal, rep_include=False)
            .global_config(validated_config)
            .build()
        )

        # With explicit run context:
        config = (
            ExportConfig.builder()
            .content(Content.depth, None)
            .global_config(validated_config)
            .run_context(fmu_context=FMUContext.case, casepath=some_path)
            .build()
        )
    """

    def __init__(self) -> None:
        # Content
        self._content: Content | None = None
        self._content_metadata: AnyContentMetadata | None = None

        # File/path
        self._name: str = ""
        self._tagname: str = ""
        self._forcefolder: str = ""
        self._subfolder: str = ""
        self._parent: str = ""
        self._filename_timedata_reverse: bool = False
        self._geometry: str | None = None

        # Domain
        self._vertical_domain: VerticalDomain = VerticalDomain.depth
        self._domain_reference: DomainReference = DomainReference.msl

        # Display/workflow
        self._display: Display = Display(name=None)
        self._workflow: Workflow | None = None
        self._description: list[str] | None = None

        # Classification
        self._classification: Classification = Classification.internal
        self._rep_include: bool = False

        # Table config
        self._table_index: list[str] | None = None
        self._table_fformat: str = "parquet"
        self._polygons_fformat: str = "parquet"
        self._points_fformat: str = "parquet"

        # Time
        self._timedata: list[str] | list[list[str]] | None = None

        # Flags
        self._preprocessed: bool = False
        self._is_prediction: bool = True
        self._is_observation: bool = False
        self._unit: str = ""
        self._undef_is_zero: bool = False

        # Config
        self._config: GlobalConfiguration | None = None

        # Run context
        self._runcontext: RunContext | None = None
        self._casepath: Path | None = None
        self._fmu_context: FMUContext | None = None
        self._ensemble_name: str | None = None
        self._run_context_called: bool = False

    def content(
        self,
        content: Content,
        metadata: AnyContentMetadata | None = None,
    ) -> ExportConfigBuilder:
        """Set content type and metadata."""
        self._content = content
        self._content_metadata = metadata
        return self

    def file_config(
        self,
        name: str = "",
        tagname: str = "",
        forcefolder: str = "",
        subfolder: str = "",
        parent: str = "",
        geometry: str | None = None,
        filename_timedata_reverse: bool = False,
    ) -> ExportConfigBuilder:
        """Set file/path configuration."""
        self._name = name
        self._tagname = tagname
        self._forcefolder = forcefolder
        self._subfolder = subfolder
        self._parent = parent
        self._geometry = geometry
        self._filename_timedata_reverse = filename_timedata_reverse
        return self

    def domain(
        self,
        vertical_domain: VerticalDomain,
        domain_reference: DomainReference,
    ) -> ExportConfigBuilder:
        """Set vertical domain and reference."""
        self._vertical_domain = vertical_domain
        self._domain_reference = domain_reference
        return self

    def display(self, display: Display) -> ExportConfigBuilder:
        """Set display configuration."""
        self._display = display
        return self

    def workflow(self, workflow: Workflow | None) -> ExportConfigBuilder:
        """Set workflow."""
        self._workflow = workflow
        return self

    def description(self, description: list[str] | None) -> ExportConfigBuilder:
        """Set description."""
        self._description = description
        return self

    def access(
        self,
        classification: Classification,
        rep_include: bool,
    ) -> ExportConfigBuilder:
        """Set classification and access."""
        self._classification = classification
        self._rep_include = rep_include
        return self

    def table_config(
        self,
        table_index: list[str] | None = None,
        table_fformat: str = "parquet",
        polygons_fformat: str = "parquet",
        points_fformat: str = "parquet",
    ) -> ExportConfigBuilder:
        """Set table-related configuration."""
        self._table_index = table_index
        self._table_fformat = table_fformat
        self._polygons_fformat = polygons_fformat
        self._points_fformat = points_fformat
        return self

    def timedata(
        self, timedata: list[str] | list[list[str]] | None
    ) -> ExportConfigBuilder:
        """Set time data."""
        self._timedata = timedata
        return self

    def flags(
        self,
        preprocessed: bool = False,
        is_prediction: bool = True,
        is_observation: bool = False,
        undef_is_zero: bool = False,
    ) -> ExportConfigBuilder:
        """Set boolean flags."""
        self._preprocessed = preprocessed
        self._is_prediction = is_prediction
        self._is_observation = is_observation
        self._undef_is_zero = undef_is_zero
        return self

    def unit(self, unit: str) -> ExportConfigBuilder:
        """Set unit."""
        self._unit = unit
        return self

    def global_config(
        self,
        config: GlobalConfiguration | None,
    ) -> ExportConfigBuilder:
        """Set global configuration.

        Args:
            config: The global configuration from the config file.
        """
        self._config = config
        return self

    def run_context(
        self,
        *,
        fmu_context: FMUContext | None = None,
        casepath: Path | None = None,
        ensemble_name: str | None = None,
    ) -> ExportConfigBuilder:
        """Set run context parameters explicitly.

        If this method is not called, the run context will be automatically detected
        from the environment when build() is called.

        Args:
            fmu_context: The FMU context (case, realization, etc.).
            casepath: The path to the case directory.
        """
        self._fmu_context = fmu_context
        self._casepath = casepath
        self._ensemble_name = ensemble_name
        self._run_context_called = True
        return self

    def _build_run_context(self) -> RunContext:
        """Build RunContext.

        Auto-detects from environment if needed."""
        if self._run_context_called:
            return RunContext(
                casepath_proposed=self._casepath,
                fmu_context=self._fmu_context,
                ensemble_name=self._ensemble_name,
            )

        fmu_context, preprocessed = _resolve_fmu_context(
            fmu_context_input=None,
            preprocessed_input=self._preprocessed,
        )

        if preprocessed:
            self._preprocessed = preprocessed

        return RunContext(
            casepath_proposed=None,
            fmu_context=fmu_context,
        )

    def build(self) -> ExportConfig:
        """Build the immutable ExportConfig.

        If run_context() was not called, the run context will be automatically detected
        from the FMU environment.

        Returns:
            Configured ExportConfig instance.

        Raises:
            ValueError: If content is not set.
        """
        if self._content is None:
            raise ValueError("content must be set before building")

        runcontext = self._build_run_context()

        return ExportConfig(
            content=self._content,
            content_metadata=self._content_metadata,
            name=self._name,
            tagname=self._tagname,
            forcefolder=self._forcefolder,
            subfolder=self._subfolder,
            parent=self._parent,
            filename_timedata_reverse=self._filename_timedata_reverse,
            geometry=self._geometry,
            vertical_domain=self._vertical_domain,
            domain_reference=self._domain_reference,
            display=self._display,
            workflow=self._workflow,
            description=self._description,
            classification=self._classification,
            rep_include=self._rep_include,
            table_index=self._table_index,
            table_fformat=self._table_fformat,
            polygons_fformat=self._polygons_fformat,
            points_fformat=self._points_fformat,
            timedata=self._timedata,
            preprocessed=self._preprocessed,
            is_prediction=self._is_prediction,
            is_observation=self._is_observation,
            unit=self._unit,
            undef_is_zero=self._undef_is_zero,
            config=self._config,
            runcontext=runcontext,
        )
