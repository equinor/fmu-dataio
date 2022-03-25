"""Test the dataio running from within RMS interactive.

In this case a suser sits in RMS, which is in folder rms/model. Hence the
basepath will be ../../

"""
import os
import shutil

import pytest
import xtgeo
import yaml

import fmu.dataionew.dataionew as dataio


@pytest.fixture(name="setup", scope="module", autouse=True)
def fixture_setup(tmp_path_factory):
    """Create the folder structure to mimic RMS project."""

    tmppath = tmp_path_factory.mktemp("rmscase")
    rmspath = tmppath / "rms/model"
    rmspath.mkdir(parents=True, exist_ok=True)

    # copy a global config here
    shutil.copy("tests/data/drogon/global_config2/global_variables.yml", rmspath)

    os.chdir(rmspath)

    return rmspath


def test_export_regularsurface(setup):
    """Test generating metadata for a surface, pretend being in RMS GUI python shell."""

    current = setup

    print()

    # read the global config
    with open("global_variables.yml", "r", encoding="utf8") as stream:
        global_cfg = yaml.safe_load(stream)

    # in RMS a surface is loaded as surf = xtgeo.surface_from_roxar() but here we make
    # a synthetic instance:
    surf = xtgeo.RegularSurface(ncol=12, nrow=10, xinc=20, yinc=20, values=1234.0)

    edata = dataio.ExportData(
        config=global_cfg,  # read from global config
    )

    edata.generate_metadata(surf)
    assert str(edata.pwd) == str(current)

    print(edata.metadata)
