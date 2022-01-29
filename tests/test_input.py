"""Test the ExportInputData module"""

import logging

from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xtgeo
import yaml

import fmu.dataio

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CFG2 = {}
with open("tests/data/drogon/global_config2/global_variables.yml", "r") as stream:
    CFG2 = yaml.safe_load(stream)

CASEPATH = "tests/data/drogon/ertrun1"


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

    casefolder = tmp_path / "scratch" / "fields" / "user" / "mycase"
    casefolder.mkdir(parents=True, exist_ok=True)
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
        caseroot=casefolder.resolve(),
        verbosity="INFO",
    )

    # save to file, on <case>/share/input
    exp.export(srf, verbosity="INFO")
    assert (out / "topvolantis--what_descr.gri").is_file() is True
    assert (out / ".topvolantis--what_descr.gri.yml").is_file() is True


def test_input_table(tmp_path):
    """Test that an input table is given expected metadata."""

    # make a fake RegularSurface
    df = pd.DataFrame({"col1": [1, 2, 3, 4, 5], "col2": [11, 12, 13, 14, 15]})

    casefolder = tmp_path / "scratch" / "fields" / "user" / "mycase"
    casefolder.mkdir(parents=True, exist_ok=True)
    out = casefolder / "share" / "input" / "tables"

    exp = fmu.dataio.ExportInputData(
        name="mytesttable",
        config=CFG2,
        content="depth",
        unit="m",
        vertical_domain={"depth": "msl"},
        timedata=None,
        is_prediction=True,
        is_observation=False,
        tagname="what Descr",
        caseroot=casefolder.resolve(),
        verbosity="INFO",
    )

    # save to file, on <case>/share/input
    exp.export(df, verbosity="INFO")
    assert (out / "mytesttable--what_descr.csv").is_file() is True
    assert (out / ".mytesttable--what_descr.csv.yml").is_file() is True
