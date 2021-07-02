"""Test the surface_io module."""
from collections import OrderedDict
import logging
import shutil
import pandas as pd
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
CASEPATH = "tests/data/drogon/ertrun1"


def test_table_io(tmp_path):
    """Minimal test tables io, uses tmp_path."""

    # make a small DataFrame
    table = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.table_fformat = "csv"

    exp = fmu.dataio.ExportData(name="test", verbosity="INFO", content="volumes")
    exp._pwd = tmp_path
    exp.to_file(table)

    assert (tmp_path / "tables" / ".test.csv.yml").is_file() is True


def test_tables_io_larger_case_ertrun(tmp_path):
    """Larger test table io as ERTRUN, uses global config from Drogon to tmp_path."""

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CASEPATH, current / "mycase")

    fmu.dataio.ExportData.export_root = "../../share/results"
    fmu.dataio.ExportData.table_fformat = "csv"

    runfolder = current / "mycase" / "realization-0" / "iter-0" / "rms" / "model"
    runfolder.mkdir(parents=True, exist_ok=True)
    out = (
        current / "mycase" / "realization-0" / "iter-0" / "share" / "results" / "tables"
    )

    exp = fmu.dataio.ExportData(
        name="sometable",
        config=CFG2,
        content="volumetrics",
        unit="m",
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="INFO",
        runfolder=runfolder.resolve(),
        workflow="my current workflow",
    )

    # make a fake DataFrame
    table = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})

    exp.to_file(table, verbosity="INFO")

    metadataout = out / ".sometable--what_descr.csv.yml"
    assert metadataout.is_file() is True
