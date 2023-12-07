"""Test fuc"""
import os
import pytest
import yaml
from pathlib import Path
import pandas as pd
from fmu.dataio.rmscollectors.volumetrics import RmsInplaceVolumes

DROGON_PATH = "/project/fmu/tutorial/drogon/resmod/ff/users/dbs/23.1.1/"
TEST_DATA = Path(__file__).parent / "../data/drogon/"


@pytest.fixture(name="inplace_parameters", scope="session")
def _fix_inplace_parameters():
    """Return parameter set originally extracted from drogon

    Raises:
        IOError: if cannot find test data

    Returns:
        dict: the parameter dictionary
    """
    # This parameter set is extracted from drogon rms project
    # rms version 13.1.2 linux based
    params = None
    inplace_params = TEST_DATA / "rmscollectors/rmsinplace_params.yml"
    with open(inplace_params, "r") as stream:
        params = yaml.load(stream, Loader=yaml.SafeLoader)

    if params is None:
        raise IOError(f"Cannot find parameters at {str(inplace_params)}")
    return params


@pytest.fixture(name="geo_volumes", scope="session")
def _fix_geo_volumes(drogon_project):
    return RmsInplaceVolumes(drogon_project, "Geogrid", "geogrid_volumes")


@pytest.mark.parametrize(
    "attr_name", ["params", "report_output", "selectors", "input_variables"]
)
def test_inplace_volumes_attributes(geo_volumes, attr_name):
    """Test class RmsInplaceVolumes attributes

    Args:
        drogon_project (roxar.Project): an instance of the drogon project
    """

    att_type = dict
    assert hasattr(
        geo_volumes, attr_name
    ), f"No {attr_name} attribute for RmsInplaceVolumes"
    attr = getattr(geo_volumes, attr_name)
    assert isinstance(
        attr, att_type
    ), f" {attr_name} should be dictionary, but is {type(attr)}"


def test_inplace_volumes_export(geo_volumes, DROGON_FMU_CONFIG, fmurun_w_casemetadata):
    """Test export of inplace volumes

    Args:
        geo_volumes (dataio.RmsInplaceVolumes): instance of RmsInplaceVolumes from drogon
        tmp_path (pathlib.Path): path where test will be stored
    """
    rms_path = fmurun_w_casemetadata / "rms/model/"
    folder_types = ["maps", "grids", "tables"]
    rms_path.mkdir(parents=True, exist_ok=True)
    os.chdir(rms_path)
    exported = geo_volumes.export(config_path=DROGON_FMU_CONFIG)
    shared_path = fmurun_w_casemetadata / "share/results"
    assert shared_path.exists(), f"folder {str(shared_path)}, not made"
    folders = shared_path.glob("*/")
    folder_count = 0
    for folder in folders:
        assert folder.name in folder_types, f"{folder.name} not in {folder_types}"
        folder_count += 1
    metadata_files = shared_path.glob("**/*.yml")

    print(metadata_files)
    nr_paths = len(exported)
    assert folder_count == 3, f"Found {folder_count} folders, not 3"
    nr_metadata = 0
    for metadata_file in metadata_files:
        print(metadata_file)
        # if statement below is needed because there is interaction between the tests
        if (metadata_file.parent.name not in folder_types) or (
            "geogrid" not in str(metadata_file)
        ):
            continue
        obj_file = metadata_file.parent / metadata_file.name[1:].replace(".yml", "")
        assert (
            obj_file.exists()
        ), f"{str(metadata_file)} does not have corresponding object file ({str(obj_file)})"
        nr_metadata += 1
    assert (
        nr_metadata == nr_paths
    ), f"Found {nr_metadata} objects, but {nr_paths} where expected"


def test_inplace_volumes_report(geo_volumes):
    report = geo_volumes.report
    assert isinstance(
        report, pd.DataFrame
    ), f"Report should be pandas dataframe, but is {type(report)}"
