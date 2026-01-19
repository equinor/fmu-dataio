from __future__ import annotations

import getpass
import importlib
import os
import pathlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, get_args
from unittest.mock import AsyncMock, MagicMock, patch

import ert.__main__
import pytest
import yaml
from ert.config import GenKwConfig
from ert.config.distribution import DistributionSettings
from fmu.datamodels.parameters import (
    ConstParameter,
    LogUnifParameter,
    ParameterMetadata,
    RawParameter,
    UniformParameter,
)
from pytest import CaptureFixture, MonkeyPatch

from fmu.dataio.scripts.create_case_metadata import (
    parameter_config_to_parameter_metadata,
)

from .ert_config_utils import (
    add_create_case_workflow,
    add_design_matrix,
    add_globvar_parameters,
    add_multregt_parameters,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_create_case_metadata_runs_successfully(
    fmu_snakeoil_project: Path, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    fmu_case_yml = (
        fmu_snakeoil_project / "scratch/user/snakeoil/share/metadata/fmu_case.yml"
    )
    assert fmu_case_yml.exists()

    with open(fmu_case_yml, encoding="utf-8") as f:
        fmu_case = yaml.safe_load(f)

    assert fmu_case["fmu"]["case"]["name"] == "snakeoil"
    assert fmu_case["fmu"]["case"]["user"]["id"] == getpass.getuser()
    assert fmu_case["source"] == "fmu"
    assert len(fmu_case["tracklog"]) == 1
    assert fmu_case["tracklog"][0]["user"]["id"] == getpass.getuser()


def test_create_case_metadata_warns_without_overwriting(
    fmu_snakeoil_project: Path, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    share_metadata = fmu_snakeoil_project / "scratch/user/snakeoil/share/metadata"
    fmu_case_yml = share_metadata / "fmu_case.yml"

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    assert fmu_case_yml.exists()
    with open(fmu_case_yml, encoding="utf-8") as f:
        first_run = yaml.safe_load(f)

    with pytest.warns(UserWarning, match="Using existing case metadata from casepath:"):
        ert.__main__.main()

    ls_share_metadata = os.listdir(share_metadata)
    assert ls_share_metadata == ["fmu_case.yml"]

    with open(fmu_case_yml, encoding="utf-8") as f:
        second_run = yaml.safe_load(f)

    assert first_run == second_run


def test_create_case_metadata_caseroot_not_defined(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    capsys: CaptureFixture[str],
) -> None:
    """Test that a proper error message is given if the case root is
    input as an undefined ERT variable"""
    pathlib.Path(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata"
    ).write_text(
        "WF_CREATE_CASE_METADATA <CASEPATH_NOT_DEFINED> <CONFIG_PATH> <CASE_DIR>",
        encoding="utf-8",
    )

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: ERT variable used for the case root is not defined" in stderr


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_enable_mocked_sumo(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    mock_sumo_uploader: dict[str, MagicMock | AsyncMock],
) -> None:
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo" "--sumo_env" prod')

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    with pytest.warns(FutureWarning, match="'sumo_env' is ignored"):
        ert.__main__.main()

    # Verifies case.register() was run
    with open("sumo_case_id", encoding="utf-8") as f:
        assert f.read() == "1"


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_dev_input_fails(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    mock_sumo_uploader: dict[str, MagicMock | AsyncMock],
    capsys: CaptureFixture[str],
) -> None:
    """Test that if the sumo_env argument is input as dev it raises an error"""
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo" "--sumo_env" dev')

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: Setting sumo environment through argument" in stderr
    assert "SUMO_ENV" in stderr


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_reads_from_environment(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    mock_sumo_uploader: dict[str, MagicMock | AsyncMock],
) -> None:
    """Test that sumo_env is set through the 'SUMO_ENV' environment variable"""
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo"')

    sumo_env = "dev"
    monkeypatch.setenv("SUMO_ENV", sumo_env)

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    mock_sumo_uploader["SumoConnection"].assert_called_once_with(sumo_env)


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_defaults_to_prod(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    mock_sumo_uploader: dict[str, MagicMock | AsyncMock],
) -> None:
    """Test that sumo_env is defaulted to 'prod' when not set through the environment"""
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo"')

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()

    # should default to prod when not set
    mock_sumo_uploader["SumoConnection"].assert_called_once_with("prod")


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 12),
    reason="fmu-sumo-uploader not compatible with Python 3.12",
)
@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_input_is_ignored(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    mock_sumo_uploader: dict[str, MagicMock | AsyncMock],
) -> None:
    """Test that the environment variable is used over the sumo_env argument"""
    with open(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata",
        "a",
        encoding="utf-8",
    ) as f:
        f.write(' "--sumo" "--sumo_env" prod')

    sumo_env_expected = "dev"
    monkeypatch.setenv("SUMO_ENV", sumo_env_expected)

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    with pytest.warns(FutureWarning, match="'sumo_env' is ignored"):
        ert.__main__.main()

    mock_sumo_uploader["SumoConnection"].assert_called_once_with(sumo_env_expected)


def test_create_case_metadata_collects_ert_parameters_as_expected(
    fmu_snakeoil_project: Path, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> None:
    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_design_matrix(ert_config_path)
    add_globvar_parameters(ert_config_path)
    add_multregt_parameters(ert_config_path)

    add_create_case_workflow(ert_config_path)

    scalars_and_config = []

    def capture_params(ensemble: ert.Ensemble) -> None:
        """Captures params from Ert run.

        Requires the Ert runtime context to load from local storage."""
        scalars_and_config.append(ensemble.load_scalars())
        scalars_and_config.append(ensemble.experiment.parameter_configuration)

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    with patch(
        "fmu.dataio.scripts.create_case_metadata.export_ert_parameters",
        side_effect=capture_params,
    ):
        ert.__main__.main()

    assert len(scalars_and_config) == 2
    scalars, config_dict = scalars_and_config

    assert scalars.shape == (1, 10)
    assert set(scalars.columns) == {
        "realization",
        "GLOBVAR:globvar_a",
        "GLOBVAR:globvar_b",
        "GLOBVAR:globvar_c",
        "MULTREGT:multregt_a",
        "MULTREGT:multregt_b",
        "MULTREGT:multregt_c",
        "DESIGN_MATRIX:design_a",
        "DESIGN_MATRIX:design_b",
        "DESIGN_MATRIX:design_c",
    }

    # The one constant globvar
    assert scalars[0, "GLOBVAR:globvar_c"] == 1050.0

    assert scalars[0, "DESIGN_MATRIX:design_a"] == 1
    assert scalars[0, "DESIGN_MATRIX:design_b"] == 4
    assert scalars[0, "DESIGN_MATRIX:design_c"] == 7

    # Don't include the first 'realization' column
    for col in scalars.columns[1:]:
        group, name = col.split(":", 1)
        assert name in config_dict
        param_config = config_dict[name]

        assert param_config.type == "gen_kw"
        assert param_config.group == group

        distribution = "unknown distribution!"
        input_source = "unknown input source!"
        parameter_metadata: type[ParameterMetadata] | None = None
        match group:
            case "MULTREGT":
                distribution = "logunif"
                input_source = "sampled"
                parameter_metadata = LogUnifParameter
            case "DESIGN_MATRIX":
                distribution = "raw"
                input_source = "design_matrix"
                parameter_metadata = RawParameter
            case "GLOBVAR":
                match name:
                    case "globvar_a":
                        distribution = "logunif"
                        parameter_metadata = LogUnifParameter
                    case "globvar_b":
                        distribution = "uniform"
                        parameter_metadata = UniformParameter
                    case "globvar_c":
                        distribution = "const"
                        parameter_metadata = ConstParameter
                input_source = "sampled"

        assert param_config.distribution.name == distribution
        assert str(param_config.input_source) == input_source
        assert parameter_metadata is not None

        adapted_parameter = parameter_config_to_parameter_metadata(param_config)
        assert parameter_metadata is type(adapted_parameter)


@pytest.mark.parametrize(
    "ert_distribution_class", get_args(get_args(DistributionSettings)[0])
)
def test_parameter_config_to_parameter_metadata(
    ert_distribution_class: DistributionSettings,
) -> None:
    """All current Ert parameter configs can be adapted to parameter metadata."""
    ert_distribution = ert_distribution_class()
    ert_param_config = GenKwConfig(name="test", distribution=ert_distribution)
    param_metadata = parameter_config_to_parameter_metadata(ert_param_config)

    assert param_metadata.group == "DEFAULT"
    assert param_metadata.input_source == "sampled"
    assert param_metadata.distribution == ert_param_config.distribution.name
    # Distribution fields tested in next test


def test_distribution_models_one_to_one_with_ert() -> None:
    """All fmu-datamodels parameter distributions models match Ert.

    This ensures that dataio will use distribution types in both fmu-datamodels and
    ert that have the same distributions (normal, lognormal, ...), and the same
    properties of those distributions (min, max, std dev, ...)."""

    ert_types = get_args(get_args(DistributionSettings)[0])
    datamodels_types = get_args(get_args(ParameterMetadata)[0])

    def get_name(cls: DistributionSettings | ParameterMetadata) -> str:
        for field in ("name", "distribution"):
            if field in cls.model_fields:
                return get_args(cls.model_fields[field].annotation)[0]
        raise ValueError("No 'name' or 'distribution' field")

    def get_params(cls: DistributionSettings | ParameterMetadata) -> set[str]:
        excluded = {"name", "distribution", "group", "input_source"}
        return {k for k in cls.model_fields if k not in excluded}

    ert_models = {get_name(t): get_params(t) for t in ert_types}
    datamodels_models = {get_name(t): get_params(t) for t in datamodels_types}

    assert ert_models == datamodels_models
