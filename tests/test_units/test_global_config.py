import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pydantic
import pytest
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.settings._drogon import create_drogon_fmu_dir
from pytest import MonkeyPatch

from fmu.dataio._global_config import (
    _resolve_global_config_path,
    build_global_configuration,
    load_global_config,
    load_global_config_from_fmu_settings,
    load_global_config_from_global_variables,
)
from fmu.dataio.exceptions import ValidationError


def test_build_global_configuration_valid(mock_global_config: dict[str, Any]) -> None:
    """Ensures a validated GlobalConfiguration object is returned without error."""
    global_config = build_global_configuration(mock_global_config)
    assert isinstance(global_config, GlobalConfiguration)


def test_build_global_configuration_invalid(mock_global_config: dict[str, Any]) -> None:
    """Exception raised on generally invalid global config."""
    del mock_global_config["model"]

    with pytest.raises(ValidationError, match="global configuration is invalid"):
        build_global_configuration(mock_global_config)


def test_build_global_configuration_missing_masterdata(
    mock_global_config: dict[str, Any],
) -> None:
    """Exception raised with 'Getting started' link when 'masterdata' is missing."""
    del mock_global_config["masterdata"]

    with pytest.raises(ValidationError, match="https://fmu-dataio.readthedocs.io"):
        build_global_configuration(mock_global_config)


def test_build_global_configuration_standard_result(
    mock_global_config: dict[str, Any],
) -> None:
    """Exception raised when invalid config is given for a standard result export."""
    del mock_global_config["masterdata"]

    with pytest.raises(ValidationError, match="Exporting standard results"):
        build_global_configuration(mock_global_config, standard_result=True)


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
def test_resolve_global_config_path_from_known_paths(
    runpath: Path,
    monkeypatch: MonkeyPatch,
    drogon_global_config_path: Path,
    mock_cwd: Path,
) -> None:
    """Global configuration path resolves correctly with different inputs."""

    fmuconfig_output_dir = runpath / "fmuconfig" / "output"
    fmuconfig_output_dir.mkdir(parents=True)

    config_path = fmuconfig_output_dir / "global_variables.yml"
    shutil.copy(drogon_global_config_path, config_path)

    cwd_dir = runpath / mock_cwd
    cwd_dir.mkdir(parents=True, exist_ok=True)

    # Call from runpath, ert model path, and rms model path
    monkeypatch.chdir(cwd_dir)
    assert _resolve_global_config_path(None) == config_path
    # Always resolves to config_path if valid
    assert _resolve_global_config_path(config_path) == config_path


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
    with patch("fmu.dataio._global_config.build_global_configuration") as mock_build:
        load_global_config(drogon_global_config_path, standard_result=standard_result)

    assert mock_build.call_args[0][1] == standard_result


def test_load_from_fmu_settings_returns_config_when_dotfmu_exists(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """A valid .fmu/ directory produces a GlobalConfiguration."""
    create_drogon_fmu_dir(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = load_global_config_from_fmu_settings()
    assert isinstance(result, GlobalConfiguration)
    assert result.model.name == "Drogon"  # not 'global_variables'


def test_load_from_fmu_settings_returns_none_when_no_dotfmu(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """No .fmu/ directory means None is returned."""
    monkeypatch.chdir(tmp_path)

    result = load_global_config_from_fmu_settings()
    assert result is None


def test_load_from_fmu_settings_returns_none_when_config_incomplete(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """If the .fmu config is missing required fields, returns None."""
    fmu_dir = create_drogon_fmu_dir(tmp_path)
    monkeypatch.chdir(tmp_path)

    fmu_dir.config.set("masterdata", None)

    result = load_global_config_from_fmu_settings()
    assert result is None


def test_load_from_fmu_settings_returns_none_on_invalid_access(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """If access data cannot be validated, returns None."""
    create_drogon_fmu_dir(tmp_path)
    monkeypatch.chdir(tmp_path)

    with patch(
        "fmu.dataio._global_config.Access.model_validate",
        side_effect=pydantic.ValidationError.from_exception_data(
            title="Access", line_errors=[]
        ),
    ):
        result = load_global_config_from_fmu_settings()
    assert result is None


def test_load_from_fmu_settings_returns_none_on_invalid_stratigraphy(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """If stratigraphy cannot be built, returns None."""
    fmu_dir = create_drogon_fmu_dir(tmp_path)
    monkeypatch.chdir(tmp_path)

    with (
        patch.object(
            fmu_dir._mappings,
            "build_global_config_stratigraphy",
            side_effect=pydantic.ValidationError.from_exception_data(
                title="Stratigraphy", line_errors=[]
            ),
        ),
        patch(
            "fmu.dataio._global_config.find_nearest_fmu_directory",
            return_value=fmu_dir,
        ),
    ):
        result = load_global_config_from_fmu_settings()
    assert result is None


def test_load_from_fmu_settings_has_stratigraphy(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """The GlobalConfiguration from .fmu/ includes stratigraphy data."""
    create_drogon_fmu_dir(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = load_global_config_from_fmu_settings()
    assert result is not None
    assert result.stratigraphy is not None
    assert len(result.stratigraphy.root) > 0


def test_load_global_config_prefers_fmu_settings(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    drogon_global_config_path: Path,
) -> None:
    """When .fmu/ exists, load_global_config prefers it over global_variables.yml."""
    create_drogon_fmu_dir(tmp_path)

    fmuconfig_output = tmp_path / "fmuconfig" / "output"
    fmuconfig_output.mkdir(parents=True)
    shutil.copy(drogon_global_config_path, fmuconfig_output / "global_variables.yml")

    monkeypatch.chdir(tmp_path)

    result = load_global_config()
    assert isinstance(result, GlobalConfiguration)
    # .fmu has model.name="Drogon", global_variables has model.name="global_variables"
    assert result.model.name == "Drogon"


def test_load_global_config_falls_back_to_global_variables(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    drogon_global_config_path: Path,
) -> None:
    """When no .fmu/ exists, load_global_config uses global_variables.yml."""
    fmuconfig_output = tmp_path / "fmuconfig" / "output"
    fmuconfig_output.mkdir(parents=True)
    shutil.copy(drogon_global_config_path, fmuconfig_output / "global_variables.yml")

    monkeypatch.chdir(tmp_path)

    result = load_global_config()
    assert isinstance(result, GlobalConfiguration)
    assert result.model.name == "global_variables"


def test_load_global_config_raises_when_neither_source_exists(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """When no .fmu/ and no global_variables.yml, raises FileNotFoundError."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        load_global_config()


def test_load_global_config_falls_back_when_fmu_settings_incomplete(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    drogon_global_config_path: Path,
) -> None:
    """When .fmu/ config is incomplete, falls back to global_variables.yml."""
    fmu_dir = create_drogon_fmu_dir(tmp_path)

    fmu_dir.config.set("masterdata", None)

    fmuconfig_output = tmp_path / "fmuconfig" / "output"
    fmuconfig_output.mkdir(parents=True)
    shutil.copy(drogon_global_config_path, fmuconfig_output / "global_variables.yml")

    monkeypatch.chdir(tmp_path)

    result = load_global_config()
    assert isinstance(result, GlobalConfiguration)
    assert result.model.name == "global_variables"


def test_load_global_config_with_explicit_path_still_prefers_fmu_settings(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    drogon_global_config_path: Path,
) -> None:
    """Even when an explicit config_path is given, .fmu/ is preferred."""
    create_drogon_fmu_dir(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = load_global_config(config_path=drogon_global_config_path)
    assert isinstance(result, GlobalConfiguration)
    # .fmu is still preferred
    assert result.model.name == "Drogon"


def test_load_global_config_from_runpath_with_dotfmu(
    runpath: Path,
    drogon_global_config_path: Path,
) -> None:
    """Integration test on runpath with .fmu/."""
    result = load_global_config()
    assert isinstance(result, GlobalConfiguration)
    assert result.model.name == "Drogon"
    assert result.stratigraphy is not None


def test_load_global_config_from_runpath_without_dotfmu(
    runpath_no_dotfmu: Path,
    drogon_global_config_path: Path,
) -> None:
    """Integration test on runpath without .fmu/."""
    fmuconfig_output = runpath_no_dotfmu / "fmuconfig" / "output"
    fmuconfig_output.mkdir(parents=True)
    shutil.copy(drogon_global_config_path, fmuconfig_output / "global_variables.yml")

    result = load_global_config()
    assert isinstance(result, GlobalConfiguration)
    assert result.model.name == "global_variables"
