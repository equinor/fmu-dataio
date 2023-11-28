import yaml
from pathlib import Path
from fmu.dataio.rmscollectors.grid import RmsGrid
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
    grid = RmsGrid(drogon_project, "Simgrid", "make_simgrid")
    out_file = TEST_DATA / "rmscollectors/rmsgrid_params.yml"
    if write_yaml:
        with open(out_file, "w") as stream:
            yaml.dump(grid.params, stream)

    return grid


def test_something(simgrid):
    print(simgrid.params)
