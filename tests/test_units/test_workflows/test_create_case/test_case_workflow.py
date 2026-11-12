from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.settings import get_fmu_directory

from fmu.dataio._workflows.case._config import CaseWorkflowConfig
from fmu.dataio._workflows.case.main import (
    WfExportCaseMetadata,
    _queue_ert_observations,
    _queue_ert_observations_seismic,
    _run_workflow,
)


@pytest.fixture
def workflow_config(
    runpath_prehook: Path,
    mock_global_config_validated: GlobalConfiguration,
) -> CaseWorkflowConfig:
    """Create a mock legacy case workflow config."""
    return CaseWorkflowConfig(
        casepath=runpath_prehook,
        ert_config_path=Path("../../ert/model/"),
        register_on_sumo=True,
        verbosity="WARNING",
        global_config=mock_global_config_validated,
        fmu_dir=get_fmu_directory(runpath_prehook),
    )


def test_case_workflow_exports_metadata_without_sumo(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """The legacy workflow exports metadata without initializing Sumo by default."""
    workflow_config_without_sumo = replace(workflow_config, register_on_sumo=False)
    ensemble = MagicMock()
    run_paths = MagicMock()
    metadata_path = workflow_config.casepath / "share/metadata/fmu_case.yml"

    with (
        patch("fmu.dataio._workflows.case.main.ExportCaseMetadata") as exporter,
        patch(
            "fmu.dataio._workflows.case.main.SumoUploaderInterface"
        ) as uploader_interface,
        patch("fmu.dataio._workflows.case.main._queue_ert_observations") as queue_obs,
        patch("fmu.dataio._workflows.case.main._upload_files_to_sumo") as upload,
    ):
        exporter.from_workflow_config.return_value.export.return_value = str(
            metadata_path
        )

        _run_workflow(ensemble, run_paths, workflow_config_without_sumo)

    exporter.from_workflow_config.assert_called_once_with(workflow_config_without_sumo)
    uploader_interface.from_new_case.assert_not_called()
    queue_obs.assert_not_called()
    upload.assert_not_called()


def test_case_workflow_queues_observations_then_delegates_sumo_upload(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """With --sumo enabled, the legacy workflow queues observations itself and then
    delegates parameters, .fmu tables and the upload to fmu_pre_sim."""
    ensemble = MagicMock()
    run_paths = MagicMock()
    metadata_path = workflow_config.casepath / "share/metadata/fmu_case.yml"
    sumo_uploader = MagicMock()
    call_order: list[str] = []

    with (
        patch("fmu.dataio._workflows.case.main.ExportCaseMetadata") as exporter,
        patch(
            "fmu.dataio._workflows.case.main.SumoUploaderInterface"
        ) as uploader_interface,
        patch(
            "fmu.dataio._workflows.case.main._get_ensemble_name",
            return_value="iter-0",
        ),
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_observations",
            side_effect=lambda *a, **k: call_order.append("observations"),
        ) as queue_obs,
        patch(
            "fmu.dataio._workflows.case.main._upload_files_to_sumo",
            side_effect=lambda *a, **k: call_order.append("upload"),
        ) as upload,
    ):
        exporter.from_workflow_config.return_value.export.return_value = str(
            metadata_path
        )
        uploader_interface.from_new_case.return_value = sumo_uploader

        _run_workflow(ensemble, run_paths, workflow_config)

    exporter.from_workflow_config.assert_called_once_with(workflow_config)
    uploader_interface.from_new_case.assert_called_once_with(metadata_path)
    queue_obs.assert_called_once_with(
        ensemble, "iter-0", workflow_config, sumo_uploader
    )
    upload.assert_called_once_with(
        ensemble=ensemble,
        run_paths=run_paths,
        workflow_config=workflow_config,
        sumo_uploader=sumo_uploader,
    )
    # Observations must be queued before the shared upload flushes the queue.
    assert call_order == ["observations", "upload"]


def test_queue_ert_observations_queues_all_observation_types(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """All four observation types are queued by the legacy workflow."""
    ensemble = MagicMock()
    sumo_uploader = MagicMock()

    with (
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_observations_rft"
        ) as queue_rft,
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_observations_summary"
        ) as queue_summary,
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_observations_breakthrough"
        ) as queue_breakthrough,
        patch(
            "fmu.dataio._workflows.case.main._queue_ert_observations_seismic"
        ) as queue_seismic,
    ):
        _queue_ert_observations(ensemble, "iter-0", workflow_config, sumo_uploader)

    for queue in (queue_rft, queue_summary, queue_breakthrough, queue_seismic):
        queue.assert_called_once_with(
            ensemble, "iter-0", workflow_config, sumo_uploader
        )


def test_queue_ert_observations_seismic_queues_standard_result(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """Seismic observations are queued with observation standard-result metadata."""
    ensemble = MagicMock()
    sumo_uploader = MagicMock()
    fake_table = pa.table(
        {
            "response_key": ["seismic_amplitude"],
            "observation_value": [0.42],
            "observation_error": [0.05],
            "east": [456000.0],
            "north": [6789000.0],
        }
    )

    with patch(
        "fmu.dataio._workflows.case.main.get_ert_observations_table",
        return_value=fake_table,
    ):
        _queue_ert_observations_seismic(
            ensemble, "iter-0", workflow_config, sumo_uploader
        )

    queued_table, metadata = sumo_uploader.queue_table.call_args.args
    assert queued_table == fake_table
    assert metadata["data"]["is_observation"] is True
    assert metadata["data"]["standard_result"]["name"] == "observations_seismic"
    assert metadata["data"]["table_index"] == ["response_key"]


def test_queue_ert_observations_seismic_does_nothing_when_table_is_none(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """Nothing is queued when Ert has no seismic observations."""
    sumo_uploader = MagicMock()

    with patch(
        "fmu.dataio._workflows.case.main.get_ert_observations_table",
        return_value=None,
    ):
        _queue_ert_observations_seismic(
            MagicMock(), "iter-0", workflow_config, sumo_uploader
        )

    sumo_uploader.queue_table.assert_not_called()


def test_case_workflow_is_deprecated(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """Running WF_CREATE_CASE_METADATA warns and points to WF_FMU_PRE_SIMULATION."""
    ensemble = MagicMock()
    run_paths = MagicMock()

    with (
        patch("fmu.dataio._workflows.case.main.resolve_casepath") as resolve_casepath,
        patch("fmu.dataio._workflows.case.main._copy_fmu_directory"),
        patch(
            "fmu.dataio._workflows.case.main.CaseWorkflowConfig.from_presim_workflow",
            return_value=workflow_config,
        ),
        patch("fmu.dataio._workflows.case.main._run_workflow") as run_workflow,
        pytest.warns(
            FutureWarning,
            match=(
                "WF_CREATE_CASE_METADATA workflow is deprecated.*"
                "Use the WF_FMU_PRE_SIMULATION workflow instead"
            ),
        ),
    ):
        resolve_casepath.return_value = workflow_config.casepath
        WfExportCaseMetadata().run([], ensemble, run_paths)

    run_workflow.assert_called_once_with(ensemble, run_paths, workflow_config)
