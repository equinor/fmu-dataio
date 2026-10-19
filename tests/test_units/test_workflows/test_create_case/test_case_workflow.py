from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fmu.datamodels.fmu_results.global_configuration import GlobalConfiguration
from fmu.settings import get_fmu_directory

from fmu.dataio._workflows.case._config import CaseWorkflowConfig
from fmu.dataio._workflows.case.main import _run_workflow


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
        patch("fmu.dataio._workflows.case.main._upload_files_to_sumo") as upload,
    ):
        exporter.from_workflow_config.return_value.export.return_value = str(
            metadata_path
        )

        _run_workflow(ensemble, run_paths, workflow_config_without_sumo)

    exporter.from_workflow_config.assert_called_once_with(workflow_config_without_sumo)
    uploader_interface.from_new_case.assert_not_called()
    upload.assert_not_called()


def test_case_workflow_delegates_sumo_upload(
    workflow_config: CaseWorkflowConfig,
) -> None:
    """With --sumo enabled, the legacy wrapper delegates upload to fmu_pre_sim."""
    ensemble = MagicMock()
    run_paths = MagicMock()
    metadata_path = workflow_config.casepath / "share/metadata/fmu_case.yml"
    sumo_uploader = MagicMock()

    with (
        patch("fmu.dataio._workflows.case.main.ExportCaseMetadata") as exporter,
        patch(
            "fmu.dataio._workflows.case.main.SumoUploaderInterface"
        ) as uploader_interface,
        patch("fmu.dataio._workflows.case.main._upload_files_to_sumo") as upload,
    ):
        exporter.from_workflow_config.return_value.export.return_value = str(
            metadata_path
        )
        uploader_interface.from_new_case.return_value = sumo_uploader

        _run_workflow(ensemble, run_paths, workflow_config)

    exporter.from_workflow_config.assert_called_once_with(workflow_config)
    uploader_interface.from_new_case.assert_called_once_with(metadata_path)
    upload.assert_called_once_with(
        ensemble=ensemble,
        run_paths=run_paths,
        workflow_config=workflow_config,
        sumo_uploader=sumo_uploader,
    )
