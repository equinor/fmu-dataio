"""Test the surface_io module."""
import logging
import shutil
from collections import OrderedDict

import pandas as pd
import pyarrow as pa
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


def test_table_io_pandas(tmp_path):
    """Minimal test tables io, uses tmp_path."""

    # make a small DataFrame
    df = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})
    fmu.dataio.ExportData.export_root = tmp_path.resolve()
    fmu.dataio.ExportData.table_fformat = "csv"

    exp = fmu.dataio.ExportData(
        name="test",
        verbosity="INFO",
        content="volumes",
        runfolder=tmp_path,
    )
    exp.to_file(df)

    assert (tmp_path / "tables" / ".test.csv.yml").is_file() is True
    with open(tmp_path / "tables" / "test.csv") as stream:
        header = stream.readline().split(",")
    assert len(header) == 2

    # export with index=True which will give three columns (first is the index column)
    exp.to_file(df, index=True)
    with open(tmp_path / "tables" / "test.csv") as stream:
        header = stream.readline().split(",")
    assert len(header) == 3


def test_table_io_arrow(tmp_path):
    """Test the support for PyArrow tables"""

    # make a small pa.Table
    df = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})
    table = pa.Table.from_pandas(df)
    fmu.dataio.ExportData.export_root = tmp_path.resolve()

    exp = fmu.dataio.ExportData(
        name="test", verbosity="INFO", content="timeseries", runfolder=tmp_path
    )
    exp.to_file(table)

    assert (tmp_path / "tables" / "test.arrow").is_file() is True
    assert (tmp_path / "tables" / ".test.arrow.yml").is_file() is True

    table_in = pa.feather.read_table(tmp_path / "tables" / "test.arrow")
    assert table_in.num_columns == 2

    with open(tmp_path / "tables" / ".test.arrow.yml") as stream:
        metadata = yaml.safe_load(stream)
        assert metadata["data"]["layout"] == "table"
        assert metadata["data"]["spec"]["size"] == 6
        assert metadata["data"]["spec"]["columns"] == ["STOIIP", "PORO"]


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
    df = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})

    exp.to_file(df, verbosity="INFO")

    metadataout = out / ".sometable--what_descr.csv.yml"
    assert metadataout.is_file() is True

    # then try pyarrow
    table = pa.Table.from_pandas(df)
    exp.to_file(table, verbosity="INFO")

    metadataout = out / ".sometable--what_descr.arrow.yml"
    assert metadataout.is_file() is True
