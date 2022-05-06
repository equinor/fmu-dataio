"""Test the dataio running from within RMS interactive as pretended context.

In this case a user sits in RMS, which is in folder rms/model and runs
interactive. Hence the rootpath will be ../../
"""
import logging
import os

import pandas as pd
import pytest
from conftest import inside_rms

import fmu.dataionew.dataionew as dataio
from fmu.dataionew._utils import S, prettyprint_dict
from fmu.dataionew.dataionew import ValidationError

logger = logging.getLogger(__name__)

logger.info("Inside RMS status %s", dataio.ExportData._inside_rms)


@inside_rms
def test_regsurf_generate_metadata(rmssetup, rmsglobalconfig, regsurf):
    """Test generating metadata for a surface pretend inside RMS"""
    logger.info("Active folder is %s", rmssetup)

    logger.debug(prettyprint_dict(rmsglobalconfig["access"]))

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
    )
    logger.info("Inside RMS status now %s", dataio.ExportData._inside_rms)

    edata.generate_metadata(regsurf)
    assert str(edata._pwd) == str(rmssetup)
    assert str(edata._rootpath.resolve()) == str(rmssetup.parent.parent.resolve())


@inside_rms
def test_regsurf_generate_metadata_change_content(rmssetup, rmsglobalconfig, regsurf):
    """As above but change a key in the generate_metadata"""

    logger.info("Active folder is %s", rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    meta1 = edata.generate_metadata(regsurf)
    meta2 = edata.generate_metadata(regsurf, content="time")

    assert meta1["data"]["content"] == "depth"
    assert meta2["data"]["content"] == "time"


@inside_rms
def test_regsurf_generate_metadata_change_content_invalid(rmsglobalconfig, regsurf):
    """As above but change an invalid name of key in the generate_metadata"""
    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    with pytest.raises(ValidationError):
        _ = edata.generate_metadata(regsurf, blablabla="time")


@inside_rms
def test_regsurf_export_file(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata."""

    logger.info("Active folder is %s", rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(regsurf)
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/maps/unknown.gri").resolve()
    )


@inside_rms
def test_regsurf_export_file_set_name(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata and name."""

    logger.info("Active folder is %s", rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(regsurf, name="TopVolantis")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/maps/topvolantis.gri").resolve()
    )


@inside_rms
def test_regsurf_metadata_with_timedata(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata and name and timedata."""

    logger.info("Active folder is %s", rmssetup)

    edata = dataio.ExportData(
        config=rmsglobalconfig,
        verbosity="INFO",
    )  # read from global config
    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300101, "moni"], [20100203, "base"]],
        verbosity="INFO",
    )
    assert meta1["data"]["t0"]["value"] == "2010-02-03T00:00:00"
    assert meta1["data"]["t0"]["label"] == "base"
    assert meta1["data"]["t1"]["value"] == "2030-01-01T00:00:00"
    assert meta1["data"]["t1"]["label"] == "moni"

    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300123, "one"]],
        verbosity="INFO",
    )

    assert meta1["data"]["t0"]["value"] == "2030-01-23T00:00:00"
    assert meta1["data"]["t0"]["label"] == "one"
    assert meta1["data"].get("t1", None) is None

    logger.info(prettyprint_dict(meta1))


@inside_rms
def test_regsurf_metadata_with_timedata_legacy(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata timedata, legacy ver."""

    logger.info("Active folder is %s", rmssetup)

    dataio.ExportData.legacy_time_format = True
    edata = dataio.ExportData(
        config=rmsglobalconfig,
        verbosity="INFO",
    )  # read from global config
    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300101, "moni"], [20100203, "base"]],
        verbosity="INFO",
    )
    logger.info(prettyprint_dict(meta1))

    assert meta1["data"]["time"][1]["value"] == "2010-02-03T00:00:00"
    assert meta1["data"]["time"][1]["label"] == "base"
    assert meta1["data"]["time"][0]["value"] == "2030-01-01T00:00:00"
    assert meta1["data"]["time"][0]["label"] == "moni"

    meta1 = edata.generate_metadata(
        regsurf,
        name="TopVolantis",
        timedata=[[20300123, "one"]],
        verbosity="INFO",
    )

    assert meta1["data"]["time"][0]["value"] == "2030-01-23T00:00:00"
    assert meta1["data"]["time"][0]["label"] == "one"

    assert len(meta1["data"]["time"]) == 1

    dataio.ExportData.legacy_time_format = False


@inside_rms
def test_regsurf_export_file_fmurun(
    rmsrun_fmu_w_casemetadata, rmsglobalconfig, regsurf
):
    """Being in RMS and in an active FMU run with case metadata present.

    Export the regular surface to file with correct metadata and name.
    """

    logger.info("Active folder is %s", rmsrun_fmu_w_casemetadata)
    os.chdir(rmsrun_fmu_w_casemetadata)

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


@inside_rms
def test_polys_export_file_set_name(rmssetup, rmsglobalconfig, polygons):
    """Export the polygon to file with correct metadata and name."""

    logger.info("Active folder is %s", rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(polygons, name="TopVolantis")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/polygons/topvolantis.csv").resolve()
    )


@inside_rms
def test_points_export_file_set_name(rmssetup, rmsglobalconfig, points):
    """Export the points to file with correct metadata and name."""

    logger.info("Active folder is %s", rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(points, name="TopVolantis")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/points/topvolantis.csv").resolve()
    )

    thefile = pd.read_csv(edata._rootpath / "share/results/points/topvolantis.csv")
    assert thefile.columns[0] == "X"


@inside_rms
def test_points_export_file_set_name_xtgeoheaders(rmssetup, rmsglobalconfig, points):
    """Export the points to file with correct metadata and name but here xtgeo var."""

    logger.info("Active folder is %s", rmssetup)
    dataio.ExportData.points_fformat = "csv|xtgeo"

    edata = dataio.ExportData(
        config=rmsglobalconfig, verbosity="INFO"
    )  # read from global config

    output = edata.export(points, name="TopVolantis")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata._rootpath / "share/results/points/topvolantis.csv").resolve()
    )

    thefile = pd.read_csv(edata._rootpath / "share/results/points/topvolantis.csv")
    assert thefile.columns[0] == "X_UTME"

    dataio.ExportData.points_fformat = "csv"
