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


def test_rmsgridjob_export(SimgridJob, DROGON_FMU_CONFIG, fmurun_w_casemetadata):
    print(f"cd into {str(fmurun_w_casemetadata)}")
    rms_folder = fmurun_w_casemetadata / "rms/model"
    rms_folder.mkdir(parents=True, exist_ok=True)
    os.chdir(rms_folder)
    exported = SimgridJob.export(config_path=DROGON_FMU_CONFIG)
    exported_count = len(exported)
    print(f"Exported to {exported}")
    share_path = fmurun_w_casemetadata / "share/results"
    print(share_path)
    folders = list(share_path.glob("*/"))
    assert (
        len(folders) == 1
    ), f"More than 1 folders ({folders}) under share created ({len(folders)})"
    folder_name = folders[0].name
    assert (
        folder_name == "grids"
    ), f"Exported to wrong folder, should be grids, but is {folder_name}"
    metadata_objects = share_path.glob("grids/*.yml")
    meta_count = 0
    for metadata_object in metadata_objects:
        obj_path = metadata_object.parent / metadata_object.name[1:].replace(".yml", "")
        assert (
            obj_path.exists()
        ), f"metadata object {metadata_object.name} had no corresponding object"
        meta_count += 1
    assert (
        meta_count == exported_count
    ), f"Expected count of object to be {exported_count}, but is {meta_count}"
