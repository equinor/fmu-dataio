"""Test the surface_io module."""
import logging
import shutil
import sys
from collections import OrderedDict

import pandas as pd
import pytest

try:
    import pyarrow as pa
except ImportError:
    pass

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
with open("tests/data/drogon/global_config2/global_variables.yml", "r") as mstream:
    CFG2 = yaml.safe_load(mstream)

RUN = "tests/data/drogon/ertrun1/realization-0/iter-0/rms"
CASEPATH = "tests/data/drogon/ertrun1"
FMUP1 = "share/results"


def test_table_io_pandas(tmp_path):
    """Minimal test tables io, uses tmp_path."""

    # make a small DataFrame
    df = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})
    fmu.dataio.ExportData.table_fformat = "csv"

    exp = fmu.dataio.ExportData(
        name="test",
        verbosity="INFO",
        content="volumes",
        runpath=tmp_path,
        include_index=False,
    )
    exp.export(df)

    assert (tmp_path / FMUP1 / "tables" / ".test.csv.yml").is_file() is True
    with open(tmp_path / FMUP1 / "tables" / "test.csv") as stream:
        header = stream.readline().split(",")
    assert len(header) == 2

    # export with index=True which will give three columns (first is the index column)
    exp.export(df, include_index=True)
    with open(tmp_path / FMUP1 / "tables" / "test.csv") as stream:
        header = stream.readline().split(",")
    assert len(header) == 3


@pytest.mark.skipif("pyarrow" not in sys.modules, reason="requires pyarrow")
def test_table_io_arrow(tmp_path):
    """Test the support for PyArrow tables"""

    # make a small pa.Table
    df = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})
    table = pa.Table.from_pandas(df)

    exp = fmu.dataio.ExportData(
        name="test", verbosity="INFO", content="timeseries", runpath=tmp_path
    )
    exp.export(table)

    assert (tmp_path / FMUP1 / "tables" / "test.arrow").is_file() is True
    assert (tmp_path / FMUP1 / "tables" / ".test.arrow.yml").is_file() is True

    table_in = pa.feather.read_table(tmp_path / FMUP1 / "tables" / "test.arrow")
    assert table_in.num_columns == 2

    with open(tmp_path / FMUP1 / "tables" / ".test.arrow.yml") as stream:
        metadata = yaml.safe_load(stream)
        assert metadata["data"]["layout"] == "table"
        assert metadata["data"]["spec"]["size"] == 6
        assert metadata["data"]["spec"]["columns"] == ["STOIIP", "PORO"]


@pytest.mark.skipif("pyarrow" not in sys.modules, reason="requires pyarrow")
def test_tables_io_larger_case_ertrun(tmp_path):
    """Larger test table io as ERTRUN, uses global config from Drogon to tmp_path."""

    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CASEPATH, current / "mycase")

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
        inside_rms=True,
        workflow="my current workflow",
    )

    # make a fake DataFrame
    df = pd.DataFrame({"STOIIP": [123, 345, 654], "PORO": [0.2, 0.4, 0.3]})

    exp.export(df, verbosity="INFO")

    metadataout = out / ".sometable--what_descr.csv.yml"
    assert metadataout.is_file() is True

    # then try pyarrow
    table = pa.Table.from_pandas(df)
    exp.export(table, verbosity="INFO")

    metadataout = out / ".sometable--what_descr.arrow.yml"
    assert metadataout.is_file() is True
