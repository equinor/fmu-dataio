import logging
import os
from fmu.dataio.rmscollectors.grid import RmsGridJob
import pytest

logging.basicConfig(level="DEBUG")


@pytest.fixture(name="SimgridJob", scope="session")
def _fix_simgridjob(drogon_project):
    simgrid_job = RmsGridJob(drogon_project, "Simgrid", "make_simgrid")
    return simgrid_job


@pytest.mark.parametrize(
    "base, correct_list",
    [
        ("fault", [f"F{n+1}" for n in range(6)]),
        ("zone", ["Valysar", "Therys", "Volon"]),
        ("horizon", ["TopVolantis", "TopTherys", "TopVolon", "BaseVolantis"]),
    ],
)
def test_rmsgridjob_attributes(SimgridJob, base, correct_list):
    """Check attributes related to gridjob

    Args:
        SimgridJob (RmsGridJob): object containing all attributes
        base (str): attribute base
        correct_list (list): the expected attribute list
    """
    list_attr = getattr(SimgridJob, f"{base}_names")
    assert isinstance(
        list_attr, list
    ), f"Attr {base}_names should be list, but is {type(list_attr)}"
    assert (
        list_attr == correct_list
    ), f"List should be {correct_list}, but is {list_attr}"
    # print(simgrid_job.based_on)
    # print(simgrid_job.horizon_model)
    # simgrid_job.execute()


@pytest.mark.parametrize(
    "base, correct_list",
    [
        ("fault", [f"F{n+1}" for n in range(6)]),
        ("zone", ["Valysar", "Therys", "Volon"]),
        ("horizon", ["TopVolantis", "TopTherys", "TopVolon", "BaseVolantis"]),
    ],
)
def test_rmsgridjob_attributes(SimgridJob, base, correct_list):
    list_attr = getattr(SimgridJob, f"{base}_names")
    assert isinstance(
        list_attr, list
    ), f"Attr {base}_names should be list, but is {type(list_attr)}"
    assert (
        list_attr == correct_list
    ), f"List should be {correct_list}, but is {list_attr}"
    # print(simgrid_job.based_on)
    # print(simgrid_job.horizon_model)
    # simgrid_job.execute()


def test_rmsgridjob_execute(SimgridJob):
    SimgridJob.execute()


def test_rmsgridjob_export(SimgridJob, DROGON_FMU_CONFIG, tmp_path):
    runpath = tmp_path / "realization-0/iter-0"
    runpath.mkdir(parents=True, exist_ok=True)
    os.chmod(runpath)
    SimgridJob.export(config_path=DROGON_FMU_CONFIG)
