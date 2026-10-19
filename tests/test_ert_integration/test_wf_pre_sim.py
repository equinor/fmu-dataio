from pathlib import Path
from unittest.mock import patch

import ert.__main__
from pytest import MonkeyPatch

from .ert_config_utils import add_fmu_pre_sim_workflow


def test_fmu_pre_simulation_workflow_runs_successfully(
    fmu_snakeoil_project: Path, monkeypatch: MonkeyPatch
) -> None:
    ert_model_path = fmu_snakeoil_project / "ert/model"
    monkeypatch.chdir(ert_model_path)
    ert_config_path = ert_model_path / "snakeoil.ert"
    add_fmu_pre_sim_workflow(ert_config_path)

    with (
        patch("sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]),
        patch(
            "fmu.dataio._workflows.fmu_pre_sim.main.SumoUploaderInterface"
        ) as uploader_interface,
    ):
        ert.__main__.main()

    uploader_interface.from_new_case.assert_called_once()
    uploader_interface.from_new_case.return_value.upload.assert_called_once()
    fmu_case_yml = (
        fmu_snakeoil_project / "scratch/user/snakeoil/share/metadata/fmu_case.yml"
    )
    assert fmu_case_yml.exists()
