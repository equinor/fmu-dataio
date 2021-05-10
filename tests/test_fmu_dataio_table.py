"""Test the surface_io module."""
from collections import OrderedDict
import logging
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


def test_table_io(tmp_path):
    """Minimal test tables io, uses tmp_path."""

    # make a small DataFrame
    table = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.table_fformat = "csv"

    exp = fmu.dataio.ExportData(name="test", verbosity="INFO")
    exp._pwd = tmp_path
    exp.to_file(table)

    assert (tmp_path / "tables" / ".test.yml").is_file() is True


def test_tables_io_larger_case_ertrun(tmp_path):
    """Larger test table io as ERTRUN, uses global config from Drogon to tmp_path."""

    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.table_fformat = "csv"

    exp = fmu.dataio.ExportData(
        name="sometable",
        config=CFG2,
        content="volumetrics",
        unit="m",
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        verbosity="INFO",
        runfolder=RUN,
        workflow="my current workflow",
    )

    # make a fake DataFrame
    table = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})

    exp.to_file(table, verbosity="INFO")

    metadataout = tmp_path / "tables" / ".sometable--what_descr.yml"
    assert metadataout.is_file() is True
