"""Test the polygons_io module."""
from collections import OrderedDict
import logging
import xtgeo
import yaml

import fmu.dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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

RUN = "tests/data/drogon/ertrun1/realization-0/iter-0/rms"

# make a fake Polygons
POLY = [
    (1.0, 2.0, 3.0, 1),
    (1.5, 2.5, 3.5, 1),
    (1.2, 2.2, 3.1, 1),
    (1.1, 2.0, 3.0, 1),
    (1.1, 2.0, 3.0, 2),
    (1.1, 2.0, 3.0, 2),
    (1.1, 2.0, 3.0, 2),
]


def test_polygons_io(tmp_path):
    """Minimal test polygons io, uses tmp_path."""

    srf = xtgeo.Polygons(POLY)
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.polygons_fformat = "csv"

    exp = fmu.dataio.ExportData(name="test")
    exp._pwd = tmp_path
    exp.to_file(srf)

    assert (tmp_path / "polygons" / ".test.yml").is_file() is True


def test_polygons_io_larger_case_ertrun(tmp_path):
    """Larger test polygons io as ERTRUN, uses global config from Drogon to tmp_path."""

    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.polygons_fformat = "csv"

    exp = fmu.dataio.ExportData(
        name="TopVolantis",
        config=CFG2,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="INFO",
        runfolder=RUN,
        workflow="my current workflow",
    )

    # make a fake Regularpolygons
    srf = xtgeo.Polygons(POLY)

    exp.to_file(srf, verbosity="INFO")

    metadataout = tmp_path / "polygons" / ".topvolantis--what_descr.yml"
    assert metadataout.is_file() is True
