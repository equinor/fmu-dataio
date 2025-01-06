"""Test the dataio running from ERT aka forward model as pretended context.

In this case a user sits in ERT. Hence the rootpath will be ./
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

from fmu.dataio import dataio
from fmu.dataio._utils import prettyprint_dict

logger = logging.getLogger(__name__)


def test_regsurf_generate_metadata(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test generating metadata for a surface pretend ERT job"""
    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(config=rmsglobalconfig, content="depth")

    meta = edata.generate_metadata(regsurf)
    assert str(edata._pwd) == str(fmurun_w_casemetadata)
    assert str(edata._rootpath.resolve()) == str(
        fmurun_w_casemetadata.parent.parent.resolve()
    )
    assert meta["file"]["relative_path"].startswith("realization-0/iter-0/share")
    assert "jobs" not in meta["fmu"]["realization"]


def test_incl_jobs_warning(rmsglobalconfig):
    """Check that using the deprecated class variable include_ertjobs gives warning."""

    dataio.ExportData.include_ertjobs = True

    with pytest.warns(UserWarning, match="deprecated"):
        dataio.ExportData(
            config=rmsglobalconfig,
            content="depth",
        )
    dataio.ExportData.include_ertjobs = False


def test_regsurf_metadata_with_timedata(
    fmurun_w_casemetadata, rmsglobalconfig, regsurf
):
    """Export the regular surface to file with correct metadata/name/timedata."""

    os.chdir(fmurun_w_casemetadata)

    meta1 = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        name="TopVolantis",
        timedata=[[20300101, "moni"], [20100203, "base"]],
    ).generate_metadata(regsurf)

    assert meta1["data"]["time"]["t0"]["value"] == "2010-02-03T00:00:00"
    assert meta1["data"]["time"]["t0"]["label"] == "base"
    assert meta1["data"]["time"]["t1"]["value"] == "2030-01-01T00:00:00"
    assert meta1["data"]["time"]["t1"]["label"] == "moni"

    meta1 = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        name="TopVolantis",
        timedata=[[20300123, "one"]],
    ).generate_metadata(regsurf)

    assert meta1["data"]["time"]["t0"]["value"] == "2030-01-23T00:00:00"
    assert meta1["data"]["time"]["t0"]["label"] == "one"
    assert meta1["data"]["time"].get("t1", None) is None

    logger.debug(prettyprint_dict(meta1))


def test_regsurf_export_file_fmurun(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Being in a script and in an active FMU run with case metadata present.

    Export the regular surface to file with correct metadata and name.
    """

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        workflow="My test workflow",
        unit="myunit",
        content="depth",
        classification="restricted",
        rep_include=False,
    )  # read from global config

    assert edata.unit == "myunit"

    # generating metadata without export is possible
    themeta = edata.generate_metadata(regsurf)
    assert themeta["data"]["unit"] == "myunit"
    logger.debug("Metadata: \n%s", prettyprint_dict(themeta))

    # doing actual export with a few ovverides
    # Note unit will not be allowed to override in the future
    with pytest.warns(FutureWarning, match="move them up to initialization"):
        output = edata.export(
            regsurf,
            name="TopVolantis",
            unit="forthnite",  # intentional override
        )
    logger.info("Output is %s", output)

    out = Path(edata.export(regsurf))
    with open(out.parent / f".{out.name}.yml", encoding="utf-8") as f:
        metadata = yaml.safe_load(f)
    assert metadata["access"]["ssdl"]["access_level"] == "restricted"
    assert metadata["data"]["unit"] == "forthnite"


# ======================================================================================
# Polygons and Points
# ======================================================================================


def test_polys_export_file_set_name(fmurun_w_casemetadata, rmsglobalconfig, polygons):
    """Export the polygon to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="TopVolantis"
    )

    output = edata.export(polygons)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath
            / "realization-0/iter-0/share/results/polygons/topvolantis.csv"
        ).resolve()
    )


def test_points_export_file_set_name(fmurun_w_casemetadata, rmsglobalconfig, points):
    """Export the points to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="TopVolantis"
    )

    output = edata.export(points)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath
            / "realization-0/iter-0/share/results/points/topvolantis.csv"
        ).resolve()
    )

    thefile = pd.read_csv(
        edata._rootpath / "realization-0/iter-0/share/results/points/topvolantis.csv"
    )
    assert thefile.columns[0] == "X"


def test_points_export_file_set_name_xtgeoheaders(
    fmurun_w_casemetadata, rmsglobalconfig, points
):
    """Export the points to file with correct metadata and name but here xtgeo var."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    dataio.ExportData.points_fformat = "csv"
    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="TopVolantiz"
    )
    edata.points_fformat = "csv|xtgeo"  # override

    output = edata.export(points)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath
            / "realization-0/iter-0/share/results/points/topvolantiz.csv"
        ).resolve()
    )

    thefile = pd.read_csv(
        edata._rootpath / "realization-0/iter-0/share/results/points/topvolantiz.csv"
    )
    assert thefile.columns[0] == "X_UTME"

    dataio.ExportData.points_fformat = "csv"


# ======================================================================================
# Cube
# Also use this part to test various fmu_contexts and forcefolder
# ======================================================================================


def test_cube_export_file_set_name(fmurun_w_casemetadata, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(config=rmsglobalconfig, content="depth", name="MyCube")

    output = edata.export(cube)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath / "realization-0/iter-0/share/results/cubes/mycube.segy"
        ).resolve()
    )


def test_cube_export_file_is_observation(fmurun_w_casemetadata, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata..., with is_observation flag."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        is_observation=True,
        fmu_context="realization",
        name="MyCube",
    )

    output = edata.export(cube)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath
            / "realization-0/iter-0/share/observations/cubes/mycube.segy"
        ).resolve()
    )


def test_cube_export_file_is_case_observation(
    fmurun_w_casemetadata, rmsglobalconfig, cube
):
    """Export the cube..., with is_observation flag and fmu_context is case."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        is_observation=True,
        fmu_context="case",
        name="MyCube",
    )

    output = edata.export(cube)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/observations/cubes/mycube.segy").resolve()
    )


def test_cube_export_file_is_observation_forcefolder(
    fmurun_w_casemetadata, rmsglobalconfig, cube
):
    """Export the cube to file..., with is_observation flag and forcefolder."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        content="depth",
        is_observation=True,
        fmu_context="realization",
        forcefolder="seismic",
        name="MyCube",
    )

    output = edata.export(cube)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath
            / "realization-0/iter-0/share/observations/seismic/mycube.segy"
        ).resolve()
    )


@pytest.mark.skipif("win" in sys.platform, reason="Windows tests have no /tmp")
def test_cube_export_file_is_observation_forcefolder_abs(
    fmurun_w_casemetadata, rmsglobalconfig, cube
):
    """Export the cube to file..., with is_observation flag and absolute forcefolder.

    Using an absolute path requires class property allow_forcefolder_absolute = True
    """

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    dataio.ExportData.allow_forcefolder_absolute = True
    with pytest.warns(UserWarning, match="deprecated"):
        edata = dataio.ExportData(
            config=rmsglobalconfig,
            content="depth",
            is_observation=True,
            fmu_context="realization",
            forcefolder="/tmp/seismic",
            name="MyCube",
        )

    with pytest.raises(ValueError, match="Can't use absolute path as 'forcefolder'"):
        output = edata.export(cube)
        logger.info("Output is %s", output)

    dataio.ExportData.allow_forcefolder_absolute = False


# ======================================================================================
# Grid and GridProperty
# ======================================================================================


def test_grid_export_file_set_name(fmurun_w_casemetadata, rmsglobalconfig, grid):
    """Export the grid to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(config=rmsglobalconfig, content="depth", name="MyGrid")

    output = edata.export(grid)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath / "realization-0/iter-0/share/results/grids/mygrid.roff"
        ).resolve()
    )


def test_gridproperty_export_file_set_name(
    fmurun_w_casemetadata, rmsglobalconfig, gridproperty
):
    """Export the gridprop to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="MyGridProperty"
    )
    # check that user warning is given to provide a grid geometry
    with pytest.warns(FutureWarning, match="linking it to a geometry"):
        output = edata.export(gridproperty)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath
            / "realization-0/iter-0/share/results/grids/mygridproperty.roff"
        ).resolve()
    )


# ======================================================================================
# Dataframe and PyArrow
# ======================================================================================


def test_dataframe_export_file_set_name(
    fmurun_w_casemetadata, rmsglobalconfig, dataframe
):
    """Export the dataframe to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="MyDataframe"
    )

    output = edata.export(dataframe)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath
            / "realization-0/iter-0/share/results/tables/mydataframe.csv"
        ).resolve()
    )

    metaout = dataio.read_metadata(output)
    assert metaout["data"]["spec"]["columns"] == ["COL1", "COL2"]
    assert metaout["data"]["spec"]["num_columns"] == 2
    assert metaout["data"]["spec"]["num_rows"] == 4
    assert metaout["data"]["spec"]["size"] == 8


def test_pyarrow_export_file_set_name(
    fmurun_w_casemetadata, rmsglobalconfig, arrowtable
):
    """Export the arrow to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig, content="depth", name="MyArrowtable"
    )

    if arrowtable:  # is None if PyArrow package is not present
        output = edata.export(arrowtable)
        logger.info("Output is %s", output)

        assert str(output) == str(
            (
                edata._rootpath
                / "realization-0/iter-0/share/results/tables/myarrowtable.parquet"
            ).resolve()
        )

        metaout = dataio.read_metadata(output)
        assert metaout["data"]["spec"]["columns"] == ["COL1", "COL2"]
        assert metaout["data"]["spec"]["num_columns"] == 2
        assert metaout["data"]["spec"]["num_rows"] == 4
        assert metaout["data"]["spec"]["size"] == 8
