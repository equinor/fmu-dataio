"""Test the ExportInputData module"""

import logging
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import xtgeo
import yaml
import json

import jsonschema

import fmu.dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CFG2 = {}
with open("tests/data/drogon/global_config2/global_variables.yml", "r") as stream:
    CFG2 = yaml.safe_load(stream)

CASEPATH = "tests/data/drogon/ertrun1"

TESTDIR = Path(__file__).parent.absolute()
SCHEMA = TESTDIR / "../schema/definitions/0.8.0/schema/fmu_results.json"

# use case example: A set of input data is exported to /scratch to be available
# within the case structure. The file already exists on disk, OR the file is dumped
# using functionality from fmu-dataio.


def test_input_surface(tmp_path):
    """Test that an input surface is given expected metadata."""

    # make a fake RegularSurface
    srf = xtgeo.RegularSurface(
        ncol=20,
        nrow=30,
        xinc=20,
        yinc=20,
        values=np.ma.ones((20, 30)),
        name="TopVolantis",
    )
    fmu.dataio.ExportData.surface_fformat = "irap_binary"

    # set up the case structure
    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CASEPATH, current / "mycase")
    casefolder = tmp_path / "scratch" / "fields" / "user" / "mycase"
    out = casefolder / "share" / "input" / "maps"

    exp = fmu.dataio.ExportInputData(
        config=CFG2,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        casepath=casefolder.resolve(),
        source="mysource",
        verbosity="DEBUG",
    )

    # save to file, on <case>/share/input
    exp.export(srf, verbosity="DEBUG")
    assert (out / "topvolantis--what_descr.gri").is_file() is True
    assert (out / ".topvolantis--what_descr.gri.yml").is_file() is True

    with open(out / ".topvolantis--what_descr.gri.yml", "r") as stream:
        metadata = yaml.safe_load(stream)

    assert isinstance(metadata, dict)

    assert "fmu" in metadata
    assert "input" in metadata["fmu"]
    assert "model" in metadata["fmu"]
    assert "case" in metadata["fmu"]
    assert "realization" not in metadata["fmu"]
    assert metadata["fmu"]["input"]["source"] == "mysource"

    assert "file" in metadata
    assert "data" in metadata

    # validate exported metadata
    schema = _parse_json(SCHEMA)
    jsonschema.validate(instance=metadata, schema=schema)


def test_input_table(tmp_path):
    """Test that an input table is given expected metadata."""

    # make a fake RegularSurface
    df = pd.DataFrame({"col1": [1, 2, 3, 4, 5], "col2": [11, 12, 13, 14, 15]})

    # set up the case structure
    current = tmp_path / "scratch" / "fields" / "user"
    current.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CASEPATH, current / "mycase")
    casefolder = tmp_path / "scratch" / "fields" / "user" / "mycase"
    out = casefolder / "share" / "input" / "tables"

    exp = fmu.dataio.ExportInputData(
        name="mytesttable",
        source="mysource",
        config=CFG2,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        casepath=casefolder.resolve(),
        verbosity="DEBUG",
    )

    # save to file, on <case>/share/input
    exp.export(df, verbosity="DEBUG")
    assert (out / "mytesttable--what_descr.csv").is_file() is True
    assert (out / ".mytesttable--what_descr.csv.yml").is_file() is True


def _parse_json(schema_path):
    """Parse the schema, return JSON"""
    with open(schema_path) as stream:
        data = json.load(stream)

    return data
