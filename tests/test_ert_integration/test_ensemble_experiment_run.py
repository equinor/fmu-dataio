from pathlib import Path
from typing import Any

import ert.__main__
import pytest
import yaml
from fmu.datamodels import FmuResults
from fmu.datamodels.fmu_results.enums import ErtSimulationMode

from fmu.dataio._utils import uuid_from_string

from .ert_config_utils import (
    add_create_case_workflow,
    add_export_a_surface_forward_model,
)


@pytest.fixture
def snakeoil_export_surface_experiment(
    fmu_snakeoil_project: Path, monkeypatch: Any, mocker: Any
) -> Path:
    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")
    add_export_a_surface_forward_model(fmu_snakeoil_project, "snakeoil.ert")

    mocker.patch(
        "sys.argv",
        ["ert", "ensemble_experiment", "snakeoil.ert", "--disable-monitoring"],
    )
    ert.__main__.main()
    return fmu_snakeoil_project


def test_export_ensemble_experiment(snakeoil_export_surface_experiment: Path) -> None:
    """Test that metadata is set correctly in an ensemble_experiment run"""
    fmu_case_yml = (
        snakeoil_export_surface_experiment
        / "scratch/user/snakeoil/share/metadata/fmu_case.yml"
    )
    assert fmu_case_yml.exists()

    with open(fmu_case_yml, encoding="utf-8") as f:
        fmu_case = yaml.safe_load(f)

    case_uuid = fmu_case["fmu"]["case"]["uuid"]
    share_path = "share/results/maps/all--average_poro.gri"

    # three realizations are present
    for real_num in range(3):
        avg_poro = Path(
            snakeoil_export_surface_experiment
            / f"scratch/user/snakeoil/realization-{real_num}/iter-0"
            / "share/results/maps/.all--average_poro.gri.yml"
        )
        assert avg_poro.exists()

        with open(avg_poro, encoding="utf-8") as f:
            avg_poro_metadata = yaml.safe_load(f)

        avg_poro = FmuResults.model_validate(avg_poro_metadata)  # asserts valid

        assert (
            avg_poro.root.fmu.ert.simulation_mode
            == ErtSimulationMode.ensemble_experiment
        )
        assert avg_poro.root.fmu.ert.experiment.id is not None

        # the three realizations should have equal runpath_relative_path and entity.uuid
        assert avg_poro.root.file.runpath_relative_path == Path(share_path)
        assert avg_poro.root.fmu.entity.uuid == uuid_from_string(case_uuid + share_path)
