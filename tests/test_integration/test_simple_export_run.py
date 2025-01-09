import getpass
from pathlib import Path
from typing import Any

import ert.__main__
import pytest
import yaml

from fmu.dataio._models import FmuResults
from fmu.dataio._models.fmu_results.enums import ErtSimulationMode

from .ert_config_utils import (
    add_create_case_workflow,
    add_export_a_surface_forward_model,
)


@pytest.fixture
def snakeoil_export_surface(
    fmu_snakeoil_project: Path, monkeypatch: Any, mocker: Any
) -> Path:
    monkeypatch.chdir(fmu_snakeoil_project / "ert/model")
    add_create_case_workflow("snakeoil.ert")
    add_export_a_surface_forward_model(fmu_snakeoil_project, "snakeoil.ert")

    mocker.patch(
        "sys.argv", ["ert", "test_run", "snakeoil.ert", "--disable-monitoring"]
    )
    ert.__main__.main()
    return fmu_snakeoil_project


def test_simple_export_case_metadata(snakeoil_export_surface: Path) -> None:
    fmu_case_yml = (
        snakeoil_export_surface / "scratch/user/snakeoil/share/metadata/fmu_case.yml"
    )
    assert fmu_case_yml.exists()

    with open(fmu_case_yml, encoding="utf-8") as f:
        fmu_case = yaml.safe_load(f)

    assert fmu_case["fmu"]["case"]["name"] == "snakeoil"
    assert fmu_case["fmu"]["case"]["user"]["id"] == "user"
    assert fmu_case["source"] == "fmu"
    assert len(fmu_case["tracklog"]) == 1
    assert fmu_case["tracklog"][0]["user"]["id"] == getpass.getuser()


def test_simple_export_ert_environment_variables(snakeoil_export_surface: Path) -> None:
    avg_poro_yml = Path(
        snakeoil_export_surface
        / "scratch/user/snakeoil/realization-0/iter-0"
        / "share/results/maps/.all--average_poro.gri.yml"
    )
    assert avg_poro_yml.exists()

    with open(avg_poro_yml, encoding="utf-8") as f:
        avg_poro_metadata = yaml.safe_load(f)

    avg_poro = FmuResults.model_validate(avg_poro_metadata)  # asserts valid
    assert avg_poro.root.fmu.ert.simulation_mode == ErtSimulationMode.test_run
    assert avg_poro.root.fmu.ert.experiment.id is not None
