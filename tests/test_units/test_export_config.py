"""Tests for ExportConfigBuilder."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.data import Property
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    FMUContext,
    VerticalDomain,
)
from fmu.datamodels.fmu_results.fields import Display, Workflow
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.datamodels.fmu_results.standard_result import (
    AnyStandardResult,
    InplaceVolumesStandardResult,
)
from fmu.datamodels.standard_results.enums import StandardResultName

from fmu.dataio._export_config import ExportConfig, ExportConfigBuilder


@pytest.fixture
def mock_resolve_fmu_context() -> Generator[MagicMock]:
    """Avoid environment detection."""
    with patch("fmu.dataio._export_config._resolve_fmu_context") as mock:
        mock.return_value = (None, False)
        yield mock


@pytest.fixture
def minimal_builder(mock_resolve_fmu_context: MagicMock) -> ExportConfigBuilder:
    """Builder with minimum required configuration."""
    return ExportConfig.builder().content(Content.depth, None)


def test_builder_returns_builder_instance() -> None:
    """ExportConfig.builder() returns an ExportConfigBuilder."""
    builder = ExportConfig.builder()
    assert isinstance(builder, ExportConfigBuilder)


def test_builder_build_requires_content(mock_resolve_fmu_context: MagicMock) -> None:
    """Building without content raises ValueError."""
    builder = ExportConfig.builder()
    with pytest.raises(ValueError, match="content must be set"):
        builder.build()


def test_builder_build_auto_detects_run_context(
    mock_resolve_fmu_context: MagicMock,
) -> None:
    """Building without run_context() auto-detects from environment."""
    config = ExportConfig.builder().content(Content.depth, None).build()

    assert isinstance(config, ExportConfig)
    mock_resolve_fmu_context.assert_called_once()


def test_builder_build_with_explicit_run_context(
    mock_resolve_fmu_context: MagicMock,
) -> None:
    """Building with explicit run_context() skips auto-detection."""
    config = (
        ExportConfig.builder()
        .content(Content.depth, None)
        .run_context(fmu_context=FMUContext.case)
        .build()
    )

    assert isinstance(config, ExportConfig)
    assert config.fmu_context == FMUContext.case
    mock_resolve_fmu_context.assert_not_called()


def test_builder_build_returns_export_config(
    mock_resolve_fmu_context: MagicMock,
) -> None:
    """Building with required fields returns ExportConfig."""
    config = ExportConfig.builder().content(Content.depth, None).build()
    assert isinstance(config, ExportConfig)


def test_builder_methods_return_self(mock_resolve_fmu_context: MagicMock) -> None:
    """All builder methods return self for chaining."""
    builder = ExportConfig.builder()

    assert builder.content(Content.depth, None) is builder
    assert builder.file_config(name="test") is builder
    assert builder.domain(VerticalDomain.depth, DomainReference.msl) is builder
    assert builder.display(Display(name=None)) is builder
    assert builder.workflow(None) is builder
    assert builder.description(None) is builder
    assert builder.access(Classification.internal, False) is builder
    assert builder.table_config() is builder
    assert builder.timedata(None) is builder
    assert builder.flags() is builder
    assert builder.unit("m") is builder
    assert builder.global_config(None) is builder
    assert builder.run_context() is builder
    assert builder.standard_result(StandardResultName.inplace_volumes) is builder


def test_builder_content(minimal_builder: ExportConfigBuilder) -> None:
    """Content and metadata are set correctly."""
    config = minimal_builder.content(Content.depth).build()
    assert config.content == Content.depth
    assert config.content_metadata is None


def test_builder_content_with_metadata(mock_resolve_fmu_context: MagicMock) -> None:
    """Content with metadata is set correctly."""

    metadata = Property(attribute="porosity", is_discrete=False)
    config = ExportConfig.builder().content(Content.property, metadata).build()
    assert config.content == Content.property
    assert config.content_metadata == metadata
    assert isinstance(config.content_metadata, Property)
    assert config.content_metadata.attribute == "porosity"
    assert config.content_metadata.is_discrete is False


def test_builder_file_config(minimal_builder: ExportConfigBuilder) -> None:
    """File configuration fields are set correctly."""
    config = minimal_builder.file_config(
        name="myname",
        tagname="mytag",
        forcefolder="forced",
        subfolder="sub",
        parent="parent_grid",
        geometry="/path/to/geom",
        filename_timedata_reverse=True,
    ).build()
    assert config.name == "myname"
    assert config.tagname == "mytag"
    assert config.forcefolder == "forced"
    assert config.subfolder == "sub"
    assert config.parent == "parent_grid"
    assert config.geometry == "/path/to/geom"
    assert config.filename_timedata_reverse is True


def test_builder_file_config_defaults(minimal_builder: ExportConfigBuilder) -> None:
    """File configuration has sensible defaults."""
    config = minimal_builder.build()
    assert config.name == ""
    assert config.tagname == ""
    assert config.forcefolder == ""
    assert config.subfolder == ""
    assert config.parent == ""
    assert config.geometry is None
    assert config.filename_timedata_reverse is False


def test_builder_domain(minimal_builder: ExportConfigBuilder) -> None:
    """Domain configuration is set correctly."""
    config = minimal_builder.domain(VerticalDomain.time, DomainReference.rkb).build()
    assert config.vertical_domain == VerticalDomain.time
    assert config.domain_reference == DomainReference.rkb


def test_builder_domain_defaults(minimal_builder: ExportConfigBuilder) -> None:
    """Domain configuration has same defaults."""
    config = minimal_builder.build()
    assert config.vertical_domain == VerticalDomain.depth
    assert config.domain_reference == DomainReference.msl


def test_builder_display(minimal_builder: ExportConfigBuilder) -> None:
    """Display is set correctly."""
    display = Display(name="My Display Name")
    config = minimal_builder.display(display).build()
    assert config.display == display
    assert config.display.name == "My Display Name"


def test_builder_workflow(minimal_builder: ExportConfigBuilder) -> None:
    """Workflow is set correctly."""
    workflow = Workflow(reference="my workflow")
    config = minimal_builder.workflow(workflow).build()
    assert config.workflow == workflow


def test_builder_workflow_none(minimal_builder: ExportConfigBuilder) -> None:
    """Workflow can be None."""
    config = minimal_builder.workflow(None).build()
    assert config.workflow is None


def test_builder_description(minimal_builder: ExportConfigBuilder) -> None:
    """Description is set correctly."""
    config = minimal_builder.description(["Line 1", "Line 2"]).build()
    assert config.description == ["Line 1", "Line 2"]


def test_builder_access(minimal_builder: ExportConfigBuilder) -> None:
    """Access configuration is set correctly."""
    config = minimal_builder.access(Classification.restricted, rep_include=True).build()
    assert config.classification == Classification.restricted
    assert config.rep_include is True


def test_builder_access_defaults(minimal_builder: ExportConfigBuilder) -> None:
    """Access configuration has sensible defaults."""
    config = minimal_builder.build()
    assert config.classification == Classification.internal
    assert config.rep_include is False


def test_builder_table_config(minimal_builder: ExportConfigBuilder) -> None:
    """Table configuration is set correctly."""
    config = minimal_builder.table_config(
        table_index=["ZONE", "REGION"],
        table_fformat="parquet",
        polygons_fformat="csv|xtgeo",
        points_fformat="csv|xtgeo",
    ).build()
    assert config.table_index == ["ZONE", "REGION"]
    assert config.table_fformat == "parquet"
    assert config.polygons_fformat == "csv|xtgeo"
    assert config.points_fformat == "csv|xtgeo"


def test_builder_table_config_defaults(minimal_builder: ExportConfigBuilder) -> None:
    """Table configuration has sensible defaults."""
    config = minimal_builder.build()
    assert config.table_index is None
    assert config.table_fformat == "parquet"
    assert config.polygons_fformat == "parquet"
    assert config.points_fformat == "parquet"


def test_builder_timedata(minimal_builder: ExportConfigBuilder) -> None:
    """Timedata is set correctly."""
    config = minimal_builder.timedata(["20200101", "20210101"]).build()
    assert config.timedata == ["20200101", "20210101"]


def test_builder_timedata_with_labels(minimal_builder: ExportConfigBuilder) -> None:
    """Timedata with labels is set correctly."""
    timedata = [["20200101", "monitor"], ["20180101", "base"]]
    config = minimal_builder.timedata(timedata).build()
    assert config.timedata == timedata


def test_builder_flags(minimal_builder: ExportConfigBuilder) -> None:
    """Boolean flags are set correctly."""
    config = minimal_builder.flags(
        preprocessed=True,
        is_prediction=False,
        is_observation=True,
        undef_is_zero=True,
    ).build()
    assert config.preprocessed is True
    assert config.is_prediction is False
    assert config.is_observation is True
    assert config.undef_is_zero is True


def test_builder_flags_defaults(minimal_builder: ExportConfigBuilder) -> None:
    """Boolean flags have sensible defaults."""
    config = minimal_builder.build()
    assert config.preprocessed is False
    assert config.is_prediction is True
    assert config.is_observation is False
    assert config.undef_is_zero is False


def test_builder_unit(minimal_builder: ExportConfigBuilder) -> None:
    """Unit is set correctly."""
    config = minimal_builder.unit("m").build()
    assert config.unit == "m"


def test_builder_unit_default(minimal_builder: ExportConfigBuilder) -> None:
    """Unit defaults to empty string."""
    config = minimal_builder.build()
    assert config.unit == ""


def test_builder_global_config_with_config(
    mock_resolve_fmu_context: MagicMock,
) -> None:
    """GlobalConfiguration is stored correctly."""
    mock_config = MagicMock(spec=GlobalConfiguration)
    config = (
        ExportConfig.builder().content(Content.depth).global_config(mock_config).build()
    )
    assert config.config is mock_config


def test_builder_global_config_none(mock_resolve_fmu_context: MagicMock) -> None:
    """Config can be None."""
    config = ExportConfig.builder().content(Content.depth).global_config(None).build()
    assert config.config is None


def test_builder_run_context_explicit() -> None:
    """Explicit run_context() passes values to RunContext correctly."""
    casepath = Path("/my/case")

    with patch("fmu.dataio._export_config.RunContext") as mock_runcontext_cls:
        mock_runcontext = MagicMock()
        mock_runcontext.fmu_context = FMUContext.realization
        mock_runcontext.casepath = casepath
        mock_runcontext_cls.return_value = mock_runcontext

        config = (
            ExportConfig.builder()
            .content(Content.depth)
            .run_context(
                fmu_context=FMUContext.realization,
                casepath=casepath,
                ensemble_name="foo",
            )
            .build()
        )

        mock_runcontext_cls.assert_called_once_with(
            casepath_proposed=casepath,
            fmu_context=FMUContext.realization,
            ensemble_name="foo",
        )
        assert config.fmu_context == FMUContext.realization
        assert config.casepath == casepath


def test_builder_run_context_partial(mock_resolve_fmu_context: MagicMock) -> None:
    """run_context() with partial values uses defaults for others."""
    config = (
        ExportConfig.builder()
        .content(Content.depth)
        .run_context(fmu_context=FMUContext.case)
        .build()
    )
    assert config.fmu_context == FMUContext.case
    assert config.casepath is None
    assert config.preprocessed is False


def test_builder_run_context_with_flags_preprocessed(
    mock_resolve_fmu_context: MagicMock,
) -> None:
    """run_context() does not interfere with flags(preprocessed=True)."""
    config = (
        ExportConfig.builder()
        .content(Content.depth)
        .flags(preprocessed=True)
        .run_context(fmu_context=FMUContext.case)
        .build()
    )
    assert config.preprocessed is True
    assert config.fmu_context == FMUContext.case


def test_builder_chaining(mock_resolve_fmu_context: MagicMock) -> None:
    """Full builder chain produces correct config."""
    config = (
        ExportConfig.builder()
        .content(Content.seismic)
        .file_config(name="seismic_data", tagname="amplitude")
        .domain(VerticalDomain.time, DomainReference.msl)
        .access(Classification.restricted, rep_include=True)
        .flags(is_observation=True, is_prediction=False)
        .unit("ms")
        .global_config(None)
        .build()
    )

    assert config.content == Content.seismic
    assert config.name == "seismic_data"
    assert config.tagname == "amplitude"
    assert config.vertical_domain == VerticalDomain.time
    assert config.classification == Classification.restricted
    assert config.rep_include is True
    assert config.is_observation is True
    assert config.is_prediction is False
    assert config.unit == "ms"


def test_builder_override_previous_values(mock_resolve_fmu_context: MagicMock) -> None:
    """Later calls override earlier values."""
    config = (
        ExportConfig.builder()
        .content(Content.depth)
        .content(Content.time)
        .unit("m")
        .unit("s")
        .build()
    )

    assert config.content == Content.time
    assert config.unit == "s"


def test_builder_run_context_override(mock_resolve_fmu_context: MagicMock) -> None:
    """Later run_context() calls override earlier values."""
    config = (
        ExportConfig.builder()
        .content(Content.depth)
        .run_context(fmu_context=FMUContext.case)
        .run_context(fmu_context=FMUContext.realization)
        .build()
    )
    assert config.fmu_context == FMUContext.realization


def test_builder_run_context_ensemble(mock_resolve_fmu_context: MagicMock) -> None:
    """run_context() with FMUContext.ensemble works correctly."""
    config = (
        ExportConfig.builder()
        .content(Content.depth)
        .run_context(fmu_context=FMUContext.ensemble)
        .build()
    )
    assert config.fmu_context == FMUContext.ensemble


def test_builder_run_context_ensemble_export_root(
    fmurun_w_casemetadata: Path,
) -> None:
    """run_context() with FMUContext.ensemble sets correct export root."""
    config = (
        ExportConfig.builder()
        .content(Content.depth, None)
        .run_context(fmu_context=FMUContext.ensemble)
        .build()
    )

    assert config.fmu_context == FMUContext.ensemble
    assert config.runcontext.exportroot == config.runcontext.ensemble_path


def test_builder_standard_result(minimal_builder: ExportConfigBuilder) -> None:
    """Standard result is set correctly from name."""
    config = minimal_builder.standard_result(StandardResultName.inplace_volumes).build()
    assert config.standard_result is not None
    assert config.standard_result.root.name == StandardResultName.inplace_volumes
    assert isinstance(config.standard_result.root, InplaceVolumesStandardResult)


def test_builder_standard_result_none_default(
    minimal_builder: ExportConfigBuilder,
) -> None:
    """Standard result defaults to None."""
    config = minimal_builder.build()
    assert config.standard_result is None


@pytest.mark.parametrize("name", list(StandardResultName))
def test_builder_standard_result_all_name(
    minimal_builder: ExportConfigBuilder, name: StandardResultName
) -> None:
    """Every StandardResultName resolves to a valid AnyStandardResult."""
    config = minimal_builder.standard_result(name).build()
    assert config.standard_result is not None
    assert config.standard_result.root.name == name
    assert isinstance(config.standard_result, AnyStandardResult)
