"""Tests for ExportConfig and its resolution/validation functions."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fmu.datamodels.common.enums import Classification
from fmu.datamodels.fmu_results.data import (
    Property,
)
from fmu.datamodels.fmu_results.enums import (
    Content,
    DomainReference,
    VerticalDomain,
)
from fmu.datamodels.fmu_results.fields import Workflow
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration

from fmu.dataio._export_config import (
    AnyContentMetadata,
    ExportConfig,
    _content_requires_metadata,
    _resolve_classification,
    _resolve_content_enum,
    _resolve_content_metadata,
    _resolve_description,
    _resolve_global_config,
    _resolve_rep_include,
    _resolve_vertical_domain,
    _resolve_workflow,
)
from fmu.dataio.providers.objectdata._export_models import AllowedContentSeismic


@pytest.fixture
def mock_config_internal() -> GlobalConfiguration:
    """Mock internal classification."""
    return MagicMock(
        spec=GlobalConfiguration,
        access=MagicMock(
            classification=Classification.internal.value,
            ssdl=MagicMock(rep_include=None),
        ),
    )


@pytest.fixture
def mock_export_data() -> MagicMock:
    """Create a mock export data with all required attributes."""
    mock = MagicMock()
    mock.content = "depth"
    mock.content_metadata = None
    mock.name = "test_name"
    mock.tagname = "test_tag"
    mock.forcefolder = ""
    mock.subfolder = ""
    mock.parent = ""
    mock.filename_timedata_reverse = False
    mock.geometry = None
    mock.vertical_domain = "depth"
    mock.domain_reference = "msl"
    mock.fmu_context = None
    mock.preprocessed = False
    mock.display_name = "Test Display"
    mock.workflow = None
    mock.description = None
    mock.classification = "internal"
    mock.access_ssdl = None
    mock.rep_include = None
    mock.is_prediction = True
    mock.is_observation = False
    mock.table_index = None
    mock.table_fformat = "csv"
    mock.polygons_fformat = "csv"
    mock.points_fformat = "csv"
    mock.timedata = None
    mock.unit = "m"
    mock.undef_is_zero = False
    mock.casepath = None
    mock.config = {}
    return mock


def test_resolve_global_config_with_global_configuration() -> None:
    """GlobalConfiguration instance is returned as-is."""
    mock_config = MagicMock(spec=GlobalConfiguration)
    result = _resolve_global_config(mock_config)
    assert result is mock_config


def test_resolve_global_config_with_empty_dict() -> None:
    """Empty dict returns None."""
    result = _resolve_global_config({})
    assert result is None


def test_resolve_global_config_with_invalid_dict_missing_masterdata() -> None:
    """Invalid config without masterdata returns None and warns."""
    with pytest.warns(UserWarning, match="lacking masterdata definitions"):
        result = _resolve_global_config({"some": "data"})
    assert result is None


def test_resolve_global_config_with_invalid_dict_with_masterdata() -> None:
    """Invalid config with masterdata returns None and warns."""
    with pytest.warns(UserWarning):
        result = _resolve_global_config({"masterdata": {"invalid": "data"}})
    assert result is None


def test_resolve_global_config_with_valid_dict(
    mock_global_config: dict[str, Any],
) -> None:
    """Valid config dict is resolved to GlobalConfiguration."""
    result = _resolve_global_config(mock_global_config)
    assert isinstance(result, GlobalConfiguration)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (None, None),
        ("depth", Content.depth),
        ("time", Content.time),
        ("seismic", Content.seismic),
        ({"seismic": {"attribute": "amplitude"}}, Content.seismic),
        ({"depth": {}}, Content.depth),
    ],
)
def test_resolve_content_enum(
    content: str | dict[str, Any] | None,
    expected: Content | None,
) -> None:
    """Resolves content to enum from possible formats."""
    assert _resolve_content_enum(content) == expected


@pytest.mark.parametrize(
    ("content", "match"),
    [
        (123, "not a valid value for 'content'"),
        ("not_a_content", None),
    ],
)
def test_resolve_content_enum_invalid(content: Any, match: str | None) -> None:
    """Raises ValueError for invalid content inputs."""
    with pytest.raises(ValueError, match=match):
        _resolve_content_enum(content)


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        (Content.field_outline, True),
        (Content.field_region, True),
        (Content.fluid_contact, True),
        (Content.property, True),
        (Content.seismic, True),
        (Content.depth, False),
        (Content.timeseries, False),
        (Content.volumes, False),
    ],
)
def test_content_requires_metadata(content_type: Content, expected: bool) -> None:
    """Content types requiring extra metadata are resolved as such."""
    assert _content_requires_metadata(content_type) is expected


@pytest.mark.parametrize(
    ("content_metadata", "content", "expected"),
    [
        (
            {"attribute": "amplitude"},
            "seismic",
            AllowedContentSeismic(attribute="amplitude"),
        ),
        (
            {"attribute": "custom"},
            {"seismic": {"attribute": "from_dict"}},
            AllowedContentSeismic(attribute="custom"),
        ),
        (
            None,
            {"seismic": {"attribute": "amplitude", "calculation": "mean"}},
            AllowedContentSeismic(attribute="amplitude", calculation="mean"),
        ),
        (
            {"attribute": "porosity", "is_discrete": False},
            "property",
            Property(attribute="porosity", is_discrete=False),
        ),
        (None, "depth", None),
        (None, None, None),
    ],
)
def test_resolve_content_metadata(
    content_metadata: dict[str, Any] | None,
    content: str | dict[str, Any] | None,
    expected: AnyContentMetadata | None,
) -> None:
    """Resolves content metadata from arg or dict."""
    assert _resolve_content_metadata(content_metadata, content) == expected


@pytest.mark.parametrize(
    "content",
    [
        {"seismic": "myvalue"},
        {"property": ["foo", "bar"]},
        {"field_outline": 123},
    ],
)
def test_resolve_invalid_content_metadata_from_content(content: dict[str, Any]) -> None:
    """Resolves to a ValueError if invalid content metadata given via content."""
    with pytest.raises(ValueError, match="must be a dictionary."):
        _resolve_content_metadata(None, content)


@pytest.mark.parametrize(
    ("content", "raises", "warns"),
    [
        (Content.field_outline, True, False),
        (Content.field_region, True, False),
        (Content.fluid_contact, True, False),
        (Content.seismic, True, False),
        (Content.property, False, True),
    ],
)
def test_resolve_content_metadata_raises_and_warns(
    content: Content, raises: bool, warns: bool
) -> None:
    """Resolving content metadata raises or warns appropriate."""
    if raises:
        with pytest.raises(
            ValueError, match=f"Content '{content}' requires additional"
        ):
            _resolve_content_metadata(None, str(content))

    if warns:
        with pytest.warns(FutureWarning):
            _resolve_content_metadata(None, str(content))


@pytest.mark.parametrize(
    ("vertical_domain", "domain_reference", "expected_domain", "expected_ref"),
    [
        ("depth", "msl", VerticalDomain.depth, DomainReference.msl),
        ("time", "sb", VerticalDomain.time, DomainReference.sb),
        ("depth", "rkb", VerticalDomain.depth, DomainReference.rkb),
        ({"time": "sb"}, "msl", VerticalDomain.time, DomainReference.sb),
        ({"depth": "rkb"}, "ignored", VerticalDomain.depth, DomainReference.rkb),
    ],
)
def test_resolve_vertical_domain(
    vertical_domain: str | dict[str, str],
    domain_reference: str,
    expected_domain: VerticalDomain,
    expected_ref: DomainReference,
) -> None:
    """Resolves vert domain and domain ref from string or dict inputs."""
    vert, ref = _resolve_vertical_domain(vertical_domain, domain_reference)
    assert vert == expected_domain
    assert ref == expected_ref


@pytest.mark.parametrize(
    ("vertical_domain", "domain_reference", "match"),
    [
        ("invalid", "msl", "not a valid value for 'vertical_domain'"),
        ("depth", "invalid", "not a valid value for 'domain_reference'"),
        ({"invalid", "msl"}, "msl", "not a valid value for 'vertical_domain'"),
    ],
)
def test_resolve_vertical_domain_invalid(
    vertical_domain: str | dict[str, str], domain_reference: str, match: str
) -> None:
    """Raises ValueError for invalid domain or reference."""
    with pytest.raises(ValueError, match=match):
        _resolve_vertical_domain(vertical_domain, domain_reference)


@pytest.mark.parametrize(
    ("classification_input", "access_ssdl", "use_config", "expected"),
    [
        ("restricted", None, False, Classification.restricted),
        ("restricted", {"access_level": "internal"}, True, Classification.restricted),
        ("internal", None, True, Classification.internal),
        (None, {"access_level": "restricted"}, False, Classification.restricted),
        (None, {"access_level": "internal"}, False, Classification.internal),
        (None, None, False, Classification.internal),
    ],
)
def test_resolve_classification(
    classification_input: str | None,
    access_ssdl: dict[str, Any] | None,
    use_config: bool,
    expected: Classification,
    mock_config_internal: GlobalConfiguration,
) -> None:
    """Resolves classification from different inputs."""
    config = mock_config_internal if use_config else None
    result = _resolve_classification(classification_input, access_ssdl, config)
    assert result == expected


def test_resolve_classification_asset_deprecated() -> None:
    """Deprecated 'asset' value is converted to 'restricted' with a warning."""
    with pytest.warns(FutureWarning, match="'asset'.*deprecated"):
        result = _resolve_classification("asset", None, None)
    assert result == Classification.restricted


@pytest.mark.parametrize(
    ("rep_include_input", "access_ssdl", "expected"),
    [
        (True, None, True),
        (False, None, False),
        (False, {"rep_include": True}, False),
        (True, {"rep_include": False}, True),
        (None, {"rep_include": True}, True),
        (None, {"rep_include": False}, False),
        (None, None, False),
    ],
)
def test_resolve_rep_include(
    rep_include_input: bool | None,
    access_ssdl: dict[str, Any] | None,
    expected: bool,
) -> None:
    """Resolves rep_include from input or access_ssdl."""
    result = _resolve_rep_include(rep_include_input, access_ssdl, None)
    assert result is expected


def test_resolve_rep_include_config_without_ssdl() -> None:
    """Handles config without ssdl in it."""
    config = MagicMock(spec=GlobalConfiguration, access=MagicMock(ssdl=None))
    result = _resolve_rep_include(None, None, config)
    assert result is False


@pytest.mark.parametrize(
    ("workflow", "expected_reference"),
    [
        (None, None),
        ("cool workflow", "cool workflow"),
        ({"reference": "workflow ref"}, "workflow ref"),
    ],
)
def test_resolve_workflow(
    workflow: str | dict[str, str] | None, expected_reference: str | None
) -> None:
    """Resolves workflow from string or dict."""
    result = _resolve_workflow(workflow)
    if expected_reference is None:
        assert result is None
    else:
        assert isinstance(result, Workflow)
        assert result.reference == expected_reference


@pytest.mark.parametrize(
    ("desc", "expected"),
    [
        (None, None),
        ("", None),
        ("My description", ["My description"]),
        (["Line 1", "Line 2"], ["Line 1", "Line 2"]),
    ],
)
def test_resolve_description(
    desc: str | list[str] | None, expected: list[str] | None
) -> None:
    """Resolves description toa a list."""
    assert _resolve_description(desc) == expected


def test_resolve_description_invalid_type() -> None:
    """Raises value error on bad type."""
    with pytest.raises(ValueError, match="not a valid value for 'description'"):
        _resolve_description(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="not a valid value for 'description'"):
        _resolve_description(["foo", 1])  # type: ignore[list-item]


def test_export_config_from_export_data_basic(mock_export_data: MagicMock) -> None:
    """ExportConfig is created with resolved values from ExportData."""
    with patch("fmu.dataio._export_config._resolve_fmu_context") as mock_fmu_ctx:
        mock_fmu_ctx.return_value = (None, False)

        config = ExportConfig.from_export_data(mock_export_data)

        assert config.content == Content.depth
        assert config.name == "test_name"
        assert config.tagname == "test_tag"
        assert config.vertical_domain == VerticalDomain.depth
        assert config.domain_reference == DomainReference.msl
        assert config.classification == Classification.internal
        assert config.unit == "m"
        assert config.is_prediction is True
        assert config.is_observation is False


@pytest.mark.parametrize(
    ("attr", "value", "expected_attr", "expected_value"),
    [
        ("casepath", "/some/path", "casepath", Path("/some/path")),
        ("casepath", None, "casepath", None),
        ("content", None, "content", "unset"),
        ("unit", None, "unit", ""),
        ("unit", "m", "unit", "m"),
    ],
)
def test_export_config_from_export_data_transformations(
    mock_export_data: MagicMock,
    attr: str,
    value: Any,
    expected_attr: str,
    expected_value: Any,
) -> None:
    """ExportConfig applies correct transformations to input vals."""
    setattr(mock_export_data, attr, value)

    with patch("fmu.dataio._export_config._resolve_fmu_context") as mock_fmu_ctx:
        mock_fmu_ctx.return_value = (None, False)

        config = ExportConfig.from_export_data(mock_export_data)
        assert getattr(config, expected_attr) == expected_value


def test_export_config_from_export_data_with_global_config(
    mock_export_data: MagicMock,
    mock_global_config: dict[str, Any],
) -> None:
    """GlobalConfiguration is passed through, dict becomes None."""
    mock_global_config = MagicMock(spec=GlobalConfiguration, access=MagicMock())
    mock_export_data.config = mock_global_config

    with patch("fmu.dataio._export_config._resolve_fmu_context") as mock_fmu_ctx:
        mock_fmu_ctx.return_value = (None, False)

        config = ExportConfig.from_export_data(mock_export_data)
        assert config.config is mock_global_config

    mock_export_data.config = {}
    with patch("fmu.dataio._export_config._resolve_fmu_context") as mock_fmu_ctx:
        mock_fmu_ctx.return_value = (None, False)

        config = ExportConfig.from_export_data(mock_export_data)
        assert config.config is None

    mock_export_data.config = {"some": "dict"}
    with (
        patch("fmu.dataio._export_config._resolve_fmu_context") as mock_fmu_ctx,
        pytest.warns(UserWarning, match="lacking masterdata"),
    ):
        mock_fmu_ctx.return_value = (None, False)

        config = ExportConfig.from_export_data(mock_export_data)
        assert config.config is None

    mock_export_data.config = mock_global_config
    with patch("fmu.dataio._export_config._resolve_fmu_context") as mock_fmu_ctx:
        mock_fmu_ctx.return_value = (None, False)

        config = ExportConfig.from_export_data(mock_export_data)
        assert isinstance(config.config, GlobalConfiguration)


def test_export_config_is_immutable(mock_export_data: MagicMock) -> None:
    """ExportConfig is frozen."""

    with patch("fmu.dataio._export_config._resolve_fmu_context") as mock_fmu_ctx:
        mock_fmu_ctx.return_value = (None, False)

        config = ExportConfig.from_export_data(mock_export_data)

        with pytest.raises(AttributeError):
            config.name = "new_name"  # type: ignore[misc]
