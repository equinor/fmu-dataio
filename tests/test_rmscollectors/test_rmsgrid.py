import yaml
from pathlib import Path
from fmu.dataio.rmscollectors.grid import RmsGridJob
from fmu.dataio.rmscollectors.grid import (
    _get_grid_dimensions,
    _get_general_settings,
    _get_fault_info,
    _get_zone_info,
)
import pytest

TEST_DATA = Path(__file__).parent / "../data/drogon/"


@pytest.fixture(name="simgrid")
def _fix_simgrid(drogon_project, write_yaml=False):
    """Return RmsStructuralModel object

    Args:
        drogon_project (roxar.Project): drogon project
        write_yaml (bool, optional): write yaml file of .params attribute. Defaults to False.

    Returns:
        RmsStructuralModel: results from job defined with names below
    """
    grid = RmsGridJob(drogon_project, "Simgrid", "make_simgrid")
    out_file = TEST_DATA / "rmscollectors/rmsgrid_params.yml"
    if write_yaml:
        with open(out_file, "w") as stream:
            yaml.dump(grid.params, stream)

    return grid


@pytest.fixture(name="grid_parameters", scope="session")
def _fix_grid_parameters():
    """Return parameter set originally extracted from drogon

    Raises:
        IOError: if cannot find test data

    Returns:
        dict: the parameter dictionary
    """
    # This parameter set is extracted from drogon rms project
    # rms version 13.1.2 linux based
    params = None
    inplace_params = TEST_DATA / "rmscollectors/rmsgrid_params.yml"
    with open(inplace_params, "r") as stream:
        params = yaml.load(stream, Loader=yaml.SafeLoader)

    if params is None:
        raise IOError(f"Cannot find parameters at {str(inplace_params)}")
    return params


def test_grid_dimensions(grid_parameters):
    """Test function _get_grid_dimensions

    Args:
        grid_parameters (dict): extracted parameters from grid job
    """
    required = ["origin", "length", "increment"]
    grid_dimensions = _get_grid_dimensions(grid_parameters)
    assert isinstance(
        grid_parameters, dict
    ), f"Grid dimensions should be dict, but is {type(grid_dimensions)}"
    for name in required:
        assert name in grid_dimensions.keys()
        part = grid_dimensions[name]
        for dim in ["x", "y"]:
            assert dim in part.keys()
            assert isinstance(part[dim], (int, float))


def test_general_settings(grid_parameters):
    """Test function _get_general_settings

    Args:
        grid_parameters (dict): extracted parameters from grid job
    """
    general_settings = _get_general_settings(grid_parameters)
    settings = [
        "repeatsections_allowed",
        "regularized_grid",
        "vertical_boundary",
        "juxtaposition_correction",
    ]
    for setting in settings:
        assert setting in general_settings.keys()
        assert isinstance(general_settings[setting], bool)


def test_faults(simgrid):
    faults = _get_fault_info(simgrid.params)
    assert len(faults) == 6, f"Number of faults {len(faults)}, should be 6"
    print(faults)


def test_get_zones(grid_parameters):
    zones = _get_zone_info(grid_parameters)
    print(zones)
