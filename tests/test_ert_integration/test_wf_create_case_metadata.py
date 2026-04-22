from __future__ import annotations

import getpass
import importlib
import json
import os
import pathlib
from pathlib import Path
from typing import TYPE_CHECKING, get_args
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import ert.__main__
import jsonschema
import polars as pl
import pyarrow as pa
import pytest
import yaml
from ert.config import GenKwConfig
from ert.config.distribution import DistributionSettings
from ert.config.ert_config import create_observation_dataframes
from fmu.datamodels import (
    ErtObservationsRftSchema,
)
from fmu.datamodels.standard_results.ert_parameters import (
    ConstParameter,
    ErtParameterMetadata,
    LogUnifParameter,
    RawParameter,
    UniformParameter,
)
from fmu.settings import get_fmu_directory
from pytest import CaptureFixture, MonkeyPatch

from fmu.dataio._interfaces import SumoUploaderInterface
from fmu.dataio._workflows.case._observations import get_ert_observations_table
from fmu.dataio._workflows.case._parameters import (
    ErtParameterMetadataAdapter,
    _genkw_to_metadata,
    get_ert_parameters_table,
)
from fmu.dataio._workflows.case.main import CaseWorkflowConfig

from .ert_config_utils import (
    add_create_case_workflow,
    add_design_matrix,
    add_globvar_parameters,
    add_multregt_parameters,
    add_observation_config,
    add_rft_observations,
)

if TYPE_CHECKING:
    from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration


@pytest.fixture
def mock_ert_ensemble() -> MagicMock:
    """Create a mock Ert esnemble with scalar parameters."""
    ensemble = MagicMock()
    ensemble.name = "iter-0"
    ensemble.id = uuid4()

    scalars_df = pl.DataFrame(
        {
            "realization": [0, 1, 2],
            "PARAM_GROUP:param_a": [1.0, 2.0, 3.0],
            "PARAM_GROUP:param_b": [4.0, 5.0, 6.0],
            "DESIGN_MATRIX:param_c": [1640, 1640, 1640],
            "DESIGN_MATRIX:string_param": ["a", "b", "c"],
        }
    )
    ensemble.load_scalars.return_value = scalars_df

    mock_config = MagicMock(spec=GenKwConfig)
    mock_config.group = "PARAM_GROUP"
    mock_config.input_source = "sampled"
    mock_config.distribution = MagicMock()
    mock_config.distribution.name = "normal"
    mock_config.distribution.model_dump.return_value = {"mean": 0.0, "std": 1.0}

    mock_design = MagicMock(spec=GenKwConfig)
    mock_design.group = "DESIGN_MATRIX"
    mock_design.input_source = "design_matrix"
    mock_design.distribution = MagicMock()
    mock_design.distribution.name = "raw"

    ensemble.experiment.parameter_configuration = {
        "param_a": mock_config,
        "param_b": mock_config,
        "param_c": mock_design,
        "string_param": mock_design,
    }

    return ensemble


@pytest.fixture
def mock_ert_runpaths(runpath_prehook: Path) -> MagicMock:
    """Create a mock Ert Runpaths object."""
    runpaths = MagicMock()
    runpaths.get_paths.return_value = [str(runpath_prehook / "realization-0/iter-0")]
    return runpaths


@pytest.fixture
def mock_ert_pred_runpaths(runpath_prehook: Path) -> MagicMock:
    """Create a mock Ert Runpaths object for a pred run."""
    runpaths = MagicMock()
    runpaths.get_paths.return_value = [str(runpath_prehook / "realization-0/pred-dg3")]
    return runpaths


@pytest.fixture
def workflow_config(
    runpath_prehook: Path,
    mock_global_config_validated: GlobalConfiguration,
) -> CaseWorkflowConfig:
    """Create a mock CaseWorkflowConfig."""
    return CaseWorkflowConfig(
        casepath=runpath_prehook,
        ert_config_path=Path("../../ert/model/"),
        register_on_sumo=True,
        verbosity="WARNING",
        global_config=mock_global_config_validated,
        global_config_path=Path("../../fmuconfig/output/global_variables.yml"),
        fmu_dir=get_fmu_directory(runpath_prehook),
    )


def parse_field_metadata(field: pa.Field) -> ErtParameterMetadata:
    """Decode and parse metadata from a PyArrow field."""
    assert field.metadata is not None, f"Field {field.name} has no metadata"
    decoded = {
        k.decode("utf-8"): json.loads(v.decode("utf-8"))
        for k, v in field.metadata.items()
    }
    return ErtParameterMetadataAdapter.validate_python(decoded)


def test_create_case_metadata_runs_successfully(
    fmu_snakeoil_project: Path, monkeypatch: MonkeyPatch
) -> None:
    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    with patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]):
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


def test_create_case_metadata_uses_dotfmu_config(
    fmu_snakeoil_project_with_dotfmu: Path, monkeypatch: MonkeyPatch
) -> None:
    """When .fmu/ exists, case metadata model is sourced from .fmu/ not yml."""
    ert_model_path = fmu_snakeoil_project_with_dotfmu / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    with patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]):
        ert.__main__.main()

    fmu_case_yml = (
        fmu_snakeoil_project_with_dotfmu
        / "scratch/user/snakeoil/share/metadata/fmu_case.yml"
    )
    assert fmu_case_yml.exists()

    with open(fmu_case_yml, encoding="utf-8") as f:
        fmu_case = yaml.safe_load(f)

    # .fmu has model.name="Drogon", global_variables.yml has "global_variables"
    assert fmu_case["fmu"]["model"]["name"] == "Drogon"


def test_create_case_metadata_warns_without_overwriting(
    fmu_snakeoil_project: Path, monkeypatch: MonkeyPatch
) -> None:
    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    share_metadata = fmu_snakeoil_project / "scratch/user/snakeoil/share/metadata"
    fmu_case_yml = share_metadata / "fmu_case.yml"

    with patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]):
        ert.__main__.main()

    assert fmu_case_yml.exists()
    with open(fmu_case_yml, encoding="utf-8") as f:
        first_run = yaml.safe_load(f)

    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        pytest.warns(UserWarning, match="Using existing case metadata from casepath:"),
    ):
        ert.__main__.main()

    ls_share_metadata = os.listdir(share_metadata)
    assert ls_share_metadata == ["fmu_case.yml"]

    with open(fmu_case_yml, encoding="utf-8") as f:
        second_run = yaml.safe_load(f)

    assert first_run == second_run


def test_create_case_metadata_caseroot_not_defined(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    """Test that a proper error message is given if the case path is
    input as an undefined ERT variable"""
    pathlib.Path(
        fmu_snakeoil_project / "ert/bin/workflows/xhook_create_case_metadata"
    ).write_text(
        "WF_CREATE_CASE_METADATA <CASEPATH_NOT_DEFINED>",
        encoding="utf-8",
    )

    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    with patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]):
        ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: Ert variable for case path is not defined" in stderr


def test_create_case_metadata_deprecated_arguments_warn(
    fmu_snakeoil_project: Path, monkeypatch: MonkeyPatch
) -> None:
    """Now deprecated arguments issue warnings."""
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

    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        pytest.warns(
            FutureWarning, match="The argument 'ert_config_path' is deprecated"
        ),
        pytest.warns(FutureWarning, match="The argument 'ert_casename' is deprecated"),
    ):
        ert.__main__.main()


@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_enable_mocked_sumo(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
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

    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        pytest.warns(FutureWarning, match="'--sumo_env' is deprecated"),
    ):
        ert.__main__.main()

    # Verifies case.register() was run
    with open("sumo_case_id", encoding="utf-8") as f:
        assert f.read() == "1"


@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_dev_input_fails(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
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

    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        pytest.warns(FutureWarning, match="'--sumo_env' is deprecated"),
    ):
        ert.__main__.main()

    _stdout, stderr = capsys.readouterr()
    assert "ValueError: Setting sumo environment through argument" in stderr
    assert "SUMO_ENV" in stderr


@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_reads_from_environment(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
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

    with patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]):
        ert.__main__.main()

    mock_sumo_uploader["SumoConnection"].assert_called()
    assert mock_sumo_uploader["SumoConnection"].call_args.args == ((sumo_env,))
    assert "client_id" in mock_sumo_uploader["SumoConnection"].call_args.kwargs


@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_defaults_to_prod(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
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

    with patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]):
        ert.__main__.main()

    # should default to prod when not set
    mock_sumo_uploader["SumoConnection"].assert_called()
    assert mock_sumo_uploader["SumoConnection"].call_args.args == (("prod",))
    assert "client_id" in mock_sumo_uploader["SumoConnection"].call_args.kwargs


@pytest.mark.skipif(
    not importlib.util.find_spec("fmu.sumo.uploader"),
    reason="fmu-sumo-uploader is not installed",
)
def test_create_case_metadata_sumo_env_input_is_ignored(
    fmu_snakeoil_project: Path,
    monkeypatch: MonkeyPatch,
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

    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        pytest.warns(FutureWarning, match="'--sumo_env' is deprecated"),
    ):
        ert.__main__.main()

    mock_sumo_uploader["SumoConnection"].assert_called()
    assert mock_sumo_uploader["SumoConnection"].call_args.args == ((sumo_env_expected,))
    assert "client_id" in mock_sumo_uploader["SumoConnection"].call_args.kwargs


def test_create_case_metadata_collects_ert_parameters_as_expected(
    fmu_snakeoil_project_sumo: Path, monkeypatch: MonkeyPatch
) -> None:
    ert_model_path = fmu_snakeoil_project_sumo / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_design_matrix(ert_config_path)
    add_globvar_parameters(ert_config_path)
    add_multregt_parameters(ert_config_path)

    add_create_case_workflow(ert_config_path)

    scalars_and_config = []

    def capture_params(
        ensemble: ert.Ensemble,
        ensemble_name: str,
        workflow_config: CaseWorkflowConfig,
        sumo_uploader: SumoUploaderInterface,
    ) -> None:
        """Captures params from Ert run.

        Requires the Ert runtime context to load from local storage."""
        scalars_and_config.append(ensemble.load_scalars())
        scalars_and_config.append(ensemble.experiment.parameter_configuration)

    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        patch(
            "fmu.dataio._workflows.case.main.SumoUploaderInterface",
            spec=SumoUploaderInterface,
        ),
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_parameters",
            side_effect=capture_params,
        ),
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
        parameter_metadata: type[ErtParameterMetadata] | None = None
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

        adapted_parameter = _genkw_to_metadata(param_config)
        assert parameter_metadata is type(adapted_parameter)


@pytest.mark.parametrize(
    "ert_distribution_class", get_args(get_args(DistributionSettings)[0])
)
def test_genkw_to_metadata(
    ert_distribution_class: DistributionSettings,
) -> None:
    """All current Ert parameter configs can be adapted to parameter metadata."""
    ert_distribution = ert_distribution_class()
    ert_param_config = GenKwConfig(name="test", distribution=ert_distribution)
    param_metadata = _genkw_to_metadata(ert_param_config)

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
    datamodels_types = get_args(get_args(ErtParameterMetadata)[0])

    def get_name(cls: DistributionSettings | ErtParameterMetadata) -> str:
        for field in ("name", "distribution"):
            if field in cls.model_fields:
                return get_args(cls.model_fields[field].annotation)[0]
        raise ValueError("No 'name' or 'distribution' field")

    def get_params(cls: DistributionSettings | ErtParameterMetadata) -> set[str]:
        excluded = {"name", "distribution", "group", "input_source"}
        return {k for k in cls.model_fields if k not in excluded}

    ert_models = {get_name(t): get_params(t) for t in ert_types}
    datamodels_models = {get_name(t): get_params(t) for t in datamodels_types}

    assert ert_models == datamodels_models


def test_get_ert_parameters_table(mock_ert_ensemble: MagicMock) -> None:
    """Ert parameters table returned as expected."""
    table = get_ert_parameters_table(ensemble=mock_ert_ensemble)
    assert isinstance(table, pa.Table)
    assert len(table) == 3


def test_get_ert_parameters_table_empty_scalars() -> None:
    """Empty scalars returns None."""
    ensemble = MagicMock()
    ensemble.load_scalars.return_value = pl.DataFrame()

    table = get_ert_parameters_table(ensemble=ensemble)
    assert table is None


def test_get_ert_parameters_table_subset_realizations(
    mock_ert_ensemble: MagicMock,
) -> None:
    """Export with only a subset of realizations."""
    scalars_df = pl.DataFrame(
        {
            "realization": [1, 3],
            "PARAM_GROUP:param_a": [2.0, 4.0],
            "PARAM_GROUP:param_b": [5.0, 7.0],
            "DESIGN_MATRIX:param_c": [1640, 1640],
        }
    )
    mock_ert_ensemble.load_scalars.return_value = scalars_df

    table = get_ert_parameters_table(ensemble=mock_ert_ensemble)

    assert table is not None
    assert table.column("REAL").to_pylist() == [1, 3]


def test_get_ert_parameters_table_schema_columns(mock_ert_ensemble: MagicMock) -> None:
    """Exported parquet has expected columns with correct types."""
    table = get_ert_parameters_table(ensemble=mock_ert_ensemble)

    assert table is not None
    schema = table.schema

    assert schema.field("REAL").type == pa.int32()
    assert schema.field("param_a").type == pa.float64()
    assert schema.field("param_b").type == pa.float64()
    assert schema.field("param_c").type == pa.int64()
    assert schema.field("string_param").type == pa.string()

    assert len(schema.names) == 5


def test_get_ert_parameters_table_missing_config() -> None:
    """Parameters without config in parameter_configuration are skipped."""
    ensemble = MagicMock()
    ensemble.name = "iter-0"
    ensemble.id = uuid4()

    scalars_df = pl.DataFrame(
        {
            "realization": [0],
            "UNKNOWN:unknown_param": [1.0],
        }
    )
    ensemble.load_scalars.return_value = scalars_df
    ensemble.experiment.parameter_configuration = {}  # Empty config

    table = get_ert_parameters_table(ensemble=ensemble)

    assert table is not None
    assert table.schema.names == ["REAL"]


def test_get_ert_parameters_table_non_genkw_config_skipped() -> None:
    """Non-GenKwConfig parameters are skipped."""
    ensemble = MagicMock()
    ensemble.name = "iter-0"
    ensemble.id = uuid4()

    scalars_df = pl.DataFrame(
        {
            "realization": [0],
            "GROUP:some_param": [1.0],
        }
    )
    ensemble.load_scalars.return_value = scalars_df

    ensemble.experiment.parameter_configuration = {
        "some_param": MagicMock(spec=[])  # Not a GenKwConfig
    }

    table = get_ert_parameters_table(ensemble=ensemble)

    assert table is not None
    assert table.schema.names == ["REAL"]


def test_create_case_metadata_expects_parameters_standard_result_integration(
    fmu_snakeoil_project_sumo: Path, monkeypatch: MonkeyPatch
) -> None:
    """Full integration test with the snakeoil Ert model."""
    ert_model_path = fmu_snakeoil_project_sumo / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_design_matrix(ert_config_path)
    add_globvar_parameters(ert_config_path)
    add_multregt_parameters(ert_config_path)
    add_create_case_workflow(ert_config_path)

    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        patch(
            "fmu.dataio._workflows.case.main.SumoUploaderInterface",
            spec=SumoUploaderInterface,
        ) as mock_uploader_interface,
    ):
        ert.__main__.main()

        from_new_case = mock_uploader_interface.from_new_case
        from_new_case.assert_called_once()
        from_new_case.return_value.queue_table.assert_called_once()

        parameters_table, parameters_metadata = (
            from_new_case.return_value.queue_table.call_args.args
        )

    assert parameters_table.column("REAL")[0].as_py() == 0
    assert parameters_table.column("globvar_a")[0].as_py() == pytest.approx(
        0.6725254375492808
    )

    expected_design_values = {
        "design_a": 1.0,
        "design_b": 4.0,
        "design_c": 7.0,
    }
    for name, expected_value in expected_design_values.items():
        assert parameters_table.column(f"{name}")[0].as_py() == expected_value

    schema = parameters_table.schema

    globvar_a_meta = parse_field_metadata(schema.field("globvar_a"))
    assert globvar_a_meta.group == "GLOBVAR"
    assert globvar_a_meta.input_source == "sampled"
    assert globvar_a_meta.distribution == "logunif"

    design_a_meta = parse_field_metadata(schema.field("design_a"))
    assert design_a_meta.group == "DESIGN_MATRIX"
    assert design_a_meta.input_source == "design_matrix"
    assert design_a_meta.distribution == "raw"

    globvar_b_meta = parse_field_metadata(schema.field("globvar_b"))
    assert globvar_b_meta.distribution == "uniform"
    assert hasattr(globvar_b_meta, "min")
    assert hasattr(globvar_b_meta, "max")

    globvar_c_meta = parse_field_metadata(schema.field("globvar_c"))
    assert isinstance(globvar_c_meta, ConstParameter)
    assert globvar_c_meta.distribution == "const"
    assert globvar_c_meta.value == 1050.0

    multregt_a_meta = parse_field_metadata(schema.field("multregt_a"))
    assert multregt_a_meta.group == "MULTREGT"
    assert multregt_a_meta.distribution == "logunif"

    assert parameters_metadata["data"]["content"] == "parameters"
    assert parameters_metadata["data"]["standard_result"]["name"] == "parameters"
    assert parameters_metadata["data"]["table_index"] == ["REAL"]
    assert "fmu" in parameters_metadata
    assert parameters_metadata["fmu"]["context"]["stage"] == "ensemble"
    assert parameters_metadata["fmu"]["ensemble"] is not None
    assert parameters_metadata["fmu"]["ensemble"]["name"] == "iter-0"

    assert parameters_metadata["access"]["classification"] == "internal"


# Running a full integration test with observations is tricky due
# to ERT config validations. It requires the presence of a forward_model
# that can produce a response i.e. a flow simulation. With some mocking
# it was possible to run it fully for rft, but summary observations was not.


def test_create_case_metadata_collects_rft_observations_as_expected(
    fmu_snakeoil_project_sumo: Path, monkeypatch: MonkeyPatch
) -> None:
    """
    Test rft observations are fetched and returned as expected from ert
    and tried uploaded to Sumo.
    """
    ert_model_path = fmu_snakeoil_project_sumo / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_observation_config(ert_config_path)
    add_rft_observations(ert_config_path)

    add_create_case_workflow(ert_config_path)

    captured_tables = {}

    def capture_observation_tables(
        ensemble: ert.Ensemble,
        obs_type: str,
    ) -> None:
        """Captures observation tables from Ert run.

        Requires the Ert runtime context to load from local storage."""
        df = get_ert_observations_table(ensemble, obs_type)
        captured_tables[obs_type] = df
        return df

    def mock_create_observation_dataframes(
        observations: ert.Ensemble,
        rft_config: None,
    ) -> None:
        """mock"""
        return create_observation_dataframes(observations, MagicMock())

    with (
        patch(
            "ert.storage.local_experiment.create_observation_dataframes",
            side_effect=mock_create_observation_dataframes,
        ),
        patch(
            "ert.config.ert_config.create_observation_dataframes",
            side_effect=mock_create_observation_dataframes,
        ),
        patch(
            "fmu.dataio._workflows.case.main.SumoUploaderInterface",
            spec=SumoUploaderInterface,
        ) as mock_uploader_interface,
        patch(
            "fmu.dataio._workflows.case.main.get_ert_observations_table",
            side_effect=capture_observation_tables,
        ),
        patch(
            "sys.argv",
            ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
        ),
    ):
        ert.__main__.main()

        from_new_case = mock_uploader_interface.from_new_case
        from_new_case.assert_called_once()
        # only rft table should be queued, summary should be None and not queued
        from_new_case.return_value.queue_table.assert_called_once()

    assert len(captured_tables) == 2

    assert captured_tables["summary"] is None
    assert captured_tables["rft"] is not None

    table = captured_tables["rft"]

    assert isinstance(table, pa.Table)
    assert table.num_rows == 1

    jsonschema.validate(
        instance=table.to_pylist(), schema=ErtObservationsRftSchema.dump()
    )  # Throws if invalid


def test_create_case_metadata_with_no_observations(
    fmu_snakeoil_project_sumo: Path, monkeypatch: MonkeyPatch
) -> None:
    """Test no tables are uploaded when observations are not present in ert config"""
    ert_model_path = fmu_snakeoil_project_sumo / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"

    add_create_case_workflow(ert_config_path)

    captured_tables = {}

    def capture_observation_tables(
        ensemble: ert.Ensemble,
        obs_type: str,
    ) -> None:
        """Captures rft observations from Ert run"""
        df = get_ert_observations_table(ensemble, obs_type)
        captured_tables[obs_type] = df
        return df

    with (
        patch(
            "fmu.dataio._workflows.case.main.SumoUploaderInterface",
            spec=SumoUploaderInterface,
        ) as mock_uploader_interface,
        patch(
            "fmu.dataio._workflows.case.main.get_ert_observations_table",
            side_effect=capture_observation_tables,
        ),
        patch(
            "sys.argv",
            ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"],
        ),
    ):
        ert.__main__.main()

        from_new_case = mock_uploader_interface.from_new_case
        from_new_case.assert_called_once()
        # no tables should be queued
        from_new_case.return_value.queue_table.assert_not_called()

    assert len(captured_tables) == 2

    assert captured_tables["summary"] is None
    assert captured_tables["rft"] is None
