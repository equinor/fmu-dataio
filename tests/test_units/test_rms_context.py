"""Test the dataio running from within RMS interactive as pretended context.

In this case a user sits in RMS, which is in folder rms/model and runs
interactive. Hence the basepath will be ../../
"""
import logging
import os

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
    assert str(edata.pwd) == str(rmssetup)
    assert str(edata.basepath.resolve()) == str(rmssetup.parent.parent.resolve())


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
        (edata.basepath / "share/results/maps/unknown.gri").resolve()
    )


@inside_rms
def test_regsurf_export_file_set_name(rmssetup, rmsglobalconfig, regsurf):
    """Export the regular surface to file with correct metadata and name."""

    logger.info("Active folder is %s", rmssetup)

    edata = dataio.ExportData(config=rmsglobalconfig)  # read from global config

    output = edata.export(regsurf, name="TopVolantis")
    logger.info("Output is %s", output)

    assert str(output) == str(
        (edata.basepath / "share/results/maps/volantis_gp__top.gri").resolve()
    )


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

    assert edata.cfg[S]["unit"] == "myunit"

    # generating metadata without export is possible
    themeta = edata.generate_metadata(
        regsurf,
        unit="furlongs",  # intentional override
    )
    assert themeta["data"]["unit"] == "furlongs"

    # doing actual export with a few ovverides
    output = edata.export(
        regsurf,
        name="TopVolantis",
        access_ssdl={"access_level": "restricted", "rep_include": False},
        unit="forthnite",  # intentional override
    )
    logger.info("Output is %s", output)

    assert edata.metadata["access"]["ssdl"]["access_level"] == "restricted"
    assert edata.metadata["data"]["unit"] == "forthnite"
