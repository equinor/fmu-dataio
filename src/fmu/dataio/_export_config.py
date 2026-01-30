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

from ._export_config_resolver import build_from_export_data  # Avoid circular import
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

    # Other
    preprocessed: bool
    is_prediction: bool
    is_observation: bool
    unit: str
    undef_is_zero: bool

    # Global configuration
    config: GlobalConfiguration | None
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
    def from_export_data(cls, dataio: ExportData) -> ExportConfig:
        """Create an ExportConfig from an ExportData instance.

        Args:
            dataio: The ExportData instance to create config from.

        Returns:
            An immutable ExportConfig with all resolved values.
        """

        return build_from_export_data(cls, dataio)
