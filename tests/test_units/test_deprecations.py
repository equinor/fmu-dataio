"""Tests for deprecation resolution."""

from typing import Any

import pytest

from fmu.dataio._deprecations import (
    DeprecationResolution,
    resolve_deprecations,
)


def _default_args() -> dict[str, Any]:
    """Return default arguments for resolve_deprecations with no deprecations."""
    return {
        # Arguments with replacements
        "access_ssdl": None,
        "classification": None,
        "rep_include": None,
        "content": "depth",
        "vertical_domain": "depth",
        "workflow": None,
        # Arguments with no effect
        "runpath": None,
        "grid_model": None,
        "legacy_time_format": False,
        "createfolder": True,
        "verifyfolder": True,
        "reuse_metadata_rule": None,
        "realization": None,
        "aggregation": False,
        "table_include_index": False,
        "verbosity": "DEPRECATED",
        "allow_forcefolder_absolute": False,
        "include_ertjobs": False,
        "depth_reference": None,
        "meta_format": None,
        # Format options
        "arrow_fformat": None,
        "cube_fformat": None,
        "grid_fformat": None,
        "surface_fformat": None,
        "dict_fformat": None,
    }


def test_no_deprecations_returns_empty_warnings() -> None:
    """When no deprecated arguments are used, no warnings should be emitted."""
    args = _default_args()
    resolution = resolve_deprecations(**args)

    assert resolution.warnings == []
    assert resolution.errors == []


def test_resolution_is_immutable() -> None:
    """DeprecationResolution should be frozen (immutable)."""
    resolution = DeprecationResolution()

    with pytest.raises(AttributeError):
        resolution.warnings = []  # type: ignore[misc]


def test_access_ssdl_emits_future_warning() -> None:
    """Using access_ssdl should emit FutureWarning."""
    args = _default_args()
    args["access_ssdl"] = {"access_level": "internal"}

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert "access_ssdl" in message
    assert "deprecated" in message.lower()
    assert category is FutureWarning


def test_access_ssdl_with_classification_returns_error() -> None:
    """Using access_ssdl with classification should return error."""
    args = _default_args()
    args["access_ssdl"] = {"access_level": "internal"}
    args["classification"] = "restricted"

    resolution = resolve_deprecations(**args)

    # Should have both warning (for deprecated access_ssdl) and error
    assert len(resolution.warnings) == 1
    assert len(resolution.errors) == 1
    assert "not supported" in resolution.errors[0]


def test_access_ssdl_with_rep_include_returns_error() -> None:
    """Using access_ssdl with rep_include should return error."""
    args = _default_args()
    args["access_ssdl"] = {"access_level": "internal"}
    args["rep_include"] = True

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    assert len(resolution.errors) == 1
    assert "not supported" in resolution.errors[0]


def test_content_dict_emits_future_warning() -> None:
    """Using content as dict should emit FutureWarning."""
    args = _default_args()
    args["content"] = {"depth": {"some": "metadata"}}

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert "content" in message
    assert "content_metadata" in message
    assert category is FutureWarning


def test_vertical_domain_dict_emits_future_warning() -> None:
    """Using vertical_domain as dict should emit FutureWarning."""
    args = _default_args()
    args["vertical_domain"] = {"depth": "msl"}

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert "vertical_domain" in message
    assert "domain_reference" in message
    assert category is FutureWarning


def test_workflow_dict_emits_future_warning() -> None:
    """Using workflow as dict should emit FutureWarning."""
    args = _default_args()
    args["workflow"] = {"name": "my_workflow"}

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert "workflow" in message
    assert "string" in message.lower()
    assert category is FutureWarning


@pytest.mark.parametrize(
    ("arg_name", "arg_value", "expected_in_message"),
    [
        ("runpath", "/some/path", "runpath"),
        ("grid_model", "some_model", "grid_model"),
        ("legacy_time_format", True, "legacy_time_format"),
        ("reuse_metadata_rule", "some_rule", "reuse_metadata_rule"),
        ("realization", 1, "realization"),
        ("aggregation", True, "aggregation"),
        ("table_include_index", True, "table_include_index"),
        ("allow_forcefolder_absolute", True, "forcefolder"),
        ("include_ertjobs", True, "include_ertjobs"),
        ("depth_reference", "msl", "depth_reference"),
        ("meta_format", "json", "meta_format"),
    ],
)
def test_no_effect_arguments_emit_user_warning(
    arg_name: str,
    arg_value: object,
    expected_in_message: str,
) -> None:
    """Arguments with no effect should emit UserWarning."""
    args = _default_args()
    args[arg_name] = arg_value

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert expected_in_message in message
    assert category is UserWarning


def test_createfolder_false_emits_warning() -> None:
    """Setting createfolder=False should emit warning."""
    args = _default_args()
    args["createfolder"] = False

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert "createfolder" in message
    assert category is UserWarning


def test_verifyfolder_false_emits_warning() -> None:
    """Setting verifyfolder=False should emit warning."""
    args = _default_args()
    args["verifyfolder"] = False

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert "verifyfolder" in message
    assert category is UserWarning


def test_verbosity_not_deprecated_emits_warning() -> None:
    """Setting verbosity to anything other than 'DEPRECATED' should emit warning."""
    args = _default_args()
    args["verbosity"] = "INFO"

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert "verbosity" in message
    assert category is UserWarning


@pytest.mark.parametrize(
    "format_arg",
    [
        "arrow_fformat",
        "cube_fformat",
        "grid_fformat",
        "surface_fformat",
        "dict_fformat",
    ],
)
def test_format_options_emit_single_warning(format_arg: str) -> None:
    """Any format option should emit a single combined warning."""
    args = _default_args()
    args[format_arg] = "some_format"

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 1
    message, category = resolution.warnings[0]
    assert "fformat" in message
    assert category is UserWarning


def test_multiple_format_options_emit_single_warning() -> None:
    """Multiple format options should still emit only one combined warning."""
    args = _default_args()
    args["arrow_fformat"] = "parquet"
    args["cube_fformat"] = "segy"
    args["grid_fformat"] = "roff"

    resolution = resolve_deprecations(**args)

    # Should be exactly one warning for all format options combined
    format_warnings = [w for w in resolution.warnings if "fformat" in w[0]]
    assert len(format_warnings) == 1


def test_multiple_deprecations_accumulate_warnings() -> None:
    """Multiple deprecated arguments should accumulate warnings."""
    args = _default_args()
    args["runpath"] = "/some/path"
    args["grid_model"] = "some_model"
    args["content"] = {"depth": {}}

    resolution = resolve_deprecations(**args)

    assert len(resolution.warnings) == 3
