"""Test the dataio running from ERT2 aka forward model as pretended context.

In this case a user sits in ERT. Hence the rootpath will be ./
"""
import logging
import os

import pandas as pd

import fmu.dataio.dataio as dataio
from fmu.dataio._utils import S, prettyprint_dict

logger = logging.getLogger(__name__)


def test_regsurf_generate_metadata(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test generating metadata for a surface pretend ERT2 job"""
    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        verbosity="INFO",
    )

    meta = edata.generate_metadata(regsurf)
    assert str(edata._pwd) == str(fmurun_w_casemetadata)
    assert str(edata._rootpath.resolve()) == str(
        fmurun_w_casemetadata.parent.parent.resolve()
    )
    assert meta["file"]["relative_path"].startswith("realization-0/iter-0/share")


def test_regsurf_metadata_with_timedata(
    fmurun_w_casemetadata, rmsglobalconfig, regsurf
):
    """Export the regular surface to file with correct metadata/name/timedata."""

    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        verbosity="INFO",
    )

    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300101, "moni"], [20100203, "base"]],
        verbosity="INFO",
    )
    assert meta1["data"]["time"]["t0"]["value"] == "2010-02-03T00:00:00"
    assert meta1["data"]["time"]["t0"]["label"] == "base"
    assert meta1["data"]["time"]["t1"]["value"] == "2030-01-01T00:00:00"
    assert meta1["data"]["time"]["t1"]["label"] == "moni"

    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300123, "one"]],
        verbosity="INFO",
    )

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
        verbosity="INFO",
        workflow="My test workflow",
        unit="myunit",
    )  # read from global config

    assert edata._cfg[S]["unit"] == "myunit"

    # generating metadata without export is possible
    themeta = edata.generate_metadata(
        regsurf,
        unit="furlongs",  # intentional override
    )
    assert themeta["data"]["unit"] == "furlongs"
    logger.debug("Metadata: \n%s", prettyprint_dict(themeta))

    # doing actual export with a few ovverides
    output = edata.export(
        regsurf,
        name="TopVolantis",
        access_ssdl={"access_level": "restricted", "rep_include": False},
        unit="forthnite",  # intentional override
    )
    logger.info("Output is %s", output)

    assert edata._metadata["access"]["ssdl"]["access_level"] == "restricted"
    assert edata._metadata["data"]["unit"] == "forthnite"


# ======================================================================================
# Polygons and Points
# ======================================================================================


def test_polys_export_file_set_name(fmurun_w_casemetadata, rmsglobalconfig, polygons):
    """Export the polygon to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(polygons, name="TopVolantis")
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

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(points, name="TopVolantis")
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

    dataio.ExportData.points_fformat = "csv|xtgeo"

    edata = dataio.ExportData(
        config=rmsglobalconfig, verbosity="INFO"
    )  # read from global config

    output = edata.export(points, name="TopVolantiz")
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
# ======================================================================================


def test_cube_export_file_set_name(fmurun_w_casemetadata, rmsglobalconfig, cube):
    """Export the cube to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(cube, name="MyCube")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath / "realization-0/iter-0/share/results/cubes/mycube.segy"
        ).resolve()
    )


# ======================================================================================
# Grid and GridProperty
# ======================================================================================


def test_grid_export_file_set_name(fmurun_w_casemetadata, rmsglobalconfig, grid):
    """Export the grid to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(grid, name="MyGrid")
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

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(gridproperty, name="MyGridProperty")
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

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(dataframe, name="MyDataframe")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (
            edata._rootpath
            / "realization-0/iter-0/share/results/tables/mydataframe.csv"
        ).resolve()
    )

    metaout = dataio.read_metadata(output)
    assert metaout["data"]["spec"]["columns"] == ["COL1", "COL2"]


def test_pyarrow_export_file_set_name(
    fmurun_w_casemetadata, rmsglobalconfig, arrowtable
):
    """Export the arrow to file with correct metadata and name."""

    logger.info("Active folder is %s", fmurun_w_casemetadata)
    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    if arrowtable:  # is None if PyArrow package is not present
        output = edata.export(arrowtable, name="MyArrowtable")
        logger.info("Output is %s", output)

        assert str(output) == str(
            (
                edata._rootpath
                / "realization-0/iter-0/share/results/tables/myarrowtable.arrow"
            ).resolve()
        )

        metaout = dataio.read_metadata(output)
        assert metaout["data"]["spec"]["columns"] == ["COL1", "COL2"]
