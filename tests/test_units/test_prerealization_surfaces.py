"""Test the dataio running with pre-realization objects, e.g. surfaces.

Thses outputs will ned an active 'stage' key in order to come into the right folder
and classification

These objects are normally made as hook workflows before ERT has ran any forward jobs
and are typically used to compare results.
"""
import logging
import os

import fmu.dataionew.dataionew as dataio

logger = logging.getLogger(__name__)


def test_regsurf_case_observation(fmurun_w_casemetadata, rmsglobalconfig, regsurf):
    """Test generating pre-realization surfaces."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
        context="case",
        name="mymap",
        is_observation=True,
    )

    metadata = edata.generate_metadata(regsurf)
    assert (
        "ertrun1/share/observation/maps/mymap.gri" in metadata["file"]["absolute_path"]
    )

    exp = edata.export(regsurf)
    assert "ertrun1/share/observation/maps/mymap.gri" in exp


def test_regsurf_case_observation_w_symlinks(
    fmurun_w_casemetadata, rmsglobalconfig, regsurf
):
    """Generating case level surface, with symlinks on realization folders."""
    logger.info("Active folder is %s", fmurun_w_casemetadata)

    os.chdir(fmurun_w_casemetadata)

    edata = dataio.ExportData(
        config=rmsglobalconfig,  # read from global config
        context={"case": "symlink"},
        name="mymap",
        is_observation=True,
    )

    metadata = edata.generate_metadata(regsurf)
    assert (
        "ertrun1/share/observation/maps/mymap.gri" in metadata["file"]["absolute_path"]
    )

    exp = edata.export(regsurf)
    assert "ertrun1/share/observation/maps/mymap.gri" in exp
