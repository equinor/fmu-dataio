"""Test the surface_io module."""
from collections import OrderedDict
import numpy as np
import xtgeo
import yaml

import fmu.dataio

CFG = OrderedDict()
CFG["template"] = {"name": "Test", "revision": "AUTO"}
CFG["masterdata"] = {
    "smda": {
        "country": [
            {"identifier": "Norway", "uuid": "ad214d85-8a1d-19da-e053-c918a4889309"}
        ],
        "discovery": [{"short_identifier": "abdcef", "uuid": "ghijk"}],
    }
}

CFG2 = {}
with open("tests/data/drogon/global_config2/global_variables.yml", "r") as stream:
    CFG2 = yaml.safe_load(stream)


def test_surface_io(tmp_path):
    """Minimal test surface io, uses tmp_path."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, values=np.ma.ones((20, 30)), name="test"
    )
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData()
    exp._pwd = tmp_path
    exp.to_file(srf)

    assert (tmp_path / "maps" / ".test.yml").is_file() is True


def test_surface_io_larger_case(tmp_path):
    """Larger test surface io, uses global config from Drogon to tmp_path."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20, nrow=30, values=np.ma.ones((20, 30)), name="TopVolantis"
    )
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    exp = fmu.dataio.ExportData(
        config=CFG2,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="WARNING",
    )
    exp._pwd = tmp_path
    exp.to_file(srf, verbosity="DEBUG")

    metadataout = tmp_path / "maps" / ".topvolantis--what_descr.yml"
    assert metadataout.is_file() is True
    print(metadataout)
