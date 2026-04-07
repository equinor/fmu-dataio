import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from pytest import MonkeyPatch

from fmu.dataio._global_config import (
    GLOBAL_CONFIG_ENV_VAR,
    _build_global_configuration,
    _resolve_global_config_path,
    load_global_config,
    load_global_config_from_global_variables,
)
from fmu.dataio.exceptions import ValidationError


def test_build_global_configuration_valid(mock_global_config: dict[str, Any]) -> None:
    """Ensures a validated GlobalConfiguration object is returned without error."""
    global_config = _build_global_configuration(mock_global_config)
    assert isinstance(global_config, GlobalConfiguration)


def test_build_global_configuration_invalid(mock_global_config: dict[str, Any]) -> None:
    """Exception and warning raised on generally invalid global config."""
    del mock_global_config["model"]

    with (
        pytest.raises(ValidationError, match="does not contain valid"),
        pytest.warns(UserWarning, match="global configuration has one or more errors"),
    ):
        _build_global_configuration(mock_global_config)


def test_build_global_configuration_missing_masterdata(
    mock_global_config: dict[str, Any],
) -> None:
    """Exception and warning raised when 'masterdata' missing."""
    del mock_global_config["masterdata"]

    with (
        pytest.raises(ValidationError, match="https://fmu-dataio.readthedocs.io"),
        pytest.warns(UserWarning, match="global configuration has one or more errors"),
    ):
        _build_global_configuration(mock_global_config)


def test_build_global_configuration_standard_result(
    mock_global_config: dict[str, Any],
) -> None:
    """Exception and warning raised when 'masterdata' missing for a standard result."""
    del mock_global_config["masterdata"]

    with pytest.raises(ValidationError, match="exporting standard results"):
        _build_global_configuration(mock_global_config, standard_result=True)


def test_load_config_from_global_variables(drogon_global_config_path: Path) -> None:
    """Valid case of loading global config from global variables."""
    global_config = load_global_config_from_global_variables(drogon_global_config_path)
    assert isinstance(global_config, GlobalConfiguration)


def test_load_config_from_global_variables_invalid_path() -> None:
    """Invalid case of loading global config from global variables."""

    with pytest.raises(FileNotFoundError, match="Could not find"):
        load_global_config_from_global_variables(Path(".foo"))


def test_load_invalid_config_from_global_variables(tmp_path: Path) -> None:
    """Invalid global configuration yaml file raises exception."""
    bad_global_config = tmp_path / "global_variables.yml"
    bad_global_config.write_bytes(b"\x01")

    with pytest.raises(ValueError, match="Unable to load config"):
        load_global_config_from_global_variables(bad_global_config)


def test_resolve_global_config_path_resolves_to_existing_path(
    drogon_global_config_path: Path,
) -> None:
    """Tests that resolution returns itself if provided a valid path."""
    assert (
        _resolve_global_config_path(drogon_global_config_path)
        == drogon_global_config_path
    )


@pytest.mark.parametrize(
    "given",
    [
        None,
        Path("foo"),
        Path("global_variables.yml"),
    ],
)
def test_resolve_global_config_path_raises_if_not_options_found(
    tmp_path: Path, given: Path
) -> None:
    """Tests that an exception is raised if no config file found."""
    with pytest.raises(FileNotFoundError, match="Could not find the global"):
        _resolve_global_config_path(given)


@pytest.mark.parametrize(
    "mock_cwd",
    [
        Path("."),
        Path("ert/model"),
        Path("rms/model"),
    ],
)
@pytest.mark.parametrize("check_env", [True, False])
def test_resolve_global_config_path_from_known_paths(
    runpath: Path,
    monkeypatch: MonkeyPatch,
    drogon_global_config_path: Path,
    mock_cwd: Path,
    check_env: bool,
) -> None:
    """Global configuration path resolves correctly with different inputs.

    Tests the most common path, and also if check_env differs."""
    fmuconfig_output_dir = runpath / "fmuconfig" / "output"
    fmuconfig_output_dir.mkdir(parents=True)

    config_path = fmuconfig_output_dir / "global_variables.yml"
    shutil.copy(drogon_global_config_path, config_path)

    cwd_dir = runpath / mock_cwd
    cwd_dir.mkdir(parents=True, exist_ok=True)

    # Call from runpath, ert model path, and rms model path
    monkeypatch.chdir(cwd_dir)
    if check_env:
        monkeypatch.setenv(GLOBAL_CONFIG_ENV_VAR, str(drogon_global_config_path))

    expected_config_path = drogon_global_config_path if check_env else config_path

    assert (
        _resolve_global_config_path(None, check_env=check_env) == expected_config_path
    )
    # Always resolves to config_path if valid
    assert _resolve_global_config_path(config_path, check_env=check_env) == config_path


def test_resolve_global_config_path_exists(
    runpath: Path, monkeypatch: MonkeyPatch, drogon_global_config_path: Path
) -> None:
    """Default global configuration path is used when no .fmu/ is present."""
    fmuconfig_output_dir = runpath / "fmuconfig" / "output"
    fmuconfig_output_dir.mkdir(parents=True)
    shutil.copy(
        drogon_global_config_path, fmuconfig_output_dir / "global_variables.yml"
    )

    ert_model_dir = runpath / "ert" / "model"
    ert_model_dir.mkdir(parents=True)

    monkeypatch.chdir(ert_model_dir)
    global_config = load_global_config()
    assert isinstance(global_config, GlobalConfiguration)


def test_load_global_config_returns_global_configuration(
    drogon_global_config_path: Path,
) -> None:
    """Global configuration path is used when no .fmu/ is present."""
    global_config = load_global_config(drogon_global_config_path)
    assert isinstance(global_config, GlobalConfiguration)


def test_load_global_config_returns_global_configuration_with_default_path(
    runpath: Path, monkeypatch: MonkeyPatch, drogon_global_config_path: Path
) -> None:
    """Default global configuration path is used when no .fmu/ is present."""
    fmuconfig_output_dir = runpath / "fmuconfig" / "output"
    fmuconfig_output_dir.mkdir(parents=True)
    shutil.copy(
        drogon_global_config_path, fmuconfig_output_dir / "global_variables.yml"
    )

    ert_model_dir = runpath / "ert" / "model"
    ert_model_dir.mkdir(parents=True)

    monkeypatch.chdir(ert_model_dir)
    global_config = load_global_config()
    assert isinstance(global_config, GlobalConfiguration)


@pytest.mark.parametrize("standard_result", [True, False])
def test_load_global_config_passes_standard_result_to_build(
    drogon_global_config_path: Path, standard_result: bool
) -> None:
    """Standard result argument is passed back to global config builder."""
    with patch("fmu.dataio._global_config._build_global_configuration") as mock_build:
        load_global_config(drogon_global_config_path, standard_result=standard_result)

    assert mock_build.call_args[0][1] == standard_result
