import argparse
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest
from ert.substitutions import Substitutions
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.settings import get_fmu_directory
from fmu.settings._drogon import create_drogon_fmu_dir
from pytest import MonkeyPatch

from fmu.dataio._workflows.case.main import (
    CaseWorkflowConfig,
    _copy_fmu_directory,
    _get_ensemble_name,
    _queue_ert_parameters,
    _queue_stratigraphy_mappings,
    _queue_wellbore_mappings,
    _resolve_casepath,
    _upload_files_to_sumo,
)


@pytest.fixture
def mock_ensemble() -> Callable[[int], MagicMock]:
    """Mocks an ert.storage.Ensemble object."""

    def _mock_ensemble(iteration: int = 0) -> MagicMock:
        """Creates the mocked object."""
        ensemble = MagicMock()
        ensemble.iteration = 0
        return ensemble

    return _mock_ensemble


@pytest.fixture
def mock_run_paths() -> Callable[[str], MagicMock]:
    """Mocks and ert.runpaths.Runpaths object."""

    def _mock_run_paths(runpath: str = "/tmp/realization-0/iter-0") -> MagicMock:
        """Creates the mocked object."""
        run_paths = MagicMock()
        run_paths.get_paths.return_value = [runpath]
        return run_paths

    return _mock_run_paths


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


def test_get_ensemble_name_returns_runpath_leaf_when_inside_casepath(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[str], MagicMock],
) -> None:
    """Runpath that is a subdirectory of casepath uses the dir name."""
    casepath = tmp_path / "scratch/user/snakeoil"
    runpath = casepath / "realization-0/iter-0"

    ensemble = mock_ensemble()
    run_paths = mock_run_paths(str(runpath))

    name = _get_ensemble_name(ensemble, run_paths, casepath)

    assert name == "iter-0"


def test_get_ensemble_name_returns_iter0_fallback_when_runpath_equals_casepath(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[str], MagicMock],
) -> None:
    """Runpath whose parent is the casepath falls back to iter-0."""
    casepath = tmp_path / "scratch/user/snakeoil"
    runpath = casepath / "realization-0"

    ensemble = mock_ensemble()
    run_paths = mock_run_paths(str(runpath))

    name = _get_ensemble_name(ensemble, run_paths, casepath)

    assert name == "iter-0"


def test_get_ensemble_name_pred_run(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[str], MagicMock],
) -> None:
    """A prediction run uses the actual directory name."""
    casepath = tmp_path / "scratch/user/snakeoil"
    runpath = casepath / "realization-0/pred-dg3"

    ensemble = mock_ensemble()
    run_paths = mock_run_paths(str(runpath))

    name = _get_ensemble_name(ensemble, run_paths, casepath)

    assert name == "pred-dg3"


def test_queue_ert_parameters_does_nothing_when_table_is_none(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[], MagicMock],
    workflow_config: CaseWorkflowConfig,
) -> None:
    """When get_ert_parameters_table returns None queue_table must not be called.

    This shouldn't happen (Ert should have parameters), but in theory is possible.
    """
    ensemble = mock_ensemble()
    run_paths = mock_run_paths()
    sumo_uploader = MagicMock()

    with patch(
        "fmu.dataio._workflows.case.main.get_ert_parameters_table",
        return_value=None,
    ):
        _queue_ert_parameters(ensemble, run_paths, workflow_config, sumo_uploader)

    sumo_uploader.queue_table.assert_not_called()


def test_queue_ert_parameters_queue_table_when_present(
    tmp_path: Path,
    mock_ensemble: Callable[[], MagicMock],
    mock_run_paths: Callable[[str], MagicMock],
    workflow_config: CaseWorkflowConfig,
) -> None:
    """When a table is returned it should be queued with generated metadata."""

    ensemble = mock_ensemble()
    run_paths = mock_run_paths(str(tmp_path / "realization-0/iter-0"))
    sumo_uploader = MagicMock()

    fake_table = pa.table({"REAL": [0]})
    fake_metadata = {"data": {"content": "parameters"}}

    with (
        patch(
            "fmu.dataio._workflows.case.main.get_ert_parameters_table",
            return_value=fake_table,
        ),
        patch(
            "fmu.dataio._workflows.case.main.generate_metadata",
            return_value=fake_metadata,
        ),
    ):
        _queue_ert_parameters(ensemble, run_paths, workflow_config, sumo_uploader)

    sumo_uploader.queue_table.assert_called_once_with(fake_table, fake_metadata)


def test_queue_stratigraphy_mappings_does_nothing_when_table_is_none(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """
    When get_stratigraphy_mappings_table returns None queue_table
    must not be called.
    """
    sumo_uploader = MagicMock()

    with patch(
        "fmu.dataio._workflows.case.main.get_stratigraphy_mappings_table",
        return_value=None,
    ):
        _queue_stratigraphy_mappings("ensemble", workflow_config, sumo_uploader)

    sumo_uploader.queue_table.assert_not_called()


def test_queue_stratigraphy_mappings_queue_table_when_present(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """When a table is returned it should be queued with generated metadata."""

    sumo_uploader = MagicMock()

    fake_table = pa.table({"column": ["value"]})
    fake_metadata = {"data": {"content": "mapping"}}

    with (
        patch(
            "fmu.dataio._workflows.case.main.get_stratigraphy_mappings_table",
            return_value=fake_table,
        ),
        patch(
            "fmu.dataio._workflows.case.main.generate_metadata",
            return_value=fake_metadata,
        ) as generate_metadata,
    ):
        _queue_stratigraphy_mappings("ensemble", workflow_config, sumo_uploader)

    export_config = generate_metadata.call_args.args[0]
    assert export_config.is_observation is False
    sumo_uploader.queue_table.assert_called_once_with(fake_table, fake_metadata)


def test_upload_files_to_sumo_queues_stratigraphy_when_fmu_dir_present(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """With fmu_dir present, all queues including stratigraphy are called."""
    ensemble_name = "ens"
    ensemble = MagicMock()
    run_paths = MagicMock()
    sumo_uploader = MagicMock()

    assert workflow_config.fmu_dir is not None

    with (
        patch(
            "fmu.dataio._workflows.case.main._get_ensemble_name",
            return_value=ensemble_name,
        ),
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_parameters"
        ) as queue_parameters,
        patch(
            "fmu.dataio._workflows.case.main._queue_stratigraphy_mappings"
        ) as queue_stratigraphy,
    ):
        _upload_files_to_sumo(ensemble, run_paths, workflow_config, sumo_uploader)

    queue_stratigraphy.assert_called_once_with(
        ensemble_name, workflow_config, sumo_uploader
    )
    queue_parameters.assert_called_once_with(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    sumo_uploader.upload.assert_called_once_with()


def test_upload_files_to_sumo_skips_stratigraphy_when_fmu_dir_missing(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """With no fmu_dir, stratigraphy mappings are not queued."""
    ensemble_name = "ens"
    ensemble = MagicMock()
    run_paths = MagicMock()
    sumo_uploader = MagicMock()

    # set fmu_dir to None to simulate missing .fmu directory
    workflow_config_without_fmu = replace(workflow_config, fmu_dir=None)

    with (
        patch(
            "fmu.dataio._workflows.case.main._get_ensemble_name",
            return_value=ensemble_name,
        ),
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_parameters"
        ) as queue_parameters,
        patch(
            "fmu.dataio._workflows.case.main._queue_stratigraphy_mappings"
        ) as queue_stratigraphy,
    ):
        _upload_files_to_sumo(
            ensemble, run_paths, workflow_config_without_fmu, sumo_uploader
        )

    queue_stratigraphy.assert_not_called()
    queue_parameters.assert_called_once_with(
        ensemble, ensemble_name, workflow_config_without_fmu, sumo_uploader
    )
    sumo_uploader.upload.assert_called_once_with()


def test_queue_wellbore_mappings_does_nothing_when_table_is_none(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """
    When get_wellbore_mappings_table returns None queue_table
    must not be called.
    """
    sumo_uploader = MagicMock()

    with patch(
        "fmu.dataio._workflows.case.main.get_wellbore_mappings_table",
        return_value=None,
    ):
        _queue_wellbore_mappings("ensemble", workflow_config, sumo_uploader)

    sumo_uploader.queue_table.assert_not_called()


def test_queue_wellbore_mappings_queue_table_when_present(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """When a table is returned it should be queued with generated metadata."""

    sumo_uploader = MagicMock()

    fake_table = pa.table({"column": ["value"]})
    fake_metadata = {"data": {"content": "mapping"}}

    with (
        patch(
            "fmu.dataio._workflows.case.main.get_wellbore_mappings_table",
            return_value=fake_table,
        ),
        patch(
            "fmu.dataio._workflows.case.main.generate_metadata",
            return_value=fake_metadata,
        ) as generate_metadata,
    ):
        _queue_wellbore_mappings("ensemble", workflow_config, sumo_uploader)

    export_config = generate_metadata.call_args.args[0]
    assert export_config.is_observation is False
    sumo_uploader.queue_table.assert_called_once_with(fake_table, fake_metadata)


def test_upload_files_to_sumo_queues_wellbore_when_fmu_dir_present(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """With fmu_dir present, all queues including wellbore are called."""
    ensemble_name = "ens"
    ensemble = MagicMock()
    run_paths = MagicMock()
    sumo_uploader = MagicMock()

    assert workflow_config.fmu_dir is not None

    with (
        patch(
            "fmu.dataio._workflows.case.main._get_ensemble_name",
            return_value=ensemble_name,
        ),
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_parameters"
        ) as queue_parameters,
        patch(
            "fmu.dataio._workflows.case.main._queue_wellbore_mappings"
        ) as queue_wellbore,
    ):
        _upload_files_to_sumo(ensemble, run_paths, workflow_config, sumo_uploader)

    queue_wellbore.assert_called_once_with(
        ensemble_name, workflow_config, sumo_uploader
    )
    queue_parameters.assert_called_once_with(
        ensemble, ensemble_name, workflow_config, sumo_uploader
    )
    sumo_uploader.upload.assert_called_once_with()


def test_upload_files_to_sumo_skips_wellbore_when_fmu_dir_missing(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """With no fmu_dir, wellbore mappings are not queued."""
    ensemble_name = "ens"
    ensemble = MagicMock()
    run_paths = MagicMock()
    sumo_uploader = MagicMock()

    # set fmu_dir to None to simulate missing .fmu directory
    workflow_config_without_fmu = replace(workflow_config, fmu_dir=None)

    with (
        patch(
            "fmu.dataio._workflows.case.main._get_ensemble_name",
            return_value=ensemble_name,
        ),
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_parameters"
        ) as queue_parameters,
        patch(
            "fmu.dataio._workflows.case.main._queue_wellbore_mappings"
        ) as queue_wellbore,
    ):
        _upload_files_to_sumo(
            ensemble, run_paths, workflow_config_without_fmu, sumo_uploader
        )

    queue_wellbore.assert_not_called()
    queue_parameters.assert_called_once_with(
        ensemble, ensemble_name, workflow_config_without_fmu, sumo_uploader
    )
    sumo_uploader.upload.assert_called_once_with()


def test_copy_fmu_directory_no_dot_fmu(tmp_path: Path) -> None:
    """None is returned when no .fmu/ exists."""
    assert _copy_fmu_directory(tmp_path) is None


def test_copy_fmu_directory_with_fmu(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Source .fmu/ is copied to destination .fmu/ and returned."""
    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()

    monkeypatch.chdir(src)

    src_fmu_dir = create_drogon_fmu_dir(src)
    assert src_fmu_dir.path.parent == src

    dest_fmu_dir = _copy_fmu_directory(dest)
    assert dest_fmu_dir is not None
    assert dest_fmu_dir.path.parent == dest
    assert (dest / ".fmu").is_dir()


def test_copy_fmu_directory_with_fmu_already_exists(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Source .fmu/ is copied to destination where .fmu/ already exists."""
    src = tmp_path / "src"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()

    monkeypatch.chdir(src)

    src_fmu_dir = create_drogon_fmu_dir(src)
    assert src_fmu_dir.path.parent == src

    dest_fmu_dir = create_drogon_fmu_dir(dest)

    new_dest_fmu_dir = _copy_fmu_directory(dest)
    assert new_dest_fmu_dir is not None
    assert new_dest_fmu_dir.path.parent == dest
    assert (dest / ".fmu").is_dir()

    assert dest_fmu_dir.config.load() != new_dest_fmu_dir.config.load()
    assert src_fmu_dir.config.load() == new_dest_fmu_dir.config.load()


def test_resolve_casepath_uses_sumo_casepath_when_defined() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = Substitutions(
        {"<SUMO_CASEPATH>": "/tmp/scratch/user/case"}
    )

    assert _resolve_casepath(
        run_paths, argparse.Namespace(casepath=None, sumo=False)
    ) == Path("/tmp/scratch/user/case")


def test_resolve_casepath_warns_when_legacy_casepath_is_provided() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = Substitutions(
        {"<SUMO_CASEPATH>": "/tmp/scratch/user/case"}
    )

    with pytest.warns(FutureWarning, match="The argument 'casepath' is deprecated"):
        resolved = _resolve_casepath(
            run_paths, argparse.Namespace(casepath="/tmp/legacy/case", sumo=False)
        )

    assert resolved == Path("/tmp/scratch/user/case")


def test_resolve_casepath_uses_legacy_casepath_when_allowed() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = Substitutions({})  # missing <SUMO_CASEPATH>

    assert _resolve_casepath(
        run_paths, argparse.Namespace(casepath="/tmp/legacy/case", sumo=False)
    ) == Path("/tmp/legacy/case")


def test_resolve_casepath_raises_when_sumo_required_but_missing() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = Substitutions({})  # missing <SUMO_CASEPATH>

    with pytest.raises(ValueError, match="Missing required <SUMO_CASEPATH> definition"):
        _resolve_casepath(
            run_paths, argparse.Namespace(casepath="/tmp/legacy/case", sumo=True)
        )


def test_resolve_casepath_raises_when_no_casepath_is_available() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = Substitutions({})  # missing <SUMO_CASEPATH>

    with pytest.raises(ValueError, match="The case path could not be resolved"):
        _resolve_casepath(run_paths, argparse.Namespace(casepath=None, sumo=False))


def test_resolve_casepath_resolves_nested_substitutions_regardless_of_order() -> None:
    run_paths = MagicMock()
    run_paths.substitutions = Substitutions(
        {
            "<SUMO_CASEPATH>": "<SCRATCH>/<USER>/case",
            "<SCRATCH>": "/tmp/scratch",
            "<USER>": "user",
        }
    )

    assert _resolve_casepath(
        run_paths, argparse.Namespace(casepath=None, sumo=False)
    ) == Path("/tmp/scratch/user/case")


def test_workflow_config_resolves_nested_config_path(
    mock_global_config_validated: GlobalConfiguration,
) -> None:
    run_paths = MagicMock()
    run_paths.substitutions = Substitutions(
        {"<CONFIG_PATH>": "<PROJECT_PATH>/ert/model", "<PROJECT_PATH>": "/tmp/project"}
    )
    args = argparse.Namespace(
        casepath=None,
        sumo=False,
        ert_config_path=None,
        ert_casename=None,
        ert_username=None,
        global_variables_path=None,
        verbosity=None,
        sumo_env=None,
    )

    with patch(
        "fmu.dataio._workflows.case._config.load_global_config",
        return_value=mock_global_config_validated,
    ) as load_global_config:
        config = CaseWorkflowConfig.from_presim_workflow(
            run_paths, args, Path("/tmp/scratch/user/case")
        )

    assert config.ert_config_path == Path("/tmp/project/ert/model")
    load_global_config.assert_called_once_with(
        Path("/tmp/project/ert/model/../../fmuconfig/output/global_variables.yml")
    )
